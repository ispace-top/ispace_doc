/**
 * iSpaceDoc Components
 * Toast, Modal, confirm, FormValidator
 * No jQuery dependency.
 */
window.iSpaceDoc = window.iSpaceDoc || {};

/* ================================================================
   Toast
   ================================================================ */
window.iSpaceDoc.Toast = (() => {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.getElementById('ispace-toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'ispace-toast-container';
        container.className = 'ispace-toast-container';
        document.body.appendChild(container);
      }
    }
    return container;
  }

  function show(message, type = 'info', duration = 4000) {
    const c = getContainer();
    const toast = document.createElement('div');
    toast.className = `ispace-toast ispace-toast-${type}`;
    toast.innerHTML = `
      <div class="ispace-toast-body">
        <div class="ispace-toast-description">${escapeHTML(message)}</div>
      </div>
      <button class="ispace-toast-close" onclick="this.closest('.ispace-toast').remove()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `;
    c.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add('ispace-removing');
        setTimeout(() => toast.remove(), 200);
      }, duration);
    }
  }

  function success(message, duration) { show(message, 'success', duration); }
  function warning(message, duration) { show(message, 'warning', duration); }
  function error(message, duration) { show(message, 'error', duration); }
  function info(message, duration) { show(message, 'info', duration); }

  function escapeHTML(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  return { show, success, warning, error, info };
})();

window.showToast = window.iSpaceDoc.Toast.show;
window.showSuccess = window.iSpaceDoc.Toast.success;
window.showWarning = window.iSpaceDoc.Toast.warning;
window.showError = window.iSpaceDoc.Toast.error;
window.showInfo = window.iSpaceDoc.Toast.info;

/* ================================================================
   Modal
   ================================================================ */
window.iSpaceDoc.Modal = (() => {
  function open(backdropEl) {
    if (typeof backdropEl === 'string') {
      backdropEl = document.getElementById(backdropEl);
    }
    if (backdropEl) {
      backdropEl.classList.add('ispace-active');
      document.body.style.overflow = 'hidden';
    }
  }

  function close(backdropEl) {
    if (typeof backdropEl === 'string') {
      backdropEl = document.getElementById(backdropEl);
    }
    if (backdropEl) {
      backdropEl.classList.remove('ispace-active');
      document.body.style.overflow = '';
    }
  }

  function initAll() {
    document.querySelectorAll('.ispace-modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) close(backdrop);
      });
      backdrop.querySelectorAll('[data-ispace-modal-close]').forEach(btn => {
        btn.addEventListener('click', () => close(backdrop));
      });
    });
  }

  document.addEventListener('DOMContentLoaded', initAll);

  return { open, close };
})();

/* ================================================================
   confirm dialog — returns Promise<boolean>
   Usage:
     await iSpaceDoc.confirm('确定删除？')                         // default
     await iSpaceDoc.confirm('确定删除？', { variant: 'danger' }) // danger (red button)
     await iSpaceDoc.confirm({ message: '...', title: '...' })   // object form
   ================================================================ */
