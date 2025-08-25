/**
 * iSpaceDoc 现代化UI交互组件库
 * 提供下拉菜单、通知、移动端导航等功能
 */

class ModernUI {
  constructor() {
    this.init();
  }

  init() {
    this.initDropdowns();
    this.initMobileMenu();
    this.initSearch();
    this.initTooltips();
    this.initNotifications();
    this.initModals();
    this.initScrollToTop();
  }

  // 初始化下拉菜单
  initDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown');
    
    dropdowns.forEach(dropdown => {
      const toggle = dropdown.querySelector('.dropdown-toggle');
      const menu = dropdown.querySelector('.dropdown-menu');
      
      if (!toggle || !menu) return;

      // 点击切换下拉菜单
      toggle.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        // 关闭其他下拉菜单
        this.closeAllDropdowns();
        
        // 切换当前下拉菜单
        const isOpen = dropdown.classList.contains('show');
        if (isOpen) {
          this.closeDropdown(dropdown);
        } else {
          this.openDropdown(dropdown);
        }
      });

      // 点击菜单项后关闭
      menu.addEventListener('click', (e) => {
        if (e.target.classList.contains('dropdown-item')) {
          setTimeout(() => this.closeDropdown(dropdown), 150);
        }
      });
    });

    // 点击外部关闭下拉菜单
    document.addEventListener('click', () => {
      this.closeAllDropdowns();
    });

    // ESC 键关闭下拉菜单
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllDropdowns();
      }
    });
  }

  openDropdown(dropdown) {
    dropdown.classList.add('show');
    const toggle = dropdown.querySelector('.dropdown-toggle');
    const menu = dropdown.querySelector('.dropdown-menu');
    
    if (toggle) {
      toggle.setAttribute('aria-expanded', 'true');
    }
    
    if (menu) {
      menu.style.opacity = '0';
      menu.style.transform = 'translateY(-10px)';
      
      requestAnimationFrame(() => {
        menu.style.transition = 'opacity 200ms ease, transform 200ms ease';
        menu.style.opacity = '1';
        menu.style.transform = 'translateY(0)';
      });
    }
  }

  closeDropdown(dropdown) {
    const menu = dropdown.querySelector('.dropdown-menu');
    const toggle = dropdown.querySelector('.dropdown-toggle');
    
    if (toggle) {
      toggle.setAttribute('aria-expanded', 'false');
    }
    
    if (menu) {
      menu.style.opacity = '0';
      menu.style.transform = 'translateY(-10px)';
      
      setTimeout(() => {
        dropdown.classList.remove('show');
        menu.style.transition = '';
      }, 200);
    } else {
      dropdown.classList.remove('show');
    }
  }

  closeAllDropdowns() {
    document.querySelectorAll('.dropdown.show').forEach(dropdown => {
      this.closeDropdown(dropdown);
    });
  }

  // 初始化移动端菜单
  initMobileMenu() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const navbar = document.querySelector('.navbar-nav');
    
    if (!toggle || !navbar) return;

    // 创建移动端菜单覆盖层
    const overlay = document.createElement('div');
    overlay.className = 'mobile-menu-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 999;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
    `;
    document.body.appendChild(overlay);

    // 移动端菜单样式
    const mobileMenuStyles = `
      .mobile-menu-open {
        overflow: hidden;
      }
      
      .mobile-menu-overlay.show {
        opacity: 1;
        visibility: visible;
      }
      
      @media (max-width: 767px) {
        .navbar-nav {
          position: fixed;
          top: 64px;
          right: 0;
          width: 280px;
          height: calc(100vh - 64px);
          background: var(--bg-primary);
          border-left: 1px solid var(--border-primary);
          padding: var(--space-6) var(--space-4);
          transform: translateX(100%);
          transition: transform 0.3s ease;
          z-index: 1000;
          overflow-y: auto;
        }
        
        .navbar-nav.show {
          transform: translateX(0);
        }
        
        .navbar-nav-item {
          display: block;
          margin-bottom: var(--space-2);
        }
        
        .navbar-nav-link {
          display: block;
          padding: var(--space-3) var(--space-4);
          border-radius: var(--radius-md);
        }
        
        .dropdown-menu {
          position: static;
          box-shadow: none;
          border: none;
          background: var(--bg-secondary);
          margin-top: var(--space-2);
          border-radius: var(--radius-md);
        }
      }
    `;

    // 添加样式
    const styleSheet = document.createElement('style');
    styleSheet.textContent = mobileMenuStyles;
    document.head.appendChild(styleSheet);

    // 切换移动端菜单
    toggle.addEventListener('click', () => {
      const isOpen = navbar.classList.contains('show');
      
      if (isOpen) {
        this.closeMobileMenu();
      } else {
        this.openMobileMenu();
      }
    });

    // 点击覆盖层关闭菜单
    overlay.addEventListener('click', () => {
      this.closeMobileMenu();
    });

    // ESC 键关闭菜单
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navbar.classList.contains('show')) {
        this.closeMobileMenu();
      }
    });
  }

  openMobileMenu() {
    const navbar = document.querySelector('.navbar-nav');
    const overlay = document.querySelector('.mobile-menu-overlay');
    
    navbar.classList.add('show');
    overlay.classList.add('show');
    document.body.classList.add('mobile-menu-open');
  }

  closeMobileMenu() {
    const navbar = document.querySelector('.navbar-nav');
    const overlay = document.querySelector('.mobile-menu-overlay');
    
    navbar.classList.remove('show');
    overlay.classList.remove('show');
    document.body.classList.remove('mobile-menu-open');
  }

  // 初始化搜索功能
  initSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
      let searchTimeout;
      
      // 实时搜索建议（如果需要）
      input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length >= 2) {
          searchTimeout = setTimeout(() => {
            this.performSearch(query, input);
          }, 300);
        } else {
          this.hideSearchResults(input);
        }
      });

      // 键盘导航
      input.addEventListener('keydown', (e) => {
        const results = input.parentElement.querySelector('.search-results');
        if (!results || !results.children.length) return;

        const items = results.querySelectorAll('.search-result-item');
        const current = results.querySelector('.search-result-item.active');
        let index = current ? Array.from(items).indexOf(current) : -1;

        switch (e.key) {
          case 'ArrowDown':
            e.preventDefault();
            index = Math.min(index + 1, items.length - 1);
            this.highlightSearchResult(items[index]);
            break;
          case 'ArrowUp':
            e.preventDefault();
            index = Math.max(index - 1, 0);
            this.highlightSearchResult(items[index]);
            break;
          case 'Enter':
            e.preventDefault();
            if (current) {
              current.click();
            } else {
              input.closest('form').submit();
            }
            break;
        }
      });

      // 失焦隐藏结果
      input.addEventListener('blur', () => {
        setTimeout(() => this.hideSearchResults(input), 200);
      });
    });
  }

  performSearch(query, input) {
    // 这里可以实现实时搜索 API 调用
    // 暂时跳过实时搜索功能
  }

  hideSearchResults(input) {
    const results = input.parentElement.querySelector('.search-results');
    if (results) {
      results.style.display = 'none';
    }
  }

  highlightSearchResult(item) {
    const parent = item.parentElement;
    parent.querySelectorAll('.search-result-item').forEach(el => {
      el.classList.remove('active');
    });
    item.classList.add('active');
    item.scrollIntoView({ block: 'nearest' });
  }

  // 初始化工具提示
  initTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    
    tooltipElements.forEach(element => {
      const title = element.getAttribute('title');
      if (!title) return;

      // 创建工具提示元素
      const tooltip = document.createElement('div');
      tooltip.className = 'tooltip-content';
      tooltip.textContent = title;
      tooltip.style.cssText = `
        position: absolute;
        background: var(--gray-800);
        color: white;
        padding: 6px 8px;
        border-radius: 4px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 1060;
        pointer-events: none;
        opacity: 0;
        visibility: hidden;
        transition: all 0.2s ease;
      `;

      document.body.appendChild(tooltip);

      // 移除原始 title 属性
      element.removeAttribute('title');
      element.setAttribute('data-tooltip', title);

      // 鼠标事件
      element.addEventListener('mouseenter', (e) => {
        this.showTooltip(tooltip, e.target);
      });

      element.addEventListener('mouseleave', () => {
        this.hideTooltip(tooltip);
      });

      element.addEventListener('mousemove', (e) => {
        this.updateTooltipPosition(tooltip, e);
      });
    });
  }

  showTooltip(tooltip, element) {
    tooltip.style.opacity = '1';
    tooltip.style.visibility = 'visible';
  }

  hideTooltip(tooltip) {
    tooltip.style.opacity = '0';
    tooltip.style.visibility = 'hidden';
  }

  updateTooltipPosition(tooltip, event) {
    const rect = tooltip.getBoundingClientRect();
    const x = event.clientX;
    const y = event.clientY;
    
    let left = x + 10;
    let top = y - rect.height - 10;
    
    // 边界检查
    if (left + rect.width > window.innerWidth) {
      left = x - rect.width - 10;
    }
    
    if (top < 0) {
      top = y + 10;
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
  }

  // 初始化通知系统
  initNotifications() {
    // 创建通知容器
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    // 暴露全局通知方法
    window.showNotification = (message, type = 'info', duration = 3000) => {
      this.showNotification(message, type, duration);
    };
  }

  showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = this.getNotificationIcon(type);
    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        ${icon}
        <div style="flex: 1;">
          <div style="font-weight: 500; color: var(--text-primary);">
            ${this.getNotificationTitle(type)}
          </div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 2px;">
            ${message}
          </div>
        </div>
        <button class="toast-close" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; padding: 4px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    `;

    // 添加到容器
    container.appendChild(toast);

    // 显示动画
    setTimeout(() => toast.classList.add('show'), 100);

    // 自动关闭
    const autoClose = setTimeout(() => this.hideNotification(toast), duration);

    // 点击关闭按钮
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
      clearTimeout(autoClose);
      this.hideNotification(toast);
    });

    // 鼠标悬停暂停自动关闭
    toast.addEventListener('mouseenter', () => clearTimeout(autoClose));
    toast.addEventListener('mouseleave', () => {
      setTimeout(() => this.hideNotification(toast), 1000);
    });

    return toast;
  }

  hideNotification(toast) {
    toast.classList.remove('show');
    setTimeout(() => {
      if (toast.parentElement) {
        toast.parentElement.removeChild(toast);
      }
    }, 300);
  }

  getNotificationIcon(type) {
    const icons = {
      success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color: var(--success-500);"><path d="M9 12l2 2 4-4"></path><circle cx="12" cy="12" r="10"></circle></svg>',
      error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color: var(--error-500);"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
      warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color: var(--warning-500);"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
      info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color: var(--primary-500);"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    return icons[type] || icons.info;
  }

  getNotificationTitle(type) {
    const titles = {
      success: '成功',
      error: '错误',
      warning: '警告',
      info: '提示'
    };
    return titles[type] || '通知';
  }

  // 初始化模态框
  initModals() {
    const modals = document.querySelectorAll('.modal-backdrop');
    
    modals.forEach(modal => {
      const closeBtn = modal.querySelector('.modal-close');
      
      // 点击关闭按钮
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.closeModal(modal));
      }
      
      // 点击背景关闭
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.closeModal(modal);
        }
      });
      
      // ESC 键关闭
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
          this.closeModal(modal);
        }
      });
    });

    // 暴露全局模态框方法
    window.openModal = (modalId) => this.openModal(modalId);
    window.closeModal = (modalId) => this.closeModal(modalId);
  }

  openModal(modal) {
    if (typeof modal === 'string') {
      modal = document.getElementById(modal);
    }
    
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  }

  closeModal(modal) {
    if (typeof modal === 'string') {
      modal = document.getElementById(modal);
    }
    
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  }

  // 初始化返回顶部
  initScrollToTop() {
    const button = document.createElement('button');
    button.className = 'scroll-to-top';
    button.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <line x1="12" y1="19" x2="12" y2="5"></line>
        <polyline points="5,12 12,5 19,12"></polyline>
      </svg>
    `;
    button.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 24px;
      width: 48px;
      height: 48px;
      background: var(--primary-600);
      color: white;
      border: none;
      border-radius: 50%;
      box-shadow: var(--shadow-lg);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
      transform: translateY(20px);
    `;

    document.body.appendChild(button);

    // 显示/隐藏按钮
    let isVisible = false;
    window.addEventListener('scroll', () => {
      const shouldShow = window.scrollY > 300;
      
      if (shouldShow && !isVisible) {
        button.style.opacity = '1';
        button.style.visibility = 'visible';
        button.style.transform = 'translateY(0)';
        isVisible = true;
      } else if (!shouldShow && isVisible) {
        button.style.opacity = '0';
        button.style.visibility = 'hidden';
        button.style.transform = 'translateY(20px)';
        isVisible = false;
      }
    });

    // 点击返回顶部
    button.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // 悬停效果
    button.addEventListener('mouseenter', () => {
      button.style.transform = 'translateY(0) scale(1.1)';
    });

    button.addEventListener('mouseleave', () => {
      button.style.transform = 'translateY(0) scale(1)';
    });
  }
}

// 初始化现代化UI组件
document.addEventListener('DOMContentLoaded', () => {
  window.modernUI = new ModernUI();
});

// 暴露初始化函数给全局使用
window.initDropdowns = () => window.modernUI?.initDropdowns();
window.initMobileMenu = () => window.modernUI?.initMobileMenu();
window.initSearch = () => window.modernUI?.initSearch();
window.initTooltips = () => window.modernUI?.initTooltips();
window.initNotifications = () => window.modernUI?.initNotifications();