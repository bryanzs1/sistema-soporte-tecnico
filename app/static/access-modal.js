// static/access-modal.js
// Maneja el cierre automático del modal y muestra alertas tras enviar el formulario de acceso

document.addEventListener('DOMContentLoaded', function () {
  const accessForm = document.getElementById('accessRequestForm');
  const accessModal = document.getElementById('accessModal');

  if (accessForm) {
    accessForm.addEventListener('submit', function (e) {
      // Permite el submit normal para que Flask procese y redirija
      // Pero al volver, si hay un mensaje flash, cierra el modal
      setTimeout(() => {
        // Si hay un mensaje flash visible, cierra el modal
        const flash = document.querySelector('.alert');
        if (flash && accessModal.classList.contains('show')) {
          const modal = bootstrap.Modal.getOrCreateInstance(accessModal);
          modal.hide();
        }
      }, 500);
    });
  }

  // Opcional: Cierra el modal si se navega a otra página
  window.addEventListener('pageshow', function () {
    if (accessModal.classList.contains('show')) {
      const modal = bootstrap.Modal.getOrCreateInstance(accessModal);
      modal.hide();
    }
  });
});
