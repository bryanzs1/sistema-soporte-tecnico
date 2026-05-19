// static/assistant-chat.js
// Maneja el chat del asistente: envía mensajes y muestra respuestas

document.addEventListener('DOMContentLoaded', function () {
  const chatForm = document.getElementById('assistantChatForm');
  const chatInput = document.getElementById('assistantChatInput');
  const chatBox = document.getElementById('assistantChatBox');
  if (!chatForm || !chatInput || !chatBox) return;

  function appendMessage(text, sender = 'user') {
    const msg = document.createElement('div');
    msg.className = `chat-message chat-message-${sender}`;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    appendMessage(message, 'user');
    chatInput.value = '';
    fetch('/assistant-chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ message })
    })
    .then(async response => {
      let data;
      try { data = await response.json(); } catch { data = {}; }
      if (response.ok && data.success) {
        appendMessage(data.reply || 'Sin respuesta.', 'assistant');
      } else {
        appendMessage(data.message || 'Error en el chat.', 'assistant');
      }
    })
    .catch(() => {
      appendMessage('Error de red. Intenta nuevamente.', 'assistant');
    });
  });
});
