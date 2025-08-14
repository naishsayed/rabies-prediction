// script.js
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('predictForm');
  const resultCard = document.getElementById('resultCard');
  const riskLabel = document.getElementById('riskLabel');
  const riskAdvice = document.getElementById('riskAdvice');
  const probBar = document.getElementById('probBar');
  const loading = document.getElementById('loading');
  const resetBtn = document.getElementById('resetBtn');
  const backBtn = document.getElementById('backBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    loading.style.display = 'inline-flex';
    resultCard.style.display = 'none';

    const formData = new FormData(form);
    const payload = {};
    formData.forEach((v, k) => payload[k] = v);

    try {
      const res = await fetch('/predict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      const prob = data.probability; // 0..1
      const perc = Math.round(prob * 100);

      riskLabel.textContent = `Risk: ${data.risk}`;
      probBar.style.width = `${perc}%`;
      probBar.textContent = `${perc}%`;

      // color and advice
      if (data.risk === 'High') {
        probBar.classList.remove('bg-success');
        probBar.classList.add('bg-danger');
        riskAdvice.innerHTML = "<strong>Advice:</strong> High risk — seek medical attention immediately for PEP and wound care.";
      } else {
        probBar.classList.remove('bg-danger');
        probBar.classList.add('bg-success');
        riskAdvice.innerHTML = "<strong>Advice:</strong> Likely low risk, but monitor closely and consult healthcare if worried or symptoms appear.";
      }

      resultCard.style.display = 'block';
    } catch (err) {
      alert('Prediction failed — check server console for errors.');
      console.error(err);
    } finally {
      loading.style.display = 'none';
    }
  });

  resetBtn.addEventListener('click', () => form.reset());

  backBtn.addEventListener('click', () => {
    resultCard.style.display = 'none';
    form.reset();
  });
});
