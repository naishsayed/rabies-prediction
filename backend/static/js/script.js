// Wizard controls
const step1 = document.getElementById('step-1');
const step2 = document.getElementById('step-2');
document.getElementById('nextBtn').addEventListener('click', () => {
  step1.classList.add('animate__animated', 'animate__fadeOutLeft');
  setTimeout(() => {
    step1.classList.add('d-none');
    step2.classList.remove('d-none', 'animate__fadeOutLeft');
    step2.classList.add('animate__animated', 'animate__fadeInRight');
  }, 400);
});

// Elements
const resultEmpty = document.getElementById('resultEmpty');
const resultPanel = document.getElementById('resultPanel');
const riskText = document.getElementById('riskText');
const probBadge = document.getElementById('probBadge');
const probBar = document.getElementById('probBar');
const adviceText = document.getElementById('adviceText');
const historyBody = document.getElementById('historyBody');

// =======================================================
// == MODIFICATION: Get references to the buttons       ==
// =======================================================
const predictBtn = document.getElementById('predictBtn');
const resetBtn = document.getElementById('resetBtn');

const loaderOverlay = document.createElement('div');
loaderOverlay.id = "loaderOverlay";
loaderOverlay.innerHTML = `<div class="spinner-border text-light" role="status"><span class="visually-hidden">Loading...</span></div>`;
document.body.appendChild(loaderOverlay);

// Chart.js donut (created lazily)
let donut = null;

function resetForm() {
    // =======================================================
    // == MODIFICATION: Swap buttons back to original state ==
    // =======================================================
    resetBtn.classList.add('d-none');
    predictBtn.classList.remove('d-none');

    // 1. Reset all form inputs to their default state
    document.querySelectorAll('#step-1 select, #step-2 select').forEach(select => select.selectedIndex = 0);
    document.querySelector('input[name="time_to_clean_minutes"]').value = 30;
    document.querySelector('input[name="age"]').value = 30;

    // 2. Reset the result panel to its initial empty state
    resultPanel.classList.add('d-none');
    resultEmpty.classList.remove('d-none');
    if (donut) {
        donut.destroy();
        donut = null;
    }

    // 3. Animate back to Step 1
    step2.classList.add('animate__animated', 'animate__fadeOutRight');
    setTimeout(() => {
        step2.classList.add('d-none');
        step1.classList.remove('d-none', 'animate__fadeOutRight');
        step1.classList.add('animate__animated', 'animate__fadeInLeft');
    }, 400);
}

// Attach the new resetForm function to our new button
resetBtn.addEventListener('click', resetForm);

// Collect all form inputs by name from both steps
function getPayload() {
  const payload = {};
  document.querySelectorAll('#step-1 select, #step-1 input, #step-2 select, #step-2 input')
    .forEach(el => payload[el.name] = el.value);
  payload.time_to_clean_minutes = Number(payload.time_to_clean_minutes || 30);
  payload.age = Number(payload.age || 30);
  return payload;
}

// Map probability to UX category (Low/Medium/High) for nicer display
function bandFromProb(p) {
  if (p < 0.34) return 'Low';
  if (p < 0.67) return 'Medium';
  return 'High';
}

// Update UI based on prediction
function updateResultUI(labelFromServer, prob) {
  const probPct = Math.round(prob * 100);
  const band = bandFromProb(prob);
  riskText.textContent = `Risk: ${band}`;
  probBadge.textContent = `${probPct}%`;
  probBar.style.width = `${probPct}%`;
  probBar.textContent = `${probPct}%`;

  probBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
  riskText.classList.remove('text-low', 'text-med', 'text-high');
  probBadge.classList.remove('badge-low', 'badge-med', 'badge-high');

  if (band === 'High') {
    probBar.classList.add('bg-danger');
    riskText.classList.add('text-high');
    probBadge.classList.add('badge-high');
    adviceText.innerHTML = "<strong>Advice:</strong> High risk — seek immediate medical attention for PEP and professional wound care.";
  } else if (band === 'Medium') {
    probBar.classList.add('bg-warning');
    riskText.classList.add('text-med');
    probBadge.classList.add('badge-med');
    adviceText.innerHTML = "<strong>Advice:</strong> Moderate risk — consult a healthcare professional promptly; PEP may be recommended.";
  } else {
    probBar.classList.add('bg-success');
    riskText.classList.add('text-low');
    probBadge.classList.add('badge-low');
    adviceText.innerHTML = "<strong>Advice:</strong> Likely low risk — monitor closely and follow medical advice. Seek care if symptoms appear.";
  }

  if (typeof Chart !== "undefined") {
    const ctx = document.getElementById('probChart').getContext('2d');
    if (donut) donut.destroy();
    const centerTextPlugin = {
      id: 'centerText',
      beforeDraw(chart) {
        const { ctx, chartArea: { width, height } } = chart;
        ctx.save();
        ctx.font = "bold 20px Poppins";
        ctx.fillStyle = "#fff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${probPct}%`, width / 2, height / 2);
        ctx.restore();
      }
    };
    donut = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['High-risk probability', 'Other'],
        datasets: [{
          data: [probPct, 100 - probPct],
          borderWidth: 0,
          backgroundColor: [
            band === 'High' ? '#c62828' : (band === 'Medium' ? '#ff8f00' : '#2e7d32'),
            'rgba(255,255,255,0.12)'
          ],
          hoverOffset: 4
        }]
      },
      options: { cutout: '72%', plugins: { legend: { display: false } } },
      plugins: [centerTextPlugin]
    });
  } else {
    console.warn("Chart.js not loaded — skipping donut chart rendering.");
  }
  resultEmpty.classList.add('d-none');
  resultPanel.classList.remove('d-none');
  resultPanel.classList.add('animate__animated', 'animate__fadeInUp');
  if (window.innerWidth <= 768) {
    resultPanel.scrollIntoView({ behavior: "smooth" });
  }
}

function showLoader() { loaderOverlay.style.display = "flex"; }
function hideLoader() { loaderOverlay.style.display = "none"; }

// Predict button → call Flask /predict
predictBtn.addEventListener('click', async () => {
  const payload = getPayload();
  showLoader();
  try {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Server returned ' + res.status);
    const data = await res.json();
    const p = Number(data.probability ?? 0);
    updateResultUI(data.risk, p);
    const now = new Date();
    const formattedDate = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
    const row = document.createElement('tr');
    row.innerHTML = `<td class="text-secondary">${formattedDate}</td><td>${payload.bite_location}</td><td>${payload.bite_severity}</td><td>${data.risk}</td><td>${Math.round(p*100)}%</td>`;
    historyBody.prepend(row);

    // =======================================================
    // == MODIFICATION: Swap buttons after successful prediction
    // =======================================================
    predictBtn.classList.add('d-none');
    resetBtn.classList.remove('d-none');

  } catch (e) {
    console.error(e);
    alert('Prediction failed. Please check if the Flask server is running and model.joblib is loaded.');
  } finally {
    hideLoader();
  }
});