window.iSpaceDoc.confirm = function (message, options = {}) {
  // Support object-first form: iSpaceDoc.confirm({ message, title, ... })
  if (typeof message === 'object' && message !== null) {
    options = message;
    message = options.message || '';
  }
  return new Promise((resolve) => {
    const title = options.title || '确认操作';
    const variant = options.variant || 'default';
    const confirmText = options.confirmText || '确认';
    const cancelText = options.cancelText || '取消';

    var isDanger = variant === 'danger' || variant === 'warning';
    var confirmClass = isDanger ? 'ispace-btn ispace-btn-danger' : 'ispace-btn ispace-btn-primary';

    var iconSvg = '';
    if (variant === 'danger') {
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--ispace-color-danger-500)" stroke-width="2" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    } else if (variant === 'warning') {
      iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--ispace-color-warning-500)" stroke-width="2" style="flex-shrink:0;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    }

    var bodyContent = iconSvg
      ? '<div style="display:flex;align-items:flex-start;gap:12px;"><div style="flex-shrink:0;">' + iconSvg + '</div><p class="ispace-text-sm ispace-text-secondary">' + escapeHTML(message) + '</p></div>'
      : '<p class="ispace-text-sm ispace-text-secondary">' + escapeHTML(message) + '</p>';

    var backdrop = document.createElement('div');
    backdrop.className = 'ispace-modal-backdrop';
    backdrop.innerHTML =
      '<div class="ispace-modal ispace-modal-sm">' +
        '<div class="ispace-modal-header">' +
          '<h3 class="ispace-modal-title">' + escapeHTML(title) + '</h3>' +
          '<button class="ispace-modal-close" data-ispace-modal-close>' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
              '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' +
            '</svg>' +
          '</button>' +
        '</div>' +
        '<div class="ispace-modal-body">' + bodyContent + '</div>' +
        '<div class="ispace-modal-footer">' +
          '<button class="ispace-btn ispace-btn-secondary" data-action="cancel">' + cancelText + '</button>' +
          '<button class="' + confirmClass + '" data-action="confirm">' + confirmText + '</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(backdrop);

    function cleanup() {
      backdrop.classList.remove('ispace-active');
      setTimeout(function () { backdrop.remove(); }, 300);
      document.removeEventListener('keydown', onKeydown);
    }

    function onKeydown(e) {
      if (e.key === 'Escape') { cleanup(); resolve(false); }
    }

    requestAnimationFrame(function () {
      backdrop.classList.add('ispace-active');
      var confirmBtn = backdrop.querySelector('[data-action="confirm"]');
      if (confirmBtn) confirmBtn.focus();
    });

    backdrop.querySelector('[data-action="confirm"]').addEventListener('click', function () {
      cleanup();
      resolve(true);
    });
    backdrop.querySelector('[data-action="cancel"]').addEventListener('click', function () {
      cleanup();
      resolve(false);
    });
    backdrop.addEventListener('click', function (e) {
      if (e.target === backdrop) {
        cleanup();
        resolve(false);
      }
    });
    document.addEventListener('keydown', onKeydown);
  });
};

window.confirm = window.iSpaceDoc.confirm;

/* ================================================================
   Confirm with CAPTCHA (high-risk deletion)
   ================================================================ */
