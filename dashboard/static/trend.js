const dayMs = 86_400_000;
const canvas = document.querySelector('#trend-chart');
const ctx = canvas.getContext('2d');
const tooltip = document.querySelector('#tooltip');
const summary = document.querySelector('#trend-description');
const buttons = document.querySelectorAll('.range button');
const formatter = new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const numbers = new Intl.NumberFormat('en-CA');
const days = JSON.parse(document.querySelector('#daily-data').textContent).map(row => ({
  ...row,
  time: Date.parse(row.date),
}));

let visible = days;
let hover = null;
let layout;

function renderChart() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;
  ctx.scale(scale, scale);

  const peak = visible.reduce((max, day) => Math.max(max, day.minutes), 0);
  const top = Math.max(4, Math.ceil(peak / 100) * 100);
  const first = visible[0].time;
  const last = visible.at(-1).time;
  const left = 55;
  const right = width - 12;
  const floor = height - 31;
  const x = time => first === last ? (left + right) / 2 : left + (right - left) * (time - first) / (last - first);
  const y = value => floor - (floor - 10) * value / top;
  layout = { left, right, x, y };

  ctx.font = '14px Segoe UI, sans-serif';
  ctx.fillStyle = '#c3d1d6';
  ctx.textAlign = 'right';
  ctx.strokeStyle = '#3c5560';
  for (let tick = 0; tick <= 4; tick++) {
    const value = top * tick / 4;
    const level = y(value);
    ctx.beginPath();
    ctx.moveTo(left, level);
    ctx.lineTo(right, level);
    ctx.stroke();
    ctx.fillText(numbers.format(value), left - 7, level + 4);
  }

  ctx.fillText(formatter.format(last), right, height - 7);
  if (first !== last) {
    ctx.textAlign = 'left';
    ctx.fillText(formatter.format(first), left, height - 7);
  }

  ctx.strokeStyle = '#8edbd5';
  ctx.lineJoin = 'round';
  ctx.lineWidth = 1.45;
  ctx.beginPath();
  visible.forEach((day, index) => {
    if (index === 0 || day.time - visible[index - 1].time > dayMs) ctx.moveTo(x(day.time), y(day.minutes));
    else ctx.lineTo(x(day.time), y(day.minutes));
  });
  ctx.stroke();

  const dot = hover || (visible.length === 1 ? visible[0] : null);
  if (dot) {
    ctx.beginPath();
    ctx.arc(x(dot.time), y(dot.minutes), 4, 0, Math.PI * 2);
    ctx.fillStyle = '#f5967c';
    ctx.fill();
  }
}

function selectRange(limit) {
  const end = days.at(-1).time;
  visible = limit ? days.filter(day => day.time >= end - (limit - 1) * dayMs) : days;
  const peak = visible.reduce((best, day) => day.minutes > best.minutes ? day : best);
  summary.textContent = `${numbers.format(visible.length)} reported dates · Peak ${numbers.format(peak.minutes)} min on ${formatter.format(peak.time)}`;
  hover = null;
  tooltip.hidden = true;
  renderChart();
}

buttons.forEach(button => button.addEventListener('click', () => {
  buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  selectRange(Number(button.dataset.days));
}));

canvas.addEventListener('pointermove', event => {
  if (!layout) return;
  const mouseX = event.clientX - canvas.getBoundingClientRect().left;
  hover = visible.reduce((closest, day) =>
    Math.abs(layout.x(day.time) - mouseX) < Math.abs(layout.x(closest.time) - mouseX) ? day : closest);
  tooltip.textContent = `${formatter.format(hover.time)} · ${numbers.format(hover.minutes)} min`;
  tooltip.hidden = false;
  tooltip.style.left = `${Math.max(0, Math.min(layout.x(hover.time), canvas.clientWidth - tooltip.offsetWidth))}px`;
  tooltip.style.top = `${Math.max(0, layout.y(hover.minutes) - tooltip.offsetHeight - 9)}px`;
  renderChart();
});

canvas.addEventListener('pointerleave', () => {
  hover = null;
  tooltip.hidden = true;
  renderChart();
});

document.querySelector('.range').hidden = false;
selectRange(0);
new ResizeObserver(renderChart).observe(canvas);
