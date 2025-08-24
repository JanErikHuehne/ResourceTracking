async function updateChart(){


     // Pick ONE of these depending on the option you chose:
    const spinner = document.getElementById('spinner');             // inline

    // SHOW
    if (spinner) spinner.hidden = false;
   
    const response = await fetch('/cpu2');
    const data = await response.json();
    
    const container = document.getElementById('res-grid');
    console.log('res-grid exists?', !!document.getElementById('res-grid'));
    console.log(container);
    const map = new Map(Object.entries(data));
    map.entries(data).forEach(([ip, metrics]) => {
  

        function makeErrorRow(ip, err) {
            const cell = document.createElement("div");
            cell.className = "res-error";
            cell.textContent =
              err === "timeout"
                ? `NOT RESPONDING — timeout`
                : `NOT RESPONDING${err ? ` — ${err}` : ""}`;
            return cell;
        }
        function isFiniteNumber(x) {
            return typeof x === "number" && Number.isFinite(x);
          }
        function makeIPCell(ip) {
            const cell = document.createElement("div");
            cell.className = "res-ip";    // CSS: grid-column: 1 / -1
            cell.textContent = ip;
            return cell;
        }

        function makeMetricCell(label, value) {
            const cell = document.createElement("div");
            cell.className = "res-cell";
            cell.dataset.server = ip;
            if (value <= 20) {
                cell.innerHTML = `
                <span class="metric-label">${label}</span>
                <div class="rb" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}">
                    <div class="rb-track">
                    <span class="rb-seg low" style="--w:${value}"></span>
                    <span class="rb-seg idle" style="--w:${100 - value}"></span>
                    </div>
                    <span class="rb-pct">${value}%</span>
                </div>
                `;
            }
            else if (value >= 80) {
                cell.innerHTML = `
                <span class="metric-label">${label}</span>
                <div class="rb" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}">
                    <div class="rb-track">
                    <span class="rb-seg high" style="--w:${value}"></span>
                    <span class="rb-seg idle" style="--w:${100 - value}"></span>
                    </div>
                    <span class="rb-pct">${value}%</span>
                </div>
                `;
            }
            else {
                cell.innerHTML = `
                <span class="metric-label">${label}</span>
                <div class="rb" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}">
                    <div class="rb-track">
                    <span class="rb-seg medium" style="--w:${value}"></span>
                    <span class="rb-seg idle" style="--w:${100 - value}"></span>
                    </div>
                    <span class="rb-pct">${value}%</span>
                </div>
                `;
            }

           
            return cell;
        }

        function makePlaceholderCell(label) {
            const cell = document.createElement("div");
            cell.className = "res-cell placeholder";
            cell.innerHTML = `
                <span class="metric-label">${label}</span>
                <div class="rb">
                <div class="rb-track"></div>
                <span class="rb-pct">N/A</span>
                </div>
            `;
            return cell;
        }

  

        // add CPU, MEM, DISK
        container.appendChild(makeIPCell(ip));


        if (metrics && Object.prototype.hasOwnProperty.call(metrics, "error")) {
            container.appendChild(makeErrorRow(ip, metrics.error));
            return; // exits THIS iteration only
          }
        container.appendChild(makeMetricCell("CPU", metrics.cpu_usage));
        container.appendChild(makeMetricCell("MEM", Math.round(metrics.memory)));
        container.appendChild(makeMetricCell("DISK", Math.round(metrics.disk)));
        console.log("gpu_usage", ip, metrics.hasOwnProperty("gpu_usage"))
        if (metrics.hasOwnProperty("gpu_usage")) {
            container.appendChild(makeMetricCell("GPU", Math.round(metrics.gpu_usage)));
        // safe check on own keys
        }
        else {
            container.appendChild(makePlaceholderCell("GPU"));
        }


    });
    if (spinner) spinner.hidden = true;

}
document.addEventListener('DOMContentLoaded', () => {
updateChart();
});