window.iSpaceDoc.confirmDeleteWithCaptcha = function (opts) {
  return new Promise(function(resolve) {
    var docName = opts.docName || '';
    var totalChildren = opts.totalChildren || 0;
    var directChildren = opts.directChildren || [];
    
    var csrf = opts.csrfToken || '';

    function esc(str) {
      if (!str) return '';
      var d = document.createElement('div');
      d.textContent = str;
      return d.innerHTML;
    }

    var childrenHtml = '';
    if (directChildren.length > 0) {
      childrenHtml = '<div style="max-height:120px;overflow-y:auto;margin:8px 0;padding:8px;background:var(--ispace-color-surface-100);border-radius:6px;font-size:12px;">';
      directChildren.forEach(function(c) {
        childrenHtml += '<div style="padding:2px 0;color:var(--ispace-color-text-secondary);">• ' + esc(c.name) + '</div>';
      });
      if (totalChildren > directChildren.length) {
        childrenHtml += '<div style="padding:2px 0;color:var(--ispace-color-text-quaternary);">... 还有 ' + (totalChildren - directChildren.length) + ' 个子文档</div>';
      }
      childrenHtml += '</div>';
    }

    var container = document.getElementById('ispace-modals-container');
    var backdrop = document.createElement('div');
    backdrop.className = 'ispace-modal-backdrop ispace-active';
    backdrop.innerHTML = '<div class="ispace-modal ispace-modal-sm ispace-active">'
      + '<div class="ispace-modal-header" style="background:var(--ispace-color-error);color:#fff;border-radius:8px 8px 0 0;">'
      + '<div class="ispace-modal-title" style="display:flex;align-items:center;gap:8px;">'
      + '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
      + '高危操作确认</div></div>'
      + '<div class="ispace-modal-body">'
      + '<p style="color:var(--ispace-color-error);font-weight:600;margin:0 0 8px;">'
      + (isProject ? '此操作将删除整个项目《' + esc(docName) + '》及其所有 ' + totalChildren + ' 篇文档！' : '此操作将把《' + esc(docName) + '》及其 ' + totalChildren + ' 个子文档一并移入回收站。')
      + '</p>'
      + childrenHtml
      + '<p style="font-size:13px;color:var(--ispace-color-text-tertiary);margin:8px 0;">请输入下方验证码以确认删除：</p>'
      + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
      + '<img id="captcha-img" src="/delete-verify/image/?t=' + Date.now() + '" style="height:40px;border:1px solid var(--ispace-color-border);border-radius:4px;cursor:pointer;" onclick="this.src=\'/delete-verify/image/?t=\'+Date.now()" title="点击刷新验证码">'
      + '<a href="javascript:void(0)" onclick="document.getElementById(\'captcha-img\').src=\'/delete-verify/image/?t=\'+Date.now()" style="font-size:12px;color:var(--ispace-color-brand-600);white-space:nowrap;">换一张</a>'
      + '</div>'
      + '<input type="text" id="captcha-input" class="ispace-form-input" placeholder="请输入4位验证码" maxlength="4" autocomplete="off" style="width:120px;">'
      + '<span id="captcha-error" style="color:var(--ispace-color-error);font-size:12px;margin-left:8px;display:none;"></span>'
      + '</div>'
      + '<div class="ispace-modal-footer">'
      + '<button class="ispace-btn ispace-btn-secondary" id="captcha-cancel">取消</button>'
      + '<button class="ispace-btn ispace-btn-danger" id="captcha-confirm" disabled>确认删除</button>'
      + '</div></div>';

    container.appendChild(backdrop);

    var confirmBtn = backdrop.querySelector('#captcha-confirm');
    var cancelBtn = backdrop.querySelector('#captcha-cancel');
    var input = backdrop.querySelector('#captcha-input');
    var errorEl = backdrop.querySelector('#captcha-error');
    var verifying = false;

    function cleanup() {
      backdrop.classList.remove('ispace-active');
      setTimeout(function() { backdrop.remove(); }, 200);
    }

    input.addEventListener('input', function() {
      confirmBtn.disabled = input.value.length !== 4;
      errorEl.style.display = 'none';
    });

    cancelBtn.addEventListener('click', function() { cleanup(); resolve(false); });
    backdrop.addEventListener('click', function(e) {
      if (e.target === backdrop) { cleanup(); resolve(false); }
    });

    confirmBtn.addEventListener('click', async function() {
      if (verifying) return;
      verifying = true;
      confirmBtn.disabled = true;
      confirmBtn.textContent = '验证中...';

      try {
        var vForm = new FormData();
        vForm.append('csrfmiddlewaretoken', csrf);
        vForm.append('code', input.value);
        var vResp = await fetch('/delete-verify/check/', { method: 'POST', body: vForm });
        var vResult = await vResp.json();
        if (vResult.status) {
          cleanup(); resolve(true);
        } else {
          errorEl.textContent = vResult.data || '验证码错误';
          errorEl.style.display = '';
          document.getElementById('captcha-img').src = '/delete-verify/image/?t=' + Date.now();
          input.value = '';
          confirmBtn.disabled = true;
          confirmBtn.textContent = '确认删除';
          verifying = false;
        }
      } catch (e) {
        errorEl.textContent = '网络错误';
        errorEl.style.display = '';
        verifying = false;
        confirmBtn.disabled = false;
        confirmBtn.textContent = '确认删除';
      }
    });
  });
};

/* ================================================================
   FormValidator
   ================================================================ */
