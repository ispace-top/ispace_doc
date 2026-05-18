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
   Helper
   ================================================================ */
function escapeHTML(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
