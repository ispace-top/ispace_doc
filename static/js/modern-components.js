/**
 * Modern Components JavaScript - 现代化组件交互
 */

// Toast 通知系统
class Toast {
    constructor() {
        this.container = document.getElementById('toastContainer');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toastContainer';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', options = {}) {
        const toast = this.create(message, type, options);
        this.container.appendChild(toast);

        // 触发显示动画
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // 自动关闭
        const duration = options.duration || 4000;
        if (duration > 0) {
            setTimeout(() => {
                this.hide(toast);
            }, duration);
        }

        return toast;
    }

    create(message, type, options) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = this.getIcon(type);
        const title = options.title || this.getDefaultTitle(type);

        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-description">${message}</div>
            </div>
            <button class="toast-close" onclick="window.toastManager.hide(this.parentElement)">
                <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </button>
        `;

        return toast;
    }

    hide(toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 200);
    }

    getIcon(type) {
        const icons = {
            success: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
            warning: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
            danger: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
            info: '<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
        };
        return icons[type] || icons.info;
    }

    getDefaultTitle(type) {
        const titles = {
            success: '成功',
            warning: '警告',
            danger: '错误',
            info: '信息'
        };
        return titles[type];
    }
}

// Modal 弹窗系统
class Modal {
    constructor(element) {
        this.element = element;
        this.backdrop = element.closest('.modal-backdrop');
        this.bindEvents();
    }

    bindEvents() {
        // 点击背景关闭
        this.backdrop.addEventListener('click', (e) => {
            if (e.target === this.backdrop) {
                this.close();
            }
        });

        // ESC 键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });

        // 关闭按钮
        const closeBtn = this.element.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
    }

    open() {
        this.backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // 触发打开事件
        this.element.dispatchEvent(new CustomEvent('modal:open'));
    }

    close() {
        this.backdrop.classList.remove('active');
        document.body.style.overflow = '';
        
        // 触发关闭事件
        this.element.dispatchEvent(new CustomEvent('modal:close'));
    }

    isOpen() {
        return this.backdrop.classList.contains('active');
    }

    static create(content, options = {}) {
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.width = options.width || 'auto';
        modal.style.maxWidth = options.maxWidth || '500px';

        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${options.title || '提示'}</h3>
                <button class="modal-close">
                    <svg viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
            ${options.actions ? `<div class="modal-footer">${options.actions}</div>` : ''}
        `;

        backdrop.appendChild(modal);
        document.getElementById('modalsContainer').appendChild(backdrop);

        return new Modal(modal);
    }
}

// 确认对话框
function confirmDialog(message, options = {}) {
    return new Promise((resolve) => {
        const actions = `
            <button class="btn btn-secondary" onclick="this.closest('.modal-backdrop').modalInstance.close(); this.closest('.modal-backdrop').resolve(false);">
                ${options.cancelText || '取消'}
            </button>
            <button class="btn btn-danger" onclick="this.closest('.modal-backdrop').modalInstance.close(); this.closest('.modal-backdrop').resolve(true);">
                ${options.confirmText || '确认'}
            </button>
        `;

        const modal = Modal.create(message, {
            title: options.title || '确认操作',
            actions: actions
        });

        modal.backdrop.modalInstance = modal;
        modal.backdrop.resolve = resolve;
        modal.open();
    });
}

// 表单验证
class FormValidator {
    constructor(form) {
        this.form = form;
        this.rules = {};
        this.bindEvents();
    }

    addRule(fieldName, validators) {
        this.rules[fieldName] = Array.isArray(validators) ? validators : [validators];
        return this;
    }

    addRequired(fieldName, message = '此字段为必填项') {
        return this.addRule(fieldName, {
            validate: (value) => value && value.trim() !== '',
            message: message
        });
    }

    addMinLength(fieldName, minLength, message) {
        return this.addRule(fieldName, {
            validate: (value) => !value || value.length >= minLength,
            message: message || `至少需要 ${minLength} 个字符`
        });
    }

    addEmail(fieldName, message = '请输入有效的邮箱地址') {
        return this.addRule(fieldName, {
            validate: (value) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
            message: message
        });
    }

    bindEvents() {
        // 实时验证
        this.form.addEventListener('input', (e) => {
            if (e.target.matches('input, textarea, select')) {
                this.validateField(e.target);
            }
        });

        // 提交验证
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validateForm()) {
                this.form.dispatchEvent(new CustomEvent('form:valid'));
            }
        });
    }

    validateField(field) {
        const fieldName = field.name;
        const rules = this.rules[fieldName];
        
        if (!rules) return true;

        const value = field.value;
        let isValid = true;
        let errorMessage = '';

        for (const rule of rules) {
            if (!rule.validate(value)) {
                isValid = false;
                errorMessage = rule.message;
                break;
            }
        }

        this.showFieldError(field, isValid ? '' : errorMessage);
        return isValid;
    }

    validateForm() {
        let isFormValid = true;
        const inputs = this.form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isFormValid = false;
            }
        });

        return isFormValid;
    }

    showFieldError(field, message) {
        field.classList.toggle('error', !!message);
        
        let errorElement = field.parentNode.querySelector('.form-error-text');
        if (message) {
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.className = 'form-error-text';
                field.parentNode.appendChild(errorElement);
            }
            errorElement.textContent = message;
        } else if (errorElement) {
            errorElement.remove();
        }
    }
}

// 初始化全局组件
document.addEventListener('DOMContentLoaded', function() {
    // 初始化 Toast 管理器
    window.toastManager = new Toast();

    // 初始化所有表单验证
    document.querySelectorAll('form[data-validate]').forEach(form => {
        new FormValidator(form);
    });

    // 初始化所有模态框
    document.querySelectorAll('.modal').forEach(modal => {
        new Modal(modal);
    });

    // 全局快捷方法
    window.showToast = (message, type, options) => {
        return window.toastManager.show(message, type, options);
    };

    window.showSuccess = (message, options) => {
        return window.toastManager.show(message, 'success', options);
    };

    window.showWarning = (message, options) => {
        return window.toastManager.show(message, 'warning', options);
    };

    window.showError = (message, options) => {
        return window.toastManager.show(message, 'danger', options);
    };

    window.showInfo = (message, options) => {
        return window.toastManager.show(message, 'info', options);
    };

    window.confirm = confirmDialog;
});

// 工具函数
const Utils = {
    // 防抖
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    },

    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showSuccess('已复制到剪贴板');
            return true;
        } catch (err) {
            showError('复制失败');
            return false;
        }
    },

    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 格式化时间
    formatTime(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}天前`;
        if (hours > 0) return `${hours}小时前`;
        if (minutes > 0) return `${minutes}分钟前`;
        return '刚刚';
    },

    // 生成随机ID
    generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    },

    // 本地存储
    storage: {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('无法保存到本地存储:', e);
            }
        },

        get(key, defaultValue = null) {
            try {
                const value = localStorage.getItem(key);
                return value ? JSON.parse(value) : defaultValue;
            } catch (e) {
                console.warn('无法从本地存储读取:', e);
                return defaultValue;
            }
        },

        remove(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.warn('无法从本地存储删除:', e);
            }
        }
    }
};

// 导出工具函数到全局
window.Utils = Utils;