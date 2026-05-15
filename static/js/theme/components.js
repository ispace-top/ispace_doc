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
   ================================================================ */
window.iSpaceDoc.confirm = function (message, options = {}) {
  return new Promise((resolve) => {
    const title = options.title || '确认操作';
    const confirmText = options.confirmText || '确认';
    const cancelText = options.cancelText || '取消';

    const backdrop = document.createElement('div');
    backdrop.className = 'ispace-modal-backdrop';
    backdrop.innerHTML = `
      <div class="ispace-modal ispace-modal-sm">
        <div class="ispace-modal-header">
          <h3 class="ispace-modal-title">${escapeHTML(title)}</h3>
          <button class="ispace-modal-close" data-ispace-modal-close>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="ispace-modal-body">
          <p class="ispace-text-sm ispace-text-secondary">${escapeHTML(message)}</p>
        </div>
        <div class="ispace-modal-footer">
          <button class="ispace-btn ispace-btn-secondary" data-action="cancel">${cancelText}</button>
          <button class="ispace-btn ispace-btn-primary" data-action="confirm">${confirmText}</button>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);

    requestAnimationFrame(() => {
      backdrop.classList.add('ispace-active');
    });

    backdrop.querySelector('[data-action="confirm"]').addEventListener('click', () => {
      cleanup();
      resolve(true);
    });
    backdrop.querySelector('[data-action="cancel"]').addEventListener('click', () => {
      cleanup();
      resolve(false);
    });
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        cleanup();
        resolve(false);
      }
    });

    function cleanup() {
      backdrop.classList.remove('ispace-active');
      setTimeout(() => backdrop.remove(), 300);
    }
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
