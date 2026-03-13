(function () {
  function reviveIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function scrollToBottom(el) {
    if (!el) return;
    requestAnimationFrame(function () {
      el.scrollTop = el.scrollHeight;
    });
  }

  window.renderMarkdown = function (text) {
    if (window.marked) {
      return window.marked.parse(text || '');
    }
    return text || '';
  };

  window.copyText = function (text) {
    navigator.clipboard.writeText(text || '');
  };

  window.appShell = function () {
    return {
      mobileNavOpen: false,
      showScrollTop: false,
      init: function () {
        var self = this;
        window.addEventListener('scroll', function () {
          self.showScrollTop = window.scrollY > 300;
        });
      }
    };
  };

  function buildChatState(initial) {
    return {
      open: false,
      suggestionsOpen: true,
      sessionId: initial.sessionId || '',
      message: '',
      typing: false,
      messages: initial.messages || [],
      toggle: function () {
        this.open = !this.open;
        if (this.open) scrollToBottom(this.$refs.messages);
      },
      toggleSuggestions: function () {
        this.suggestionsOpen = !this.suggestionsOpen;
      },
      appendMessage: function (role, content) {
        this.messages.push({ id: Date.now() + Math.random(), role: role, content: content || '' });
        scrollToBottom(this.$refs.messages);
      },
      renderMarkdown: window.renderMarkdown,
      copyText: window.copyText,
      send: function () {
        var self = this;
        if (!self.message.trim()) return;
        var prompt = self.message.trim();
        self.appendMessage('user', prompt);
        self.message = '';
        self.typing = true;
        var assistant = { id: Date.now() + Math.random(), role: 'assistant', content: '' };
        self.messages.push(assistant);
        scrollToBottom(self.$refs.messages);
        var url = '/ai/chat/stream/?message=' + encodeURIComponent(prompt);
        if (self.sessionId) {
          url += '&session_id=' + encodeURIComponent(self.sessionId);
        }
        var evtSource = new EventSource(url);
        evtSource.onmessage = function (event) {
          var data = JSON.parse(event.data || '{}');
          if (data.session_id && !self.sessionId) {
            self.sessionId = String(data.session_id);
          }
          if (data.done) {
            self.typing = false;
            evtSource.close();
            return;
          }
          assistant.content += data.token || '';
          scrollToBottom(self.$refs.messages);
        };
        evtSource.onerror = function () {
          self.typing = false;
          assistant.content = assistant.content || 'Não foi possível concluir a resposta agora.';
          evtSource.close();
        };
      }
    };
  }

  window.aiWidget = function (initial) {
    return buildChatState(initial || {});
  };

  window.aiChatPage = function (initial) {
    return buildChatState(initial || {});
  };

  function setupConfirmModal() {
    var overlay = document.getElementById('confirm-overlay');
    var messageEl = document.getElementById('confirm-message');
    var cancelBtn = document.getElementById('confirm-cancel');
    var acceptBtn = document.getElementById('confirm-accept');
    if (!overlay || !messageEl || !cancelBtn || !acceptBtn) return;

    var pendingAction = null;
    document.body.addEventListener('submit', function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (!form.dataset.confirm) return;
      event.preventDefault();
      pendingAction = function () { form.submit(); };
      messageEl.textContent = form.dataset.confirm;
      overlay.classList.remove('hidden');
      overlay.classList.add('flex');
    });

    cancelBtn.addEventListener('click', function () {
      overlay.classList.add('hidden');
      overlay.classList.remove('flex');
      pendingAction = null;
    });
    acceptBtn.addEventListener('click', function () {
      overlay.classList.add('hidden');
      overlay.classList.remove('flex');
      if (pendingAction) pendingAction();
      pendingAction = null;
    });
  }

  document.addEventListener('DOMContentLoaded', reviveIcons);
  document.body.addEventListener('htmx:afterSwap', reviveIcons);
  document.addEventListener('DOMContentLoaded', setupConfirmModal);
})();