window.iSpaceDoc.FormValidator = class {
  constructor(form) {
    this.form = form;
    this.rules = [];
    this._bindEvents();
  }

  addRule(fieldName, validators) {
    this.rules.push({ fieldName, validators });
    return this;
  }

  _bindEvents() {
    this.form.addEventListener('input', (e) => {
      const field = e.target.closest('[name]');
      if (field) this._validateField(field.name);
    });

    this.form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (this.validateAll()) {
        this.form.dispatchEvent(new CustomEvent('form:valid'));
      }
    });
  }

  _getRule(fieldName) {
    return this.rules.find(r => r.fieldName === fieldName);
  }

  _validateField(fieldName) {
    const rule = this._getRule(fieldName);
    if (!rule) return true;

    const field = this.form.querySelector(`[name="${fieldName}"]`);
    if (!field) return true;

    const value = field.value.trim();
    let error = null;

    for (const v of rule.validators) {
      if (typeof v === 'function') {
        error = v(value);
      } else if (v.type === 'required' && !value) {
        error = v.message || '此字段为必填项';
      } else if (v.type === 'minLength' && value.length < v.value) {
        error = v.message || `最少输入 ${v.value} 个字符`;
      } else if (v.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        error = v.message || '请输入有效的邮箱地址';
      }
      if (error) break;
    }

    const group = field.closest('.ispace-form-group');
    const errorEl = group ? group.querySelector('.ispace-form-error-text') : null;

    if (error) {
      field.classList.add('ispace-error');
      if (group) group.classList.add('ispace-has-error');
      if (errorEl) errorEl.textContent = error;
    } else {
      field.classList.remove('ispace-error');
      if (group) group.classList.remove('ispace-has-error');
      if (errorEl) errorEl.textContent = '';
    }

    return !error;
  }

  validateAll() {
    let valid = true;
    for (const rule of this.rules) {
      if (!this._validateField(rule.fieldName)) {
        valid = false;
      }
    }
    return valid;
  }
};

/* ================================================================
   @Mention User Selector
   ================================================================ */
window.iSpaceDoc.MentionSelector = class {
  constructor(textarea, options = {}) {
    this.textarea = textarea;
    this.options = Object.assign({ debounce: 300, minChars: 0 }, options);
    this.dropdown = null;
    this.candidates = [];
    this.selectedIndex = -1;
    this.searchTimer = null;
    this.mentionStart = -1;
    this._attach();
  }

  _attach() {
    this.textarea.addEventListener('input', this._onInput.bind(this));
    this.textarea.addEventListener('keydown', this._onKeydown.bind(this));
    this.textarea.addEventListener('blur', () => { setTimeout(() => this._hide(), 200); });
    document.addEventListener('click', (e) => {
      if (this.dropdown && !this.dropdown.contains(e.target) && e.target !== this.textarea) {
        this._hide();
      }
    });
  }

  _onInput() {
    var val = this.textarea.value;
    var pos = this.textarea.selectionStart;
    // Find the last @ before cursor that starts a mention
    var atIdx = -1;
    for (var i = pos - 1; i >= 0; i--) {
      if (val[i] === '@') { atIdx = i; break; }
      if (val[i] === ' ' || val[i] === '\n') break;
    }
    if (atIdx === -1) { this._hide(); return; }
    // Check that @ is at word boundary
    if (atIdx > 0 && val[atIdx - 1] !== ' ' && val[atIdx - 1] !== '\n') { this._hide(); return; }
    var query = val.substring(atIdx + 1, pos);
    if (query.includes(' ')) { this._hide(); return; }
    if (query.length < this.options.minChars) { this._hide(); return; }

    this.mentionStart = atIdx;
    this.selectedIndex = -1;
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this._search(query), this.options.debounce);
  }

  _onKeydown(e) {
    if (!this.dropdown || !this.dropdown.parentNode) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, this.candidates.length - 1);
      this._highlight();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
      this._highlight();
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      if (this.selectedIndex >= 0 && this.selectedIndex < this.candidates.length) {
        e.preventDefault();
        this._select(this.candidates[this.selectedIndex]);
      } else if (e.key === 'Enter' && this.candidates.length > 0) {
        e.preventDefault();
        this._select(this.candidates[0]);
      } else {
        this._hide();
      }
    } else if (e.key === 'Escape') {
      this._hide();
    }
  }

  _search(query) {
    var self = this;
    fetch('/api/users/search/?q=' + encodeURIComponent(query))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        self.candidates = (data.results || []).slice(0, 8);
        self._render();
      })
      .catch(function() { self._hide(); });
  }

  _render() {
    if (this.candidates.length === 0) { this._hide(); return; }
    if (!this.dropdown) {
      this.dropdown = document.createElement('div');
      this.dropdown.className = 'ispace-mention-dropdown';
      document.body.appendChild(this.dropdown);
    }
    var html = '';
    for (var i = 0; i < this.candidates.length; i++) {
      var u = this.candidates[i];
      var active = i === this.selectedIndex ? ' ispace-mention-active' : '';
      html += '<div class="ispace-mention-item' + active + '" data-index="' + i + '">'
        + '<span class="ispace-mention-avatar" style="background:' + (u.avatar_color || '#4A90D9') + '">'
        + (u.avatar_url ? '<img src="' + esc(u.avatar_url) + '" alt="">' : (u.avatar_initial || '?'))
        + '</span>'
        + '<span class="ispace-mention-name">' + esc(u.display_name || u.username) + '</span>'
        + '<span class="ispace-mention-username">@' + esc(u.username) + '</span>'
        + '</div>';
    }
    this.dropdown.innerHTML = html;

    // Position near cursor (above/below textarea)
    var rect = this.textarea.getBoundingClientRect();
    this.dropdown.style.top = (rect.bottom + 4) + 'px';
    this.dropdown.style.left = rect.left + 'px';
    this.dropdown.style.display = 'block';

    // Click to select
    var self = this;
    this.dropdown.querySelectorAll('.ispace-mention-item').forEach(function(el) {
      el.addEventListener('mousedown', function(e) {
        e.preventDefault();
        self._select(self.candidates[parseInt(el.getAttribute('data-index'))]);
      });
    });
  }

  _highlight() {
    if (!this.dropdown) return;
    this.dropdown.querySelectorAll('.ispace-mention-item').forEach(function(el, i) {
      el.classList.toggle('ispace-mention-active', i === this.selectedIndex);
    }, this);
  }

  _select(user) {
    var val = this.textarea.value;
    var before = val.substring(0, this.mentionStart);
    var after = val.substring(this.textarea.selectionStart);
    var insert = '@' + user.username + ' ';
    this.textarea.value = before + insert + after;
    var cursorPos = this.mentionStart + insert.length;
    this.textarea.setSelectionRange(cursorPos, cursorPos);
    this.textarea.focus();
    this._hide();
  }

  _hide() {
    if (this.dropdown) {
      this.dropdown.style.display = 'none';
      this.dropdown.innerHTML = '';
    }
    this.candidates = [];
    this.selectedIndex = -1;
  }
};

