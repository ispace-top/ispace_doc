/**
 * iSpaceDoc Core UI
 * Dropdowns, mobile menu, tooltips via event delegation.
 * No jQuery dependency.
 */
const CoreUI = (() => {
  function init() {
    document.addEventListener('click', handleGlobalClick);
    document.addEventListener('keydown', handleGlobalKeydown);
    initDropdowns();
    initMobileMenu();
    initTooltips();
    initScrollToTop();
    initSidebarResizer();
  }

  /* ---- Dropdowns ---- */
  function initDropdowns() {
    document.querySelectorAll('[data-ispace-dropdown]').forEach(dropdown => {
      const trigger = dropdown.querySelector('[data-ispace-dropdown-toggle]');
      const menu = dropdown.querySelector('.ispace-dropdown-menu');
      if (!trigger || !menu) return;

      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasOpen = menu.classList.contains('ispace-open');
        closeAllDropdowns();
        if (!wasOpen) {
          menu.classList.add('ispace-open');
        }
      });
    });
  }

  function closeAllDropdowns() {
    document.querySelectorAll('.ispace-dropdown-menu.ispace-open')
      .forEach(m => m.classList.remove('ispace-open'));
  }

  function handleGlobalClick(e) {
    // Logout action (event delegation)
    var logoutBtn = e.target.closest('[data-action="logout"]');
    if (logoutBtn) {
      e.preventDefault();
      var csrf = window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken;
      fetch('/logout/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf || '' }
      }).then(function(r) { return r.json(); }).then(function(data) {
        if (data.status) { window.location.href = '/'; }
        else { showError(data.msg || '退出登录失败'); }
      }).catch(function() { showError('退出登录失败，请重试'); });
      return;
    }
    if (!e.target.closest('[data-ispace-dropdown]')) {
      closeAllDropdowns();
    }
  }

  function handleGlobalKeydown(e) {
    if (e.key === 'Escape') {
      closeAllDropdowns();
      document.querySelectorAll('.ispace-modal-backdrop.ispace-active')
        .forEach(el => el.classList.remove('ispace-active'));
    }
  }

  /* ---- Sidebar Toggle (desktop collapse + mobile drawer) ---- */
  var _menuBtnInited = false;
  function initMobileMenu() {
    if (_menuBtnInited) return;
    var btn = document.getElementById('mobileMenuBtn');
    // Support all sidebar IDs (doc tree, user center, admin)
    var sidebar = document.getElementById('globalSidebar')
               || document.getElementById('userCenterSidebar')
               || document.getElementById('adminSidebar');
    if (!btn || !sidebar) return;

    var appLayout = document.querySelector('.ispace-app-layout.has-sidebar');
    var isMobile = window.innerWidth <= 768;

    // Create backdrop element (only once)
    var backdrop = document.querySelector('.ispace-sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.className = 'ispace-sidebar-backdrop';
      document.body.appendChild(backdrop);
    }

    var isOpen = false;
    var _savedScrollY = 0;

    // SVG icons for hamburger state
    var ICON_MENU = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
    var ICON_CLOSE = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="9" height="16" rx="1"/><polyline points="16 10 12 14 16 18"/></svg>';

    function updateHamburgerIcon(collapsed) {
      btn.innerHTML = collapsed ? ICON_MENU : ICON_CLOSE;
      btn.setAttribute('aria-label', collapsed ? '展开侧边栏' : '折叠侧边栏');
    }

    // ---- Desktop: collapse sidebar in grid ----
    function toggleDesktopSidebar() {
      var collapsed = !sidebar.classList.contains('ispace-sidebar--collapsed');
      if (collapsed) {
        sidebar.classList.add('ispace-sidebar--collapsed');
        if (appLayout) appLayout.classList.add('ispace-layout--sidebar-collapsed');
        btn.setAttribute('aria-expanded', 'false');
      } else {
        sidebar.classList.remove('ispace-sidebar--collapsed');
        if (appLayout) appLayout.classList.remove('ispace-layout--sidebar-collapsed');
        btn.setAttribute('aria-expanded', 'true');
      }
      updateHamburgerIcon(collapsed);
      localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
    }

    // Sync hamburger icon with initial sidebar state
    var initCollapsed = sidebar.classList.contains('ispace-sidebar--collapsed');
    if (!isMobile) {
      // Restore collapsed state from localStorage on first load
      if (!initCollapsed && localStorage.getItem('sidebar-collapsed') === '1') {
        sidebar.classList.add('ispace-sidebar--collapsed');
        if (appLayout) appLayout.classList.add('ispace-layout--sidebar-collapsed');
        initCollapsed = true;
      }
      updateHamburgerIcon(initCollapsed);
      btn.setAttribute('aria-expanded', initCollapsed ? 'false' : 'true');
    } else {
      // Mobile always shows menu icon
      btn.setAttribute('aria-expanded', 'false');
    }

    // ---- Mobile: drawer overlay ----
    function open() {
      isOpen = true;
      _savedScrollY = window.scrollY;
      sidebar.classList.add('ispace-mobile-open');
      backdrop.classList.add('ispace-active');
      btn.setAttribute('aria-expanded', 'true');
      document.body.style.position = 'fixed';
      document.body.style.top = '-' + _savedScrollY + 'px';
      document.body.style.width = '100%';
    }

    function close() {
      isOpen = false;
      sidebar.classList.remove('ispace-mobile-open');
      backdrop.classList.remove('ispace-active');
      btn.setAttribute('aria-expanded', 'false');
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      window.scrollTo(0, _savedScrollY);
    }

    btn.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        isOpen ? close() : open();
      } else {
        toggleDesktopSidebar();
      }
    });

    backdrop.addEventListener('click', close);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        if (isOpen) close();
      }
    });

    // Handle resize: close mobile drawer, sync desktop state
    window.addEventListener('resize', function() {
      var nowMobile = window.innerWidth <= 768;
      if (nowMobile !== isMobile) {
        if (isOpen) close();
        isMobile = nowMobile;
        if (!nowMobile) {
          var c = sidebar.classList.contains('ispace-sidebar--collapsed');
          updateHamburgerIcon(c);
          btn.setAttribute('aria-expanded', c ? 'false' : 'true');
        } else {
          btn.innerHTML = ICON_MENU;
          btn.setAttribute('aria-label', '展开菜单');
          btn.setAttribute('aria-expanded', 'false');
        }
      }
    });

    // Close when SPA navigation happens
    window.addEventListener('popstate', function() {
      if (isOpen) close();
    });

    // Close when clicking a link inside the sidebar drawer
    sidebar.addEventListener('click', function(e) {
      if (e.target.closest('a') && isOpen) {
        setTimeout(close, 100);
      }
    });

    _menuBtnInited = true;
  }

  /* ---- Tooltips ---- */
  function initTooltips() {
    document.querySelectorAll('[data-ispace-tooltip]').forEach(el => {
      const text = el.getAttribute('data-ispace-tooltip');
      if (!text) return;

      el.addEventListener('mouseenter', (e) => showTooltip(e, text));
      el.addEventListener('mouseleave', hideTooltip);
      el.addEventListener('focus', (e) => showTooltip(e, text));
      el.addEventListener('blur', hideTooltip);
      el.removeAttribute('title');
    });
  }

  let tooltipEl = null;

  function showTooltip(e, text) {
    hideTooltip();
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'ispace-tooltip';
    tooltipEl.textContent = text;
    tooltipEl.style.cssText = `
      position: fixed;
      z-index: var(--ispace-z-tooltip, 1070);
      padding: 6px 10px;
      background: var(--ispace-color-text-primary, #0f172a);
      color: var(--ispace-color-text-inverse, #fff);
      font-size: 12px;
      border-radius: 6px;
      pointer-events: none;
      max-width: 240px;
      white-space: normal;
    `;
    document.body.appendChild(tooltipEl);

    const rect = e.target.getBoundingClientRect();
    const top = rect.bottom + 6;
    let left = rect.left + rect.width / 2 - tooltipEl.offsetWidth / 2;
    if (left < 8) left = 8;
    if (left + tooltipEl.offsetWidth > window.innerWidth - 8) {
      left = window.innerWidth - tooltipEl.offsetWidth - 8;
    }
    tooltipEl.style.top = top + 'px';
    tooltipEl.style.left = left + 'px';
  }

  function hideTooltip() {
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  /* ---- Scroll to Top ---- */
  function initScrollToTop() {
    if (document.querySelector('[data-ispace-scroll-top]')) return;

    const btn = document.createElement('button');
    btn.setAttribute('data-ispace-scroll-top', '');
    btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>';
    btn.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--ispace-color-surface-0);
      border: 1px solid var(--ispace-color-border-light);
      box-shadow: var(--ispace-shadow-md);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transition: all 0.2s ease;
      z-index: 999;
      color: var(--ispace-color-text-secondary);
    `;
    document.body.appendChild(btn);

    function getScrollContainer() {
      var main = document.querySelector('.ispace-app-layout.has-sidebar .ispace-main-content');
      if (main) {
        var style = getComputedStyle(main);
        if (style.overflowY === 'auto' || style.overflowY === 'scroll') return main;
      }
      return window;
    }

    var _scrollTicking = false;
    function onScroll() {
      if (!_scrollTicking) {
        requestAnimationFrame(function() {
          var container = getScrollContainer();
          var top = (container === window) ? window.scrollY : container.scrollTop;
          var visible = top > 300;
          btn.style.opacity = visible ? '1' : '0';
          btn.style.visibility = visible ? 'visible' : 'hidden';
          _scrollTicking = false;
        });
        _scrollTicking = true;
      }
    }

    // Attach to both — scroll events don't bubble, so bind directly
    window.addEventListener('scroll', onScroll, { passive: true });
    var mainEl = document.querySelector('.ispace-app-layout.has-sidebar .ispace-main-content');
    if (mainEl) {
      mainEl.addEventListener('scroll', onScroll, { passive: true });
    }

    btn.addEventListener('click', function() {
      var container = getScrollContainer();
      if (container === window) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        container.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  /* ---- Sidebar Resizer (drag to adjust width) ---- */
  function initSidebarResizer() {
    var resizer = document.getElementById('sidebarResizer');
    var sidebar = document.getElementById('globalSidebar');
    var layout = document.querySelector('.ispace-app-layout.has-sidebar');
    if (!resizer || !sidebar || !layout) return;

    var MIN_WIDTH = 180;
    var MAX_WIDTH = Math.floor(window.innerWidth * 0.45);
    var _dragging = false;
    var _startX = 0;
    var _startWidth = 0;

    function clampWidth(w) {
      return Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, w));
    }

    // Restore saved width
    var savedWidth = localStorage.getItem('sidebar-width');
    if (savedWidth) {
      var w = parseInt(savedWidth, 10);
      if (w >= MIN_WIDTH && w <= MAX_WIDTH) {
        layout.style.setProperty('--ispace-sidebar-width', w + 'px');
      }
    }

    // Update max width on resize
    window.addEventListener('resize', function() {
      MAX_WIDTH = Math.floor(window.innerWidth * 0.45);
      // Clamp current width to new max
      var cur = sidebar.offsetWidth;
      var clamped = clampWidth(cur);
      if (clamped !== cur) {
        layout.style.setProperty('--ispace-sidebar-width', clamped + 'px');
      }
    });

    function onMouseDown(e) {
      if (sidebar.classList.contains('ispace-sidebar--collapsed')) return;
      e.preventDefault();
      _dragging = true;
      _startX = e.clientX;
      _startWidth = sidebar.offsetWidth;
      resizer.classList.add('ispace-resizing');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    function onMouseMove(e) {
      if (!_dragging) return;
      var delta = e.clientX - _startX;
      var newWidth = clampWidth(_startWidth + delta);
      layout.style.setProperty('--ispace-sidebar-width', newWidth + 'px');
    }

    function onMouseUp() {
      if (!_dragging) return;
      _dragging = false;
      resizer.classList.remove('ispace-resizing');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      // Save width
      var currentWidth = sidebar.offsetWidth;
      localStorage.setItem('sidebar-width', currentWidth);
    }

    resizer.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => CoreUI.init());
