// static/access-modal.js
// Maneja el cierre automático del modal y muestra alertas tras enviar el formulario de acceso

document.addEventListener('DOMContentLoaded', function () {
  const accessForm = document.getElementById('accessRequestForm');
  const accessModal = document.getElementById('accessModal');

  function showAlert(message, type = 'success') {
    // Busca o crea el contenedor de alertas
    let alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
      alertContainer = document.createElement('div');
      alertContainer.className = 'alert-container';
      document.body.prepend(alertContainer);
    }
    // Crea la alerta
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    alertContainer.appendChild(alert);
    setTimeout(() => { alert.classList.remove('show'); alert.remove(); }, 6000);
  }

  if (accessForm) {
    accessForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const formData = new FormData(accessForm);
      fetch(accessForm.action, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(async response => {
        let data;
        try { data = await response.json(); } catch { data = {}; }
        if (response.ok && data.success) {
          showAlert(data.message || '¡Solicitud enviada correctamente!', 'success');
          accessForm.reset();
          const modal = bootstrap.Modal.getOrCreateInstance(accessModal);
          modal.hide();
        } else {
          showAlert(data.message || 'Ocurrió un error al enviar la solicitud.', 'danger');
        }
      })
      .catch(() => {
        showAlert('Ocurrió un error de red. Intenta nuevamente.', 'danger');
      });
    });

    // Fix: transición robusta entre modales acceso/login
    const loginLink = document.querySelector('#accessModal [href="#loginModal"]');
    if (loginLink) {
      loginLink.addEventListener('click', function (e) {
        e.preventDefault();
        const modal = bootstrap.Modal.getOrCreateInstance(accessModal);
        modal.hide();
        // Espera a que termine de cerrarse el modal de acceso
        accessModal.addEventListener('hidden.bs.modal', function openLoginOnce() {
          const loginModal = document.getElementById('loginModal');
          if (loginModal) {
            const loginBsModal = bootstrap.Modal.getOrCreateInstance(loginModal);
            loginBsModal.show();
          }
          // Solo una vez
          accessModal.removeEventListener('hidden.bs.modal', openLoginOnce);
        });
      });
    }
  }
});