/* ================================================================
   MentionCore — reusable @mention dropdown + search + keyboard nav
   Used by MentionSelector (textarea) and EditorMention (contenteditable)
   ================================================================ */
window.iSpaceDoc.MentionCore = class {
  constructor(options) {
    this.options = Object.assign({ debounce: 300 }, options || {});
    this.dropdown = null;
    this.candidates = [];
    this.selectedIndex = -1;
    this.searchTimer = null;
    this._onSelect = null;
    this._cursorRect = null;
  }

  show(query, cursorRect, onSelect) {
    this._onSelect = onSelect;
    this._cursorRect = cursorRect;
    this.selectedIndex = -1;
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(this._search.bind(this, query), this.options.debounce);
  }

  updatePosition(cursorRect) {
    this._cursorRect = cursorRect;
    if (this.dropdown && this.dropdown.parentNode && this.dropdown.style.display === 'block') {
      this.dropdown.style.top = (cursorRect.bottom + 4) + 'px';
      this.dropdown.style.left = cursorRect.left + 'px';
    }
  }

  _search(query) {
    var self = this;
    fetch('/api/users/search/?q=' + encodeURIComponent(query))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        self.candidates = (data.results || []).slice(0, 8);
        self._render();
      })
      .catch(function() { self.hide(); });
  }

  _render() {
    if (this.candidates.length === 0) { this.hide(); return; }
    if (!this.dropdown) {
      this.dropdown = document.createElement('div');
      this.dropdown.className = 'ispace-mention-dropdown';
      document.body.appendChild(this.dropdown);
    }
    var html = '';
    for (var i = 0; i < this.candidates.length; i++) {
      var u = this.candidates[i];
      var active = i === this.selectedIndex ? ' ispace-mention-active' : '';
      html += '<div class="ispace-mention-item' + active + '" data-index="' + i + '">'
        + '<span class="ispace-mention-avatar" style="background:' + (u.avatar_color || '#4A90D9') + '">'
        + (u.avatar_url ? '<img src="' + esc(u.avatar_url) + '" alt="">' : esc(u.avatar_initial || u.display_name || u.username || '?'))
        + '</span>'
        + '<span class="ispace-mention-name">' + esc(u.display_name || u.username) + '</span>'
        + '<span class="ispace-mention-username">@' + esc(u.username) + '</span>'
        + '</div>';
    }
    this.dropdown.innerHTML = html;
    this.dropdown.style.top = (this._cursorRect.bottom + 4) + 'px';
    this.dropdown.style.left = this._cursorRect.left + 'px';
    this.dropdown.style.display = 'block';

    var self = this;
    this.dropdown.querySelectorAll('.ispace-mention-item').forEach(function(el) {
      el.addEventListener('mousedown', function(e) {
        e.preventDefault();
        var idx = parseInt(el.getAttribute('data-index'));
        if (idx >= 0 && idx < self.candidates.length) {
          self._select(self.candidates[idx]);
        }
      });
    });
  }

  _highlight() {
    if (!this.dropdown) return;
    this.dropdown.querySelectorAll('.ispace-mention-item').forEach(function(el, i) {
      el.classList.toggle('ispace-mention-active', i === this.selectedIndex);
    }, this);
  }

  // Returns true if event was handled (dropdown visible, key processed)
  handleKeydown(e) {
    if (!this.dropdown || !this.dropdown.parentNode || this.dropdown.style.display === 'none') return false;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, this.candidates.length - 1);
      this._highlight();
      return true;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
      this._highlight();
      return true;
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (this.selectedIndex >= 0 && this.selectedIndex < this.candidates.length) {
        e.preventDefault();
        this._select(this.candidates[this.selectedIndex]);
        return true;
      }
      if (e.key === 'Enter' && this.candidates.length > 0) {
        e.preventDefault();
        this._select(this.candidates[0]);
        return true;
      }
      this.hide();
      return true;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      this.hide();
      return true;
    }
    return false;
  }

  _select(user) {
    if (this._onSelect) {
      var cb = this._onSelect;
      this.hide();
      cb(user);
    } else {
      this.hide();
    }
  }

  hide() {
    if (this.dropdown) {
      this.dropdown.style.display = 'none';
      this.dropdown.innerHTML = '';
    }
    this.candidates = [];
    this.selectedIndex = -1;
    this._onSelect = null;
    clearTimeout(this.searchTimer);
  }

  isVisible() {
    return !!(this.dropdown && this.dropdown.parentNode && this.dropdown.style.display === 'block');
  }

  destroy() {
    this.hide();
    if (this.dropdown) {
      this.dropdown.remove();
      this.dropdown = null;
    }
  }
};

