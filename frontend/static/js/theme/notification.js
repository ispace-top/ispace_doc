/**
 * iSpaceDoc Notification Panel
 * Bell icon badge, dropdown list, mark read, polling
 */
window.iSpaceDoc = window.iSpaceDoc || {};
window.iSpaceDoc.Notification = (() => {
  let unreadCount = 0;
  let pollTimer = null;
  let loading = false;

  const POLL_INTERVAL = 30000; // 30s

  function csrf() {
    return (window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken) || '';
  }

  function init() {
    fetchUnreadCount();
    // Prefetch notifications on bell click
    var trigger = document.querySelector('.ispace-notification-trigger');
    if (trigger) {
      // 使用捕获阶段确保在 core.js 的 dropdown toggle 之前检查菜单状态
      trigger.addEventListener('click', function() {
        var menu = document.querySelector('.ispace-dropdown-menu.ispace-open');
        // 仅在菜单关闭时（即将打开）抓取通知
        if (!menu) {
          setTimeout(function() {
            if (document.querySelector('.ispace-notification-panel.ispace-open')) {
              fetchNotifications();
            }
          }, 50);
        }
      }, true);
    }
    // Mark all read button
    var markAllBtn = document.getElementById('btn-mark-all-read');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        markAllRead();
      });
    }
    // Start polling
    startPoll();
  }

  /* ---- Fetch unread count ---- */
  function fetchUnreadCount() {
    fetch('/api/notifications/unread-count/', {
      headers: { 'X-CSRFToken': csrf() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 0) updateBadge(data.data && data.data.unread_count || 0);
    })
    .catch(function() { /* silent */ });
  }

  /* ---- Fetch notification list ---- */
  function fetchNotifications() {
    var listEl = document.getElementById('notification-list');
    if (!listEl || loading) return;
    loading = true;
    listEl.innerHTML = renderSkeleton();
    fetch('/api/notifications/?page_size=10&unread_only=true', {
      headers: { 'X-CSRFToken': csrf() }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 0) {
        var respData = data.data || {};
        renderList(respData.items || []);
        updateBadge(respData.items ? respData.items.filter(function(n) { return !n.is_read; }).length : 0);
        var btn = document.getElementById('btn-mark-all-read');
        if (btn) btn.style.display = (respData.items && respData.items.length > 0) ? '' : 'none';
      }
      loading = false;
    })
    .catch(function() { loading = false; });
  }

  /* ---- Render notification items ---- */
  function renderList(items) {
    var listEl = document.getElementById('notification-list');
    if (!listEl) return;

    if (!items.length) {
      listEl.innerHTML = '<div class="ispace-empty-state" style="padding:32px 16px;">'
        + '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--ispace-color-text-quaternary);margin-bottom:12px;">'
        + '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
        + '<span class="ispace-text-quaternary">暂无通知</span></div>';
      return;
    }

    var html = '';
    items.forEach(function(n) {
      var avatar = n.sender_avatar_url
        ? '<img src="' + escapeHTML(n.sender_avatar_url) + '" alt="">'
        : (n.sender_initial || '?');
      var avatarColor = n.sender_avatar_url ? '' : 'background:' + (n.sender_color || '#4A90D9') + ';color:#fff;';
      var unreadClass = n.is_read ? '' : ' ispace-unread';
      var dot = n.is_read ? '' : '<span class="ispace-notification-unread-dot"></span>';
      html += '<div class="ispace-notification-item' + unreadClass + '" data-id="' + n.id + '" data-link="' + escapeHTML(n.link || '') + '">'
        + '<div class="ispace-notification-item-avatar" data-user-id="' + (n.sender_id || '') + '" style="' + avatarColor + '">' + avatar + '</div>'
        + '<div class="ispace-notification-item-body">'
        + '<div class="ispace-notification-item-title">' + escapeHTML(n.title || '') + '</div>'
        + '<div class="ispace-notification-item-text">' + escapeHTML(n.body || '') + '</div>'
        + '<div class="ispace-notification-item-time">' + escapeHTML(n.relative_time || '') + '</div>'
        + '</div>'
        + dot
        + '</div>';
    });
    listEl.innerHTML = html;

    // Click to mark read & navigate based on type: has link → document, no link → notification tab
    listEl.querySelectorAll('.ispace-notification-item').forEach(function(el) {
      el.addEventListener('click', function() {
        var id = parseInt(el.getAttribute('data-id'));
        var link = el.getAttribute('data-link');
        markRead(id);
        el.classList.remove('ispace-unread');
        var dot = el.querySelector('.ispace-notification-unread-dot');
        if (dot) dot.remove();
        // Navigate after brief delay
        var dest = (link && link !== 'None' && link !== '')
          ? link
          : ('/my/?tab=notifications&open=' + id);
        setTimeout(function() { window.location.href = dest; }, 150);
      });
    });
  }

  /* ---- Mark single as read ---- */
  function markRead(id) {
    fetch('/api/notifications/read/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify({ id: id })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 0) fetchUnreadCount();
    })
    .catch(function() {});
  }

  /* ---- Mark all as read ---- */
  function markAllRead() {
    fetch('/api/notifications/read/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify({ mark_all: true })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 0) {
        // Update UI immediately
        document.querySelectorAll('.ispace-notification-item').forEach(function(el) {
          el.classList.remove('ispace-unread');
          var dot = el.querySelector('.ispace-notification-unread-dot');
          if (dot) dot.remove();
        });
        updateBadge(0);
        var btn = document.getElementById('btn-mark-all-read');
        if (btn) btn.style.display = 'none';
      }
    })
    .catch(function() {});
  }

  /* ---- Update badge ---- */
  function updateBadge(count) {
    unreadCount = count;
    var badge = document.getElementById('notification-badge');
    if (!badge) return;
    if (count > 0) {
      var text = count > 99 ? '99+' : count;
      badge.textContent = text;
      badge.style.display = '';
      // Sync to dropdown badge
      var dropBadge = document.getElementById('dropdown-unread-badge');
      if (dropBadge) { dropBadge.textContent = text; dropBadge.style.display = ''; }
    } else {
      badge.style.display = 'none';
      var dropBadge = document.getElementById('dropdown-unread-badge');
      if (dropBadge) { dropBadge.style.display = 'none'; }
    }
  }

  /* ---- Polling ---- */
  function startPoll() {
    if (pollTimer) return;
    pollTimer = setInterval(fetchUnreadCount, POLL_INTERVAL);
  }

  /* ---- Skeleton loading ---- */
  function renderSkeleton() {
    var s = '';
    for (var i = 0; i < 5; i++) {
      s += '<div class="ispace-notification-skeleton">'
        + '<div class="ispace-notification-skeleton-avatar"></div>'
        + '<div class="ispace-notification-skeleton-lines">'
        + '<div class="ispace-notification-skeleton-line"></div>'
        + '<div class="ispace-notification-skeleton-line"></div>'
        + '</div></div>';
    }
    return s;
  }

  /* ---- Escape HTML ---- */
  function escapeHTML(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return { init: init, updateBadge: updateBadge, fetchUnreadCount: fetchUnreadCount };
})();
