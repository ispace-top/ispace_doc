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

  /* ---- Mobile Sidebar Drawer ---- */
  var _mobileMenuInited = false;
  function initMobileMenu() {
    if (_mobileMenuInited) return;
    var btn = document.getElementById('mobileMenuBtn');
    // Support all sidebar IDs (doc tree, user center, admin)
    var sidebar = document.getElementById('globalSidebar')
               || document.getElementById('userCenterSidebar')
               || document.getElementById('adminSidebar');
    if (!btn || !sidebar) return;

    // Create backdrop element (only once)
    var backdrop = document.querySelector('.ispace-sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.className = 'ispace-sidebar-backdrop';
      document.body.appendChild(backdrop);
    }

    var isOpen = false;

    var _savedScrollY = 0;

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
      isOpen ? close() : open();
    });

    backdrop.addEventListener('click', close);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) {
        close();
      }
    });

    // Close on window resize back to desktop
    window.addEventListener('resize', function() {
      if (isOpen && window.innerWidth > 768) {
        close();
      }
    });

    // Close when SPA navigation happens (back/forward)
    window.addEventListener('popstate', function() {
      if (isOpen) close();
    });

    // Close when clicking a link inside the sidebar drawer
    sidebar.addEventListener('click', function(e) {
      if (e.target.closest('a') && isOpen) {
        setTimeout(close, 100); // delay to let navigation start
      }
    });

    _mobileMenuInited = true;
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

    window.addEventListener('scroll', () => {
      const visible = window.scrollY > 300;
      btn.style.opacity = visible ? '1' : '0';
      btn.style.visibility = visible ? 'visible' : 'hidden';
    });

    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => CoreUI.init());