/* ================================================================
   EditorMention — @mention for contenteditable editors (Vditor IR, iceEditor)
   ================================================================ */
window.iSpaceDoc.EditorMention = class {
  constructor(options) {
    // options: {
    //   doc: Document,           // document containing the editor (iframe doc for iceEditor)
    //   editableElement: Element, // the contenteditable root element
    //   onInsert: fn(text),      // called to insert/replace text at cursor
    //   onInput: fn(callback),   // register input listener
    //   onKeydown: fn(callback), // register keydown listener
    //   onBlur: fn(callback),    // register blur listener
    //   container: Element,      // DOM element for click-outside (default: editableElement)
    // }
    this._doc = options.doc || document;
    this._editable = options.editableElement;
    this._onInsert = options.onInsert;
    this._container = options.container || options.editableElement;
    this._core = new window.iSpaceDoc.MentionCore();
    // Track mention state for text replacement on selection
    this._mentionQueryLen = 0; // length of query text typed after @

    var self = this;

    // Input event -> detect @mention
    if (options.onInput) {
      options.onInput(function() { self._onInput(); });
    }

    // Keydown -> keyboard navigation of dropdown
    if (options.onKeydown) {
      options.onKeydown(function(e) {
        if (self._core.isVisible()) {
          self._core.handleKeydown(e);
        }
      });
    }

    // Blur -> hide dropdown after a tick
    if (options.onBlur) {
      options.onBlur(function() {
        setTimeout(function() { self._core.hide(); }, 200);
      });
    }

    // Click outside -> hide
    this._clickHandler = function(e) {
      if (!self._core.isVisible()) return;
      if (self._core.dropdown && self._core.dropdown.contains(e.target)) return;
      if (self._container.contains(e.target)) return;
      self._core.hide();
    };
    document.addEventListener('mousedown', this._clickHandler, true);
  }

  _getSelection() {
    var doc = this._doc;
    if (doc.getSelection) return doc.getSelection();
    if (doc.defaultView) return doc.defaultView.getSelection();
    return null;
  }

  _getTextBeforeCursor() {
    var sel = this._getSelection();
    if (!sel || !sel.rangeCount) return '';
    var range = sel.getRangeAt(0);
    var preRange = range.cloneRange();
    preRange.selectNodeContents(this._editable);
    preRange.setEnd(range.endContainer, range.endOffset);
    return this._extractTextWithBreaks(preRange.cloneContents());
  }

  // Walk DOM tree and insert \\n at block boundaries so that @ at the
  // start of a paragraph is detected as a word boundary (not mid-word).
  _extractTextWithBreaks(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return '';
    var BLOCKS = {P:1, DIV:1, H1:1, H2:1, H3:1, H4:1, H5:1, H6:1, LI:1, BLOCKQUOTE:1, PRE:1, SECTION:1};
    var text = '';
    for (var i = 0; i < node.childNodes.length; i++) {
      var child = node.childNodes[i];
      if (child.nodeType === Node.ELEMENT_NODE && BLOCKS[child.tagName]) {
        if (text && text[text.length - 1] !== '\n') text += '\n';
      }
      text += this._extractTextWithBreaks(child);
    }
    return text;
  }

  _getCursorRect() {
    var sel = this._getSelection();
    if (!sel || !sel.rangeCount) return null;
    var range = sel.getRangeAt(0).cloneRange();
    // Try getBoundingClientRect on the collapsed range (works for caret)
    if (range.getBoundingClientRect) {
      var r = range.getBoundingClientRect();
      if (r.width !== 0 || r.height !== 0) return r;
    }
    // Fallback: try getClientRects
    if (range.getClientRects && range.getClientRects().length > 0) {
      return range.getClientRects()[0];
    }
    // Fallback: use parent element of the start container
    var node = range.startContainer;
    if (node) {
      if (node.nodeType === Node.TEXT_NODE) node = node.parentElement;
      if (node && node.getBoundingClientRect) return node.getBoundingClientRect();
    }
    return null;
  }

  _onInput() {
    var sel = this._getSelection();
    if (!sel || !sel.rangeCount) { this._core.hide(); return; }

    var text = this._getTextBeforeCursor();
    var rect = this._getCursorRect();
    if (!rect) { this._core.hide(); return; }

    // Find last @ before cursor that starts a mention
    var atIdx = -1;
    for (var i = text.length - 1; i >= 0; i--) {
      if (text[i] === '@') { atIdx = i; break; }
      if (text[i] === ' ' || text[i] === '\n') break;
    }
    if (atIdx === -1) { this._core.hide(); return; }
    // Check word boundary: reject only when @ follows a word character (letter/digit/underscore)
    // This allows @ after space, newline, punctuation, ZWSP, or at start of text
    if (atIdx > 0 && /\w/.test(text[atIdx - 1])) { this._core.hide(); return; }
    var query = text.substring(atIdx + 1);
    if (/\s/.test(query)) { this._core.hide(); return; }

    // Save query length for later text replacement
    this._mentionQueryLen = query.length;

    var self = this;
    this._core.show(query, rect, function(user) {
      self._insertMention(user);
    });
  }

  _insertMention(user) {
    var text = '@' + user.username + ' ';
    var sel = this._getSelection();
    if (!sel || !sel.rangeCount) { this._onInsert(text); return; }

    var range = sel.getRangeAt(0);
    var container = range.endContainer;
    var offset = range.endOffset;

    // Select the @query text so the editor's insert method replaces it
    // This handles the common case where @query is in a single text node
    if (container.nodeType === Node.TEXT_NODE && offset >= this._mentionQueryLen + 1) {
      try {
        range.setStart(container, offset - this._mentionQueryLen - 1);
        sel.removeAllRanges();
        sel.addRange(range);
      } catch(e) {
        // Fall through — let onInsert handle it
      }
    }
    this._onInsert(text);
  }

  destroy() {
    document.removeEventListener('mousedown', this._clickHandler, true);
    this._core.destroy();
  }
};

function esc(str) {
  if (!str) return '';
  var d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

/* ================================================================
   Helper
   ================================================================ */
function escapeHTML(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
