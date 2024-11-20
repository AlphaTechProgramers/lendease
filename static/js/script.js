// script.js

document.addEventListener("DOMContentLoaded", function() {
  const themeToggleButton = document.getElementById("theme-toggle");
  const body = document.body;

  // Verificar el tema guardado en localStorage
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "dark") {
    body.classList.add("dark-mode");
  }

  // Alternar tema al hacer clic en el botón
  themeToggleButton.addEventListener("click", () => {
    body.classList.toggle("dark-mode");

    // Guardar la preferencia en localStorage
    if (body.classList.contains("dark-mode")) {
      localStorage.setItem("theme", "dark");
    } else {
      localStorage.setItem("theme", "light");
    }
  });
});
