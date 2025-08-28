

const rangeSel = document.getElementById('range');
const customSpan = document.getElementById('custom');
const loadBtn = document.getElementById('load');
const toggleView = document.getElementById('toggleView');
const viewLabel = document.getElementById('viewLabel');
const tableWrap = document.getElementById('tableWrap');
const chartWrap = document.getElementById('chartWrap');
const tbody = document.querySelector('#tbl tbody');
const chartCanvas = document.getElementById('chart');




rangeSel.addEventListener('change', () => { 
    customBox.style.display = rangeSel.value === 'custom' ? 'flex' : 'none';


})

toggleView.addEventListener('change', () => {
  const chartMode = toggleView.checked;
  chartWrap.style.display = chartMode ? 'none' : '';
  tableWrap.style.display = chartMode ? '' : 'none';
  viewLabel.textContent = chartMode ? ' Table view' : 'Chart view';
  if (viewLabel.textContent === chartMode) {
    load();
  }

})

async function load() {
    const params = new URLSearchParams();
    params.set('range', rangeSel.value);
    if (rangeSel.value === 'custom') {
        const s = document.getElementById('start').value;
        const e = document.getElementById('end').value;
        if (s) params.set('start', s);
        if (e) params.set('end', e);
    }

    const resp = await fetch('/api/history?' + params.toString());
    const data = await resp.json();
    const tbody = document.querySelector('#tbl tbody');
    tbody.innerHTML = '';
    for (const r of data) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${r.server_id}</td>
          <td>${new Date(r.ts).toLocaleString()}</td>
          <td>${r.up ? '✓' : '✗'}</td>
          <td>${r.cpu_usage ?? ''}</td>
          <td>${r.memory ?? ''}</td>
          <td>${r.disk ?? ''}</td>
          <td>${r.gpu_usage ?? ''}</td>
        `;
        tbody.appendChild(tr);
      }
}

// document.getElementById('load').addEventListener('click', load);
// Auto-load on first visit
load();


