/**
 * iSpaceDoc SPA Navigation
 * Persistent left sidebar + dynamic right content area.
 * Intercepts internal navigation clicks, fetches target page,
 * replaces <main> content, updates URL via History API,
 * and syncs sidebar highlights — all without full page reload.
 */
(function () {
  'use strict';

  const MAIN_ID = 'main-content';
  const SIDEBAR_NAV_ID = 'sidebarNav';
  const SPA_ATTR = 'data-spa';

  let currentUrl = location.href;

  // ---- Determine if a URL is internal (same origin, not auth/admin pages) ----
  function isInternal(url) {
    try {
      var u = new URL(url, location.origin);
      if (u.origin !== location.origin) return false;
      // Skip auth pages and admin pages (full load)
      var path = u.pathname;
      if (/^\/(login|register|forget_pwd|logout|admin)/.test(path)) return false;
      // Skip static files
      if (/\.(css|js|png|jpg|gif|svg|ico|woff|woff2|ttf|eot|pdf|zip)(\?|$)/.test(path)) return false;
      return true;
    } catch (e) {
      return false;
    }
  }

  // ---- Extract content from fetched HTML ----
  function extractContent(html) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(html, 'text/html');
    var main = doc.getElementById(MAIN_ID);
    if (!main) return null;
    return {
      html: main.innerHTML,
      title: doc.title,
      // Extract inline styles from the fetched page's head
      styles: Array.from(doc.querySelectorAll('style')).map(function (s) { return s.textContent; }),
      // Extract script elements from the main content
      scripts: Array.from(main.querySelectorAll('script')).map(function (s) {
        return { src: s.src || '', text: s.textContent };
      })
    };
  }

  // ---- Execute scripts from fetched content ----
  function executeScripts(container, scripts) {
    scripts.forEach(function (s) {
      var el = document.createElement('script');
      if (s.src) {
        el.src = s.src;
      } else {
        el.textContent = s.text;
      }
      container.appendChild(el);
    });
  }

  // ---- Apply page-specific styles ----
  function applyPageStyles(styles) {
    // Remove previous page styles
    var old = document.getElementById('spa-page-styles');
    if (old) old.remove();
    if (styles.length === 0) return;
    var styleEl = document.createElement('style');
    styleEl.id = 'spa-page-styles';
    styleEl.textContent = styles.join('\n');
    document.head.appendChild(styleEl);
  }

  // ---- SVG icons for tree toggle swapping (shared with sidebar_tree.html) ----
  var TREE_ICONS_SPA = {
    'folder-closed': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>',
    'folder-open': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/></svg>',
    'doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>'
  };

  function updateTreeIconSpa(toggle, state) {
    toggle.innerHTML = TREE_ICONS_SPA[state] || TREE_ICONS_SPA['doc'];
    toggle.setAttribute('data-icon-state', state);
  }

  function expandAncestors(el) {
    var node = el.closest('.ispace-tree-node');
    while (node) {
      var childrenContainer = node.parentElement;
      if (!childrenContainer || !childrenContainer.classList.contains('ispace-tree-children')) break;
      childrenContainer.style.display = 'block';
      var ancestorNode = childrenContainer.parentElement;
      if (!ancestorNode || !ancestorNode.classList.contains('ispace-tree-node')) break;
      // Accordion: collapse sibling nodes at this level
      var siblings = childrenContainer.querySelectorAll(':scope > .ispace-tree-node');
      siblings.forEach(function(sibling) {
        if (sibling === node) return;
        var sibChildren = sibling.querySelector(':scope > .ispace-tree-children');
        var sibToggle = sibling.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
        if (sibChildren && sibToggle && sibToggle.getAttribute('data-expanded') === '1') {
          sibChildren.style.display = 'none';
          updateTreeIconSpa(sibToggle, 'folder-closed');
          sibToggle.setAttribute('data-expanded', '0');
        }
      });
      var ancToggle = ancestorNode.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
      if (ancToggle && ancToggle.getAttribute('data-has-children') === '1') {
        updateTreeIconSpa(ancToggle, 'folder-open');
        ancToggle.setAttribute('data-expanded', '1');
      }
      node = ancestorNode;
    }
  }

  // ---- Update sidebar highlight based on current URL ----
  function syncSidebar(pathname) {
    // Reset all active states
    var allLinks = document.querySelectorAll('#' + SIDEBAR_NAV_ID + ' .ispace-tree-link');
    allLinks.forEach(function (l) { l.classList.remove('ispace-active'); });

    var docMatch = pathname.match(/\/pages\/(\d+)\//);
    if (docMatch) {
      var docId = docMatch[1];
      var docLink = document.querySelector('.ispace-tree-link[href$="/pages/' + docId + '/"]');
      if (docLink) {
        docLink.classList.add('ispace-active');
        expandAncestors(docLink);
      }
    } else if (pathname === '/') {
      var homeLink = document.querySelector('#' + SIDEBAR_NAV_ID + ' .ispace-tree-link[href="/"]');
      if (homeLink) homeLink.classList.add('ispace-active');
    }
  }

  // ---- Navigate to a URL via SPA ----
  function navigateTo(url, pushState) {
    if (pushState === undefined) pushState = true;
    if (url === currentUrl) return;

    var main = document.getElementById(MAIN_ID);
    if (!main) { location.href = url; return; }

    // Show loading indicator
    main.style.opacity = '0.6';
    main.style.transition = 'opacity 0.1s';

    fetch(url, { headers: { 'X-SPA-Navigate': '1' } })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.text();
      })
      .then(function (html) {
        var content = extractContent(html);
        if (!content) throw new Error('No main content found');

        // Replace content
        main.innerHTML = content.html;
        main.style.opacity = '1';
        main.scrollTop = 0;

        // Update title
        document.title = content.title;

        // Apply styles
        applyPageStyles(content.styles);

        // Execute scripts
        executeScripts(main, content.scripts);

        // Update URL
        if (pushState) {
          history.pushState({ url: url, spa: true }, '', url);
        }
        currentUrl = url;

        // Sync sidebar
        syncSidebar(new URL(url).pathname);
      })
      .catch(function (err) {
        console.error('SPA navigation failed:', err);
        main.style.opacity = '1';
        // Fallback to full page load
        location.href = url;
      });
  }

  // ---- Global click delegation for SPA links ----
  document.addEventListener('click', function (e) {
    // Find closest SPA-enabled anchor
    var link = e.target.closest('a[data-spa]');
    if (!link) return;

    var href = link.getAttribute('href');
    if (!href || !isInternal(href)) return;

    // Don't intercept ctrl+click, middle click, etc.
    if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;

    e.preventDefault();
    navigateTo(href);
  });

  // ---- Handle browser back/forward ----
  window.addEventListener('popstate', function (e) {
    if (e.state && e.state.spa) {
      navigateTo(location.href, false);
    }
  });

  // ---- Initial sidebar sync on page load ----
  syncSidebar(location.pathname);

  // Expose for programmatic use
  window.iSpaceNav = {
    navigateTo: navigateTo,
    syncSidebar: syncSidebar,
    refresh: function () { navigateTo(location.href, false); }
  };

})();
