/**
 * iSpaceDoc Author Card Popup
 * Hover on elements with [data-user-id] to show user info card.
 * 300ms enter delay, 200ms leave delay, async loading with skeleton.
 */
window.iSpaceDoc = window.iSpaceDoc || {};
window.iSpaceDoc.AuthorCard = (() => {
  let cardEl = null;
  let enterTimer = null;
  let leaveTimer = null;
  let currentUserId = null;
  let cache = {}; // Simple in-memory cache by user_id
  let activeTrigger = null;

  const ENTER_DELAY = 300;
  const LEAVE_DELAY = 200;
  const CACHE_TTL = 5 * 60 * 1000; // 5 min

  function init() {
    document.addEventListener('mouseenter', handleMouseEnter, true);
    document.addEventListener('mouseleave', handleMouseLeave, true);
    // Touch: show on tap, hide on outside tap
    document.addEventListener('click', handleClick);
    // Hide on scroll
    window.addEventListener('scroll', hide, { passive: true });
  }

  /* ---- Delegate mouseenter ---- */
  function handleMouseEnter(e) {
    var target = e.target.closest ? e.target : e.target.parentElement;
    if (!target) return;
    var trigger = target.closest('[data-user-id]');
    if (!trigger) return;
    var uid = parseInt(trigger.getAttribute('data-user-id'));
    if (!uid || uid === currentUserId) return;
    clearTimer('enter');
    activeTrigger = trigger;
    enterTimer = setTimeout(function() { show(uid, trigger); }, ENTER_DELAY);
  }

  /* ---- Delegate mouseleave ---- */
  function handleMouseLeave(e) {
    var target = e.target.closest ? e.target : e.target.parentElement;
    if (!target) return;
    var trigger = target.closest('[data-user-id]');
    if (!trigger || trigger !== activeTrigger) return;
    clearTimer('enter');
    leaveTimer = setTimeout(function() {
      // Only hide if not hovering over card itself
      if (!isHoveringCard()) hide();
    }, LEAVE_DELAY);
  }

  /* ---- Click: show on tap, hide on outside click ---- */
  function handleClick(e) {
    var target = e.target.closest ? e.target : e.target.parentElement;
    if (!target) return;
    var trigger = target.closest('[data-user-id]');
    if (trigger) {
      var uid = parseInt(trigger.getAttribute('data-user-id'));
      if (uid) show(uid, trigger, true);
      return;
    }
    if (cardEl && cardEl.classList.contains('ispace-visible') && !target.closest('.ispace-author-card')) {
      hide();
    }
  }

  /* ---- Show card ---- */
  function show(uid, trigger, immediate) {
    if (uid === currentUserId && cardEl && cardEl.classList.contains('ispace-visible')) return;
    currentUserId = uid;
    ensureCard();
    // Skeleton
    cardEl.innerHTML = renderSkeleton();
    position(trigger);
    cardEl.classList.add('ispace-visible');

    // Check cache
    var cached = cache[uid];
    if (cached && (Date.now() - cached.ts) < CACHE_TTL) {
      render(cached.data, trigger);
      return;
    }

    fetch('/api/users/' + uid + '/profile/')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.error) { cardEl.innerHTML = '<div class="ispace-author-card-error">' + escapeHTML(data.error) + '</div>'; return; }
        cache[uid] = { data: data, ts: Date.now() };
        if (currentUserId === uid) {
          render(data, trigger);
          position(trigger); // re-position after render
        }
      })
      .catch(function() {
        if (currentUserId === uid) {
          cardEl.innerHTML = '<div class="ispace-author-card-error">加载失败</div>';
        }
      });
  }

  /* ---- Render card content ---- */
  function render(data, trigger) {
    if (!cardEl) return;
    var avatarHtml = data.avatar_url
      ? '<img src="' + escapeHTML(data.avatar_url) + '" alt="" class="ispace-author-card-avatar-img">'
      : '<span class="ispace-author-card-avatar-initial" style="background:' + (data.avatar_color || '#4A90D9') + '">' + (data.avatar_initial || '?') + '</span>';

    var genderIcon = '';
    if (data.gender === '男') genderIcon = '<span title="男" class="ispace-author-card-gender ispace-author-card-gender-male">♂</span>';
    else if (data.gender === '女') genderIcon = '<span title="女" class="ispace-author-card-gender ispace-author-card-gender-female">♀</span>';

    var html = '<div class="ispace-author-card-header">'
      + '<div class="ispace-author-card-avatar">' + avatarHtml + '</div>'
      + '<div class="ispace-author-card-name-row">'
      + '<span class="ispace-author-card-name">' + escapeHTML(data.display_name || data.username) + '</span>'
      + genderIcon
      + '</div>'
      + '</div>';
    if (data.orgs && data.orgs.length) {
      html += '<div class="ispace-author-card-orgs">';
      data.orgs.forEach(function(org) {
        var orgIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="19" rx="1.5"/><line x1="10" y1="22" x2="10" y2="18"/><line x1="14" y1="22" x2="14" y2="18"/></svg>';
        html += '<div class="ispace-author-card-org' + (org.is_primary ? ' ispace-author-card-org--primary' : '') + '">'
          + orgIcon
          + '<span class="ispace-author-card-org-path">' + escapeHTML(org.path) + '</span>'
          + '</div>';
      });
      html += '</div>';
    }
    if (data.bio) {
      html += '<div class="ispace-author-card-bio">' + escapeHTML(data.bio) + '</div>';
    }
    cardEl.innerHTML = html;

    // Card hover tracking
    cardEl.addEventListener('mouseenter', function() { clearTimer('leave'); });
    cardEl.addEventListener('mouseleave', function() { hide(); });
  }

  /* ---- Position card ---- */
  function position(trigger) {
    if (!cardEl || !trigger) return;
    var rect = trigger.getBoundingClientRect();
    var cardW = 280;
    var gap = 8;
    var left = rect.left;
    var top = rect.bottom + gap;

    // Keep within viewport
    if (left + cardW > window.innerWidth - 12) left = window.innerWidth - cardW - 12;
    if (left < 8) left = 8;
    // If not enough room below, show above
    if (top + 180 > window.innerHeight) {
      top = rect.top - 180 - gap;
      if (top < 8) top = 8;
    }

    cardEl.style.left = left + 'px';
    cardEl.style.top = top + 'px';
  }

  /* ---- Ensure card DOM element ---- */
  function ensureCard() {
    if (cardEl) return;
    cardEl = document.createElement('div');
    cardEl.className = 'ispace-author-card';
    document.body.appendChild(cardEl);
  }

  /* ---- Hide card ---- */
  function hide() {
    clearTimer('enter');
    clearTimer('leave');
    if (cardEl) cardEl.classList.remove('ispace-visible');
    currentUserId = null;
    activeTrigger = null;
  }

  function isHoveringCard() {
    return cardEl && cardEl.matches(':hover');
  }

  function clearTimer(type) {
    if (type === 'enter' && enterTimer) { clearTimeout(enterTimer); enterTimer = null; }
    if (type === 'leave' && leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null; }
  }

  /* ---- Skeleton ---- */
  function renderSkeleton() {
    return '<div class="ispace-author-card-header ispace-author-card-skeleton">'
      + '<div class="ispace-author-card-avatar"><div class="ispace-skeleton-circle" style="width:44px;height:44px;"></div></div>'
      + '<div style="flex:1;"><div class="ispace-skeleton-line" style="width:80px;height:14px;margin-bottom:8px;"></div><div class="ispace-skeleton-line" style="width:120px;height:12px;"></div></div>'
      + '</div>'
      + '<div class="ispace-skeleton-line" style="width:70%;height:12px;margin-bottom:8px;"></div>'
      + '<div class="ispace-skeleton-line" style="width:50%;height:12px;"></div>';
  }

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

  return { show: show, hide: hide };
})();
