# Toronto TTC Subway Delay Pipeline

Load the TTC's January through December 2024 subway delay workbook into PostgreSQL, then rank stations by reported delays and causes by reported delay minutes. The Python script converts the City's two Excel workbooks into CSV files. PostgreSQL stores and queries the data. [City of Toronto TTC Subway Delay Data](https://open.toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/)

## 1. Set up on Windows

Open PowerShell in this project folder. You need Python 3 (`py -3 --version`) and a running local PostgreSQL server. If you're installing PostgreSQL, include **Command Line Tools** and keep the password you set for the `postgres` user. [PostgreSQL Windows installer](https://www.postgresql.org/download/windows/)

```powershell
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `$psql` to the path for your installation. These commands use the default port, `5432`, and prompt for your PostgreSQL password. Run the `CREATE DATABASE` command once.

```powershell
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
& $psql --version
& $psql -X -h localhost -p 5432 -U postgres -d postgres -c 'CREATE DATABASE ttc_delays;'
```

## 2. Prepare and import the data

```powershell
& .\.venv\Scripts\python.exe .\prepare_data.py
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -f .\sql\import.sql
```

The preparation step downloads any missing workbook into `data/` and writes `subway_delays_2024.csv` and `delay_codes.csv` there. It adds `source_row`, the original Excel row number, to each report. The SQL script creates the two permanent tables, reads the CSV files into temporary tables with `\copy`, and inserts the staged rows. `BEGIN` and `COMMIT` put the load in one transaction so an error rolls the import back. [PostgreSQL `psql` documentation](https://www.postgresql.org/docs/current/app-psql.html)

A fresh database should show `INSERT 0 26467` for the reports and `INSERT 0 200` for the code lookup.

## 3. Rerun the import and verify it

```powershell
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -f .\sql\import.sql
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -v ON_ERROR_STOP=1 -f .\sql\analysis.sql
```

The rerun reads the same CSV files and prints `INSERT 0 0` twice. A **primary key** requires each `source_row` to be unique. `ON CONFLICT (source_row) DO NOTHING` skips a row when its workbook position is already stored. The lookup uses the same approach with `delay_code` as its key. Each workbook row is kept, including rows that share the same reported values. The row numbers identify records within this 2024 workbook snapshot. [PostgreSQL `INSERT` documentation](https://www.postgresql.org/docs/current/sql-insert.html)

The first result from [analysis.sql](sql/analysis.sql) should show **26,467 imported rows**, **9,394 positive-delay rows**, **74,274 total delay minutes**, and dates from **2024-01-01** through **2024-12-31**. `COUNT(*)` counts all rows, while `FILTER` restricts just the second count to rows with positive delay minutes.

## 4. Read the two rankings

**Which stations have the most reported delays?** Read the second query in [analysis.sql](sql/analysis.sql).

- `WHERE delay_minutes > 0` counts reports that recorded a service delay. `LIKE '% STATION'` selects source labels that end in ` STATION`, a simple rule that leaves out yards, track segments, and truncated station names.
- `GROUP BY station` gathers rows with the same recorded label. `COUNT(*)` counts the reports in each group. Different labels for the same physical station can appear as separate rows.
- `ORDER BY reported_delays DESC, station` puts the largest counts first and breaks ties alphabetically. `LIMIT 10` displays the first ten. Kennedy BD leads with **353** reports, followed by Kipling (**351**) and Bloor (**350**).

**Which causes account for the most delay minutes?** Read the third query in [analysis.sql](sql/analysis.sql).

- `LEFT JOIN` looks up each TTC delay code's description. A report with a missing lookup entry keeps its original code, and `COALESCE` supplies the label `Unmapped TTC code`.
- `GROUP BY` creates one group per TTC code and its description. `SUM(delay_minutes)` adds up the service delay minutes in each group, and `COUNT(*)` shows how many reports contributed to that total. The workbook has a separate `Min Gap` column for the time between trains.
- `ORDER BY total_delay_minutes DESC` ranks causes by the sum. Disorderly Patron (`SUDP`) leads with **8,576 minutes**, followed by Passenger Other (`SUO`, **5,863 minutes**) and Unauthorized at Track Level (`SUUT`, **5,611 minutes**).

The station ranking measures how often a delay was reported at a given label. The cause ranking measures how much reported delay time accumulated under each code.

## 5. Build the analytics views with dbt

In the VS Code PowerShell terminal, run this from the project folder after importing the 2024 data. dbt Core requires Python 3.10 or newer. Enter the same PostgreSQL password used for the import when prompted. The supplied profile reads it from the current terminal session. [dbt PostgreSQL setup](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup)

```powershell
& .\.venv\Scripts\python.exe -m pip install -r .\dbt\requirements.txt
$env:DBT_ENV_SECRET_TTC_PASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host 'PostgreSQL password' -AsSecureString)).Password
& .\.venv\Scripts\dbt.exe build --project-dir .\dbt --profiles-dir .\dbt
Remove-Item Env:\DBT_ENV_SECRET_TTC_PASSWORD
```

The profile uses `localhost:5432`, the `postgres` user, and the `ttc_delays` database. If you changed those settings for the import, set `TTC_PG_HOST`, `TTC_PG_PORT`, `TTC_PG_USER`, or `TTC_PG_DATABASE` in PowerShell before building. The PostgreSQL user needs permission to read the imported tables and create the `analytics` schema.

dbt runs these SQL models in dependency order and runs their data tests. `source()` names a table loaded by the import. `ref()` names another model and tells dbt to build that dependency first. A view is a saved query you can read from PostgreSQL with `SELECT`. [dbt build command](https://docs.getdbt.com/reference/commands/build)

| View | What one row represents |
| --- | --- |
| `analytics.subway_delay_reports` | A TTC report with a cause description and a positive-delay flag |
| `analytics.station_delay_counts` | A recorded station label with its positive-delay report count |
| `analytics.cause_delay_minutes` | A TTC code and description with its total delay minutes and positive-delay report count |
| `analytics.daily_delay_totals` | An observed service date with its report counts and total delay minutes |

The tests check that each view's row identifier is unique and present. A separate SQL test checks that the daily view adds up to the totals from the loaded source tables. With only the 2024 archive loaded, those totals are **26,467 records**, **9,394 positive-delay reports**, and **74,274 minutes**. In a test query, returning a row signals a failure.

Use the `$psql` path from step 1 to check the modeled results.

```powershell
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -c 'SELECT * FROM analytics.station_delay_counts ORDER BY reported_delays DESC, station LIMIT 3;'
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -c 'SELECT * FROM analytics.cause_delay_minutes ORDER BY total_delay_minutes DESC, delay_code LIMIT 3;'
& $psql -X -h localhost -p 5432 -U postgres -d ttc_delays -c 'SELECT * FROM analytics.daily_delay_totals ORDER BY service_date LIMIT 7;'
```

`refresh_recent.py` loads the City's separate **TTC Subway Delay Data since 2025** resource. Run `dbt build` after the first refresh to include it in these views. `UNION ALL` appends the newer rows, and `report_id` combines the feed name and source ID because the two feeds can reuse the same numeric IDs. The cause summary groups descriptions that differ only in capitalization and keeps revised descriptions separate. The daily view provides a time series for evaluating a forecast. [City of Toronto TTC Subway Delay Data](https://open.toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/)

Contains information licensed under the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/).
