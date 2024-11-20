document.addEventListener('DOMContentLoaded', () => {
    const sliders = document.querySelectorAll('.slider-section input[type="range"]');
    const loanAmountValue = document.getElementById('loan-amount-value');
    const loanTermValue = document.getElementById('loan-term-value');
    const results = document.querySelectorAll('.result');
  
    sliders.forEach(slider => {
      slider.addEventListener('input', (e) => {
        const target = e.target;
        const valueDisplay = target.nextElementSibling;
        valueDisplay.textContent = target.value.toLocaleString();
  
        // Simulación de cálculo de resultados
        // Aquí deberías implementar tu lógica real de cálculo
        results.forEach(result => {
          result.classList.remove('updated');
          void result.offsetWidth; // Trigger reflow para reiniciar la animación
          result.classList.add('updated');
        });
      });
    });
  });
  