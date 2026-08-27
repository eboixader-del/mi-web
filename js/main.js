// Menú móvil
const navToggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".nav");

if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  // En móvil, tocar un elemento con submenú lo despliega en vez de navegar
  document.querySelectorAll(".nav-item").forEach((item) => {
    const link = item.querySelector(":scope > .nav-link");
    const submenu = item.querySelector(".submenu");
    if (!submenu || !link) return;

    link.addEventListener("click", (e) => {
      if (window.matchMedia("(max-width: 860px)").matches) {
        e.preventDefault();
        item.classList.toggle("is-open");
      }
    });
  });
}

// Año automático en el footer
const yearEl = document.getElementById("year");
if (yearEl) {
  yearEl.textContent = new Date().getFullYear();
}

// Formulario de contacto: como el sitio es estático, se abre el cliente de correo
// con los datos ya rellenados en lugar de enviarlos a un servidor.
const contactForm = document.getElementById("contact-form");
if (contactForm) {
  contactForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = contactForm.name.value.trim();
    const email = contactForm.email.value.trim();
    const message = contactForm.message.value.trim();
    const status = document.getElementById("form-status");

    const subject = encodeURIComponent(`Contacto desde eboixader.es — ${name || "Sin nombre"}`);
    const body = encodeURIComponent(`${message}\n\n—\n${name}\n${email}`);

    window.location.href = `mailto:ernesto@fundacionflors.es?subject=${subject}&body=${body}`;

    if (status) {
      status.textContent = "Abriendo tu programa de correo…";
    }
  });
}
