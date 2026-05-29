/**
 * v1.0 Phase 5 — 划词评论 (Inline Comments)
 *
 * 功能：
 *   5.2.1 文本选中检测 + 小型操作条
 *   5.2.2 选中文字标记渲染（波浪下划线 + 气泡数字）
 *   5.2.4 点击气泡展开评论面板
 *   5.2.7 文档正文与评论面板滚动联动
 */
(function () {
  'use strict';

  const INLINE_COMMENT_LIMIT = 500;

  // ---- 状态 ----
  let currentSelection = null;       // { text, anchorStart, anchorEnd, anchorHash, range }
  let pendingSubmitAnchor = null;    // 评论提交锚点快照，不受后续鼠标事件影响
  let actionBar = null;
  let commentPanel = null;
  let activeMarkerKey = null;
  let replyToCommentId = null;       // 当前正在回复的评论 ID

  // ---- DOM 引用 ----
  const docContent = document.getElementById('doc-content');
  if (!docContent) return;

  // ---- 工具函数 ----

  /** 计算文本节点在父容器中的字符偏移 */
  function getTextOffset(container, node, offset) {
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
    let pos = 0;
    let current;
    while ((current = walker.nextNode())) {
      if (current === node) {
        return pos + offset;
      }
      pos += current.textContent.length;
    }
    return pos;
  }

  /** 获取选中文本的锚点信息 */
  function getSelectionAnchor() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;

    const range = sel.getRangeAt(0);
    const text = range.toString().trim();
    if (!text || text.length > 500) return null;

    // 确保选区在文档内容区域内
    if (!docContent.contains(range.commonAncestorContainer)) return null;

    const anchorStart = getTextOffset(docContent, range.startContainer, range.startOffset);
    const anchorEnd = getTextOffset(docContent, range.endContainer, range.endOffset);

    if (anchorEnd <= anchorStart) return null;

    // MD5 哈希
    const anchorHash = md5(text);

    return { text, anchorStart, anchorEnd, anchorHash, range };
  }

  /**
   * MD5 实现 — 与后端 Python hashlib.md5 输出完全一致。
   * 基于 Joseph Myers 的公开实现改编。
   */
  function md5(str) {
    function add32(a, b) { return (a + b) & 0xffffffff; }
    function cmn(q, a, b, x, s, t) { return add32((add32(add32(a, q), add32(x, t)) << s) | (add32(add32(a, q), add32(x, t)) >>> (32 - s)), b); }
    function ff(a, b, c, d, x, s, t) { return cmn((b & c) | (~b & d), a, b, x, s, t); }
    function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & ~d), a, b, x, s, t); }
    function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
    function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | ~d), a, b, x, s, t); }

    function md5cycle(x, k) {
      var a = x[0], b = x[1], c = x[2], d = x[3];
      a = ff(a, b, c, d, k[0],  7,  -680876936); d = ff(d, a, b, c, k[1],  12, -389564586); c = ff(c, d, a, b, k[2],  17,  606105819); b = ff(b, c, d, a, k[3],  22, -1044525330);
      a = ff(a, b, c, d, k[4],  7,  -176418897); d = ff(d, a, b, c, k[5],  12,  1200080426); c = ff(c, d, a, b, k[6],  17, -1473231341); b = ff(b, c, d, a, k[7],  22, -45705983);
      a = ff(a, b, c, d, k[8],  7,   1770035416); d = ff(d, a, b, c, k[9],  12, -1958414417); c = ff(c, d, a, b, k[10], 17, -42063);     b = ff(b, c, d, a, k[11], 22, -1990404162);
      a = ff(a, b, c, d, k[12], 7,   1804603682); d = ff(d, a, b, c, k[13], 12, -40341101);  c = ff(c, d, a, b, k[14], 17, -1502002290); b = ff(b, c, d, a, k[15], 22,  1236535329);
      a = gg(a, b, c, d, k[1],  5,  -165796510); d = gg(d, a, b, c, k[6],  9,  -1069501632); c = gg(c, d, a, b, k[11], 14,  643717713); b = gg(b, c, d, a, k[0],  20, -373897302);
      a = gg(a, b, c, d, k[5],  5,  -701558691); d = gg(d, a, b, c, k[10], 9,   38016083);   c = gg(c, d, a, b, k[15], 14, -660478335); b = gg(b, c, d, a, k[4],  20, -405537848);
      a = gg(a, b, c, d, k[9],  5,   568446438); d = gg(d, a, b, c, k[14], 9,  -1019803690); c = gg(c, d, a, b, k[3],  14, -187363961); b = gg(b, c, d, a, k[8],  20,  1163531501);
      a = gg(a, b, c, d, k[13], 5,  -1444681467); d = gg(d, a, b, c, k[2],  9,  -51403784);  c = gg(c, d, a, b, k[7],  14,  1735328473); b = gg(b, c, d, a, k[12], 20, -1926607734);
      a = hh(a, b, c, d, k[5],  4,  -378558);    d = hh(d, a, b, c, k[8],  11, -2022574463); c = hh(c, d, a, b, k[11], 16,  1839030562); b = hh(b, c, d, a, k[14], 23, -35309556);
      a = hh(a, b, c, d, k[1],  4,  -1530992060); d = hh(d, a, b, c, k[4],  11,  1272893353); c = hh(c, d, a, b, k[7],  16, -155497632); b = hh(b, c, d, a, k[10], 23, -1094730640);
      a = hh(a, b, c, d, k[13], 4,   681279174); d = hh(d, a, b, c, k[0],  11, -358537222);  c = hh(c, d, a, b, k[3],  16, -722521979); b = hh(b, c, d, a, k[6],  23,  76029189);
      a = hh(a, b, c, d, k[9],  4,  -640364487); d = hh(d, a, b, c, k[12], 11, -421815835);  c = hh(c, d, a, b, k[15], 16,  530742520); b = hh(b, c, d, a, k[2],  23, -995338651);
      a = ii(a, b, c, d, k[0],  6,  -198630844); d = ii(d, a, b, c, k[7],  10,  1126891415); c = ii(c, d, a, b, k[14], 15, -1416354905); b = ii(b, c, d, a, k[5],  21, -57434055);
      a = ii(a, b, c, d, k[12], 6,   1700485571); d = ii(d, a, b, c, k[3],  10, -1894986606); c = ii(c, d, a, b, k[10], 15, -1051523);   b = ii(b, c, d, a, k[1],  21, -2054922799);
      a = ii(a, b, c, d, k[8],  6,   1873313359); d = ii(d, a, b, c, k[15], 10, -30611744);  c = ii(c, d, a, b, k[6],  15, -1560198380); b = ii(b, c, d, a, k[13], 21,  1309151649);
      a = ii(a, b, c, d, k[4],  6,  -145523070); d = ii(d, a, b, c, k[11], 10, -1120210379); c = ii(c, d, a, b, k[2],  15,  718787259); b = ii(b, c, d, a, k[9],  21, -343485551);
      x[0] = add32(a, x[0]); x[1] = add32(b, x[1]); x[2] = add32(c, x[2]); x[3] = add32(d, x[3]);
    }

    // UTF-8 encode
    var bytes = [];
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      if (c < 0x80) { bytes.push(c); }
      else if (c < 0x800) { bytes.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f)); }
      else if (c < 0xd800 || c >= 0xe000) { bytes.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f)); }
      else { i++; var cp = ((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff); cp += 0x10000; bytes.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f)); }
    }

    var msgLen = bytes.length;
    bytes.push(0x80);
    while ((bytes.length % 64) !== 56) bytes.push(0);

    var bitLen = msgLen * 8;
    for (var j = 0; j < 4; j++) bytes.push((bitLen >>> (j * 8)) & 0xff);
    for (var j2 = 0; j2 < 4; j2++) bytes.push((bitLen / 0x100000000) >>> (j2 * 8) & 0xff);

    // Process 64-byte blocks
    var state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476];
    for (var bi = 0; bi < bytes.length; bi += 64) {
      var block = [];
      for (var j3 = 0; j3 < 16; j3++) {
        var off = bi + j3 * 4;
        block[j3] = bytes[off] | (bytes[off+1] << 8) | (bytes[off+2] << 16) | (bytes[off+3] << 24);
      }
      md5cycle(state, block);
    }

    var hex = '';
    for (var i3 = 0; i3 < 4; i3++) {
      for (var j4 = 0; j4 < 4; j4++) {
        var byteVal = (state[i3] >>> (j4 * 8)) & 0xff;
        hex += (byteVal < 16 ? '0' : '') + byteVal.toString(16);
      }
    }
    return hex;
  }

  // ---- 5.2.1 文本选中检测 + 操作条 ----

  function createActionBar() {
    if (actionBar) return actionBar;
    const bar = document.createElement('div');
    bar.className = 'ispace-inline-action-bar';
    bar.innerHTML = `
      <button class="ispace-inline-action-btn" data-action="comment" title="评论">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </button>
      <button class="ispace-inline-action-btn" data-action="copy" title="复制">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>
      </button>
      <button class="ispace-inline-action-btn" data-action="highlight" title="高亮">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
      </button>
    `;
    document.body.appendChild(bar);

    bar.addEventListener('click', function (e) {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === 'comment') {
        openInlineComment();
      } else if (action === 'copy') {
        copySelectedText();
      } else if (action === 'highlight') {
        highlightSelectedText();
      }
      hideActionBar();
    });

    actionBar = bar;
    return bar;
  }

  function showActionBar(rect) {
    const bar = createActionBar();
    var barWidth = 120;
    var barHeight = 44;
    var viewportW = window.innerWidth;
    var viewportH = window.innerHeight;
    var scrollY = window.pageYOffset || document.documentElement.scrollTop;
    var scrollX = window.pageXOffset || document.documentElement.scrollLeft;

    // 水平居中于选区，但保持在视口内
    var left = rect.left + rect.width / 2 - barWidth / 2 + scrollX;
    left = Math.max(8 + scrollX, Math.min(left, viewportW - barWidth - 8 + scrollX));

    // 默认显示在选区上方，如果空间不够则显示在下方
    var aboveY = rect.top + scrollY - barHeight - 6;
    var belowY = rect.bottom + scrollY + 6;
    if (rect.top - barHeight - 6 < 0) {
      // 上方空间不足，显示在选区下方
      var top = belowY;
    } else {
      var top = aboveY;
    }
    // 确保不超出底部视口
    if (top + barHeight - scrollY > viewportH - 8) {
      top = Math.max(8 + scrollY, aboveY - (top + barHeight - scrollY - viewportH + 8));
    }

    bar.style.left = left + 'px';
    bar.style.top = top + 'px';
    bar.classList.add('active');
  }

  function hideActionBar() {
    if (actionBar) actionBar.classList.remove('active');
  }

  document.addEventListener('mouseup', function (e) {
    setTimeout(function () {
      const anchor = getSelectionAnchor();
      if (anchor) {
        currentSelection = anchor;
        const rect = anchor.range.getBoundingClientRect();
        showActionBar(rect);
      } else {
        // 仅当选区不在评论面板内时才清除 currentSelection
        // 评论面板内的点击不应影响已保存的 pendingSubmitAnchor
        if (commentPanel && commentPanel.classList.contains('active') && commentPanel.contains(e.target)) {
          return;
        }
        currentSelection = null;
        hideActionBar();
      }
    }, 10);
  });

  // 全局点击监听：点击操作条或评论面板外部时关闭对应 UI
  // 使用 capture 阶段，确保在 Vditor 等第三方库拦截事件之前处理关闭逻辑
  document.addEventListener('mousedown', function (e) {
    // 点击操作条外部 → 隐藏操作条
    if (actionBar && actionBar.classList.contains('active') && !actionBar.contains(e.target)) {
      hideActionBar();
    }
    // 点击评论面板外部 → 关闭评论面板（排除 @mention 下拉列表）
    if (commentPanel && commentPanel.classList.contains('active') &&
        !commentPanel.contains(e.target) &&
        !(actionBar && actionBar.contains(e.target)) &&
        !e.target.closest('.ispace-mention-dropdown')) {
      commentPanel.classList.remove('active');
      activeMarkerKey = null;
    }
  }, true);

  // ---- 5.2.2 选中文字标记渲染 ----

  function renderMarkers(inlineCommentGroups) {
    // 清除旧标记
    docContent.querySelectorAll('.ispace-inline-marker').forEach(function (el) {
      const parent = el.parentNode;
      parent.replaceChild(document.createTextNode(el.textContent), el);
      parent.normalize();
    });

    // 重新渲染所有标记
    inlineCommentGroups.forEach(function (group) {
      applyMarker(group.anchor_start, group.anchor_end, group.count);
    });
  }

  function applyMarker(anchorStart, anchorEnd, count) {
    // 收集锚点范围内的所有文本节点
    var walker = document.createTreeWalker(docContent, NodeFilter.SHOW_TEXT, null);
    var pos = 0;
    var node;
    var rangeNodes = [];

    while ((node = walker.nextNode())) {
      var len = node.textContent.length;
      var nodeEnd = pos + len;
      if (nodeEnd > anchorStart && pos < anchorEnd) {
        rangeNodes.push({
          node: node,
          localStart: Math.max(0, anchorStart - pos),
          localEnd: Math.min(len, anchorEnd - pos),
        });
      }
      pos = nodeEnd;
      if (pos >= anchorEnd) break;
    }

    if (rangeNodes.length === 0) return;

    // 从后往前处理，避免修改前面的节点后后面节点的引用失效
    for (var i = rangeNodes.length - 1; i >= 0; i--) {
      var item = rangeNodes[i];
      var textNode = item.node;
      var text = textNode.textContent;
      var before = text.substring(0, item.localStart);
      var selected = text.substring(item.localStart, item.localEnd);
      var after = text.substring(item.localEnd);

      var mark = document.createElement('mark');
      mark.className = 'ispace-inline-marker';
      mark.dataset.anchorStart = anchorStart;
      mark.dataset.anchorEnd = anchorEnd;
      mark.textContent = selected;

      // 气泡图标仅附加在最后一个文本节点片段上
      if (i === rangeNodes.length - 1) {
        var bubble = document.createElement('sup');
        bubble.className = 'ispace-inline-bubble';
        bubble.dataset.anchorStart = anchorStart;
        bubble.dataset.anchorEnd = anchorEnd;
        mark.appendChild(bubble);
      }

      var fragment = document.createDocumentFragment();
      if (before) fragment.appendChild(document.createTextNode(before));
      fragment.appendChild(mark);
      if (after) fragment.appendChild(document.createTextNode(after));

      textNode.parentNode.replaceChild(fragment, textNode);
      textNode.parentNode.normalize();
    }
  }

  // ---- 5.2.4 评论面板 ----

  function createCommentPanel() {
    if (commentPanel) return commentPanel;

    const panel = document.createElement('div');
    panel.className = 'ispace-inline-comment-panel';
    panel.innerHTML = `
      <div class="ispace-inline-comment-panel-header">
        <h4>划词评论</h4>
        <button class="ispace-inline-comment-panel-close">&times;</button>
      </div>
      <div class="ispace-inline-comment-panel-body" id="inline-comment-list"></div>
      <div class="ispace-inline-reply-indicator" id="inline-reply-indicator" style="display:none;">
        <span class="ispace-inline-reply-indicator-text">
          回复 <strong id="inline-reply-target-name"></strong>
        </span>
        <button class="ispace-inline-reply-cancel" id="inline-reply-cancel">&times;</button>
      </div>
      <div class="ispace-inline-comment-panel-input">
        <textarea id="inline-comment-input" placeholder="发表评论..." maxlength="2000" rows="3"></textarea>
        <div class="ispace-inline-comment-panel-actions">
          <span class="ispace-inline-comment-char-count" id="inline-comment-char-count">0/2000</span>
          <button class="ispace-btn ispace-btn-primary ispace-btn-sm" id="inline-comment-submit">发表</button>
        </div>
      </div>
    `;
    document.body.appendChild(panel);

    panel.querySelector('.ispace-inline-comment-panel-close').addEventListener('click', function () {
      panel.classList.remove('active');
      activeMarkerKey = null;
      replyToCommentId = null;
      setReplyTarget(null);
    });

    panel.querySelector('#inline-reply-cancel').addEventListener('click', function () {
      replyToCommentId = null;
      setReplyTarget(null);
    });

    const textarea = panel.querySelector('#inline-comment-input');
    textarea.addEventListener('input', function () {
      document.getElementById('inline-comment-char-count').textContent =
        this.value.length + '/2000';
    });

    panel.querySelector('#inline-comment-submit').addEventListener('click', submitInlineComment);

    // 初始化 @mention 选择器
    if (window.iSpaceDoc && window.iSpaceDoc.MentionSelector && textarea && !textarea._mentionSelector) {
      textarea._mentionSelector = new window.iSpaceDoc.MentionSelector(textarea);
    }

    commentPanel = panel;
    return panel;
  }

  function openInlineComment() {
    if (!currentSelection) return;
    // 保存锚点快照，防止后续鼠标事件清除 currentSelection
    pendingSubmitAnchor = {
      text: currentSelection.text,
      anchorStart: currentSelection.anchorStart,
      anchorEnd: currentSelection.anchorEnd,
      anchorHash: currentSelection.anchorHash,
    };
    showCommentPanel(currentSelection);
  }

  function showCommentPanel(anchor) {
    const panel = createCommentPanel();
    activeMarkerKey = anchor.anchorStart + ':' + anchor.anchorEnd;
    panel.classList.add('active');

    // 更新面板标题
    const header = panel.querySelector('.ispace-inline-comment-panel-header h4');
    const displayText = anchor.text.length > 30 ? anchor.text.substring(0, 30) + '...' : anchor.text;
    header.textContent = '划词评论: "' + displayText + '"';

    // 清空输入框
    panel.querySelector('#inline-comment-input').value = '';
    document.getElementById('inline-comment-char-count').textContent = '0/2000';

    // 加载已有评论
    loadInlineComments(anchor);
  }

  function loadInlineComments(anchor) {
    const docId = window._docId;
    if (!docId) return;

    const listEl = document.getElementById('inline-comment-list');
    listEl.innerHTML = '<div class="ispace-inline-comment-loading">加载中...</div>';

    fetch('/pages/' + docId + '/inline-comments/')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.status || !resp.data) {
          listEl.innerHTML = '<div class="ispace-inline-comment-empty">暂无评论</div>';
          return;
        }
        // 找到当前锚点的评论组
        const key = anchor.anchorStart + ':' + anchor.anchorEnd;
        const group = resp.data.find(function (g) {
          return (g.anchor_start + ':' + g.anchor_end) === key;
        });
        if (!group || !group.comments.length) {
          listEl.innerHTML = '<div class="ispace-inline-comment-empty">暂无评论</div>';
          return;
        }
        // 递归渲染评论树
        function renderCommentTree(comment, depth) {
          depth = depth || 0;
          var deleteBtn = comment.can_delete
            ? '<button class="ispace-inline-comment-delete" data-id="' + comment.id + '" title="删除">&times;</button>'
            : '';
          var repliesHtml = '';
          if (comment.replies && comment.replies.length) {
            repliesHtml = '<div class="ispace-inline-comment-replies">' +
              comment.replies.map(function (r) { return renderCommentTree(r, depth + 1); }).join('') +
              '</div>';
          }
          var replyBtn = '<button class="ispace-inline-comment-reply-btn" data-id="' + comment.id + '">回复</button>';
          var itemClass = depth > 0 ? ' ispace-inline-comment-reply-item' : '';
          return '<div class="ispace-inline-comment-item' + itemClass + '">' +
            '<div class="ispace-inline-comment-item-header">' +
            '<strong data-user-id="' + (comment.user_id || '') + '">' + escapeHtml(comment.user_name) + '</strong>' +
            '<span class="ispace-inline-comment-time">' + comment.create_time + '</span>' +
            deleteBtn +
            '</div>' +
            '<div class="ispace-inline-comment-item-body">' + (comment.content_html || escapeHtml(comment.content)) + '</div>' +
            replyBtn +
            repliesHtml +
            '</div>';
        }

        listEl.innerHTML = group.comments.map(function (c) {
          return renderCommentTree(c, 0);
        }).join('');

        // 删除按钮事件
        listEl.querySelectorAll('.ispace-inline-comment-delete').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteInlineComment(parseInt(this.dataset.id));
          });
        });

        // 回复按钮事件
        listEl.querySelectorAll('.ispace-inline-comment-reply-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var commentId = parseInt(this.dataset.id);
            if (replyToCommentId === commentId) {
              replyToCommentId = null;
              setReplyTarget(null);
            } else {
              replyToCommentId = commentId;
              setReplyTarget(commentId, this.closest('.ispace-inline-comment-item'));
            }
          });
        });
      })
      .catch(function () {
        listEl.innerHTML = '<div class="ispace-inline-comment-empty">加载失败</div>';
      });
  }

  function submitInlineComment() {
    const textarea = document.getElementById('inline-comment-input');
    const content = textarea.value.trim();
    if (!content) return;

    const docId = window._docId;
    if (!docId) return;

    var submitBtn = document.getElementById('inline-comment-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';

    // 优先使用 pendingSubmitAnchor（从操作条打开时保存的快照），
    // 其次使用 currentSelection，最后回退到 activeMarkerKey
    var anchor = pendingSubmitAnchor || currentSelection || {};
    if (!anchor.anchorStart && activeMarkerKey) {
      var parts = activeMarkerKey.split(':');
      anchor.anchorStart = parseInt(parts[0]);
      anchor.anchorEnd = parseInt(parts[1]);
      anchor.text = '';
      anchor.anchorHash = '';
    }

    fetch('/pages/' + docId + '/inline-comments/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        anchor_start: anchor.anchorStart,
        anchor_end: anchor.anchorEnd,
        anchor_hash: anchor.anchorHash,
        selected_text: anchor.text || '',
        content: content,
        parent_id: replyToCommentId || null,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        submitBtn.disabled = false;
        submitBtn.textContent = '发表';
        if (resp.status) {
          textarea.value = '';
          document.getElementById('inline-comment-char-count').textContent = '0/2000';
          // 构建重载用的锚点数据
          var reloadAnchor = {
            anchorStart: anchor.anchorStart,
            anchorEnd: anchor.anchorEnd,
            text: anchor.text || '',
          };
          loadInlineComments(reloadAnchor);
          pendingSubmitAnchor = null;
          replyToCommentId = null;
          setReplyTarget(null);
          refreshAllInlineComments();
        } else {
          alert(resp.data);
        }
      })
      .catch(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = '发表';
        alert('提交失败，请重试');
      });
  }

  function deleteInlineComment(commentId) {
    if (!confirm('确定删除该评论？')) return;
    fetch('/comments/inline/' + commentId + '/delete/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
    })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (resp.status) {
          refreshAllInlineComments();
        } else {
          alert(resp.data);
        }
      });
  }

  function refreshAllInlineComments() {
    var docId = window._docId;
    if (!docId) return;

    fetch('/pages/' + docId + '/inline-comments/')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (resp.status && resp.data) {
          renderMarkers(resp.data);
        }
      });
  }

  // ---- 点击气泡展开评论 ----

  docContent.addEventListener('click', function (e) {
    var bubble = e.target.closest('.ispace-inline-bubble');
    if (!bubble) return;

    var anchorStart = parseInt(bubble.dataset.anchorStart);
    var anchorEnd = parseInt(bubble.dataset.anchorEnd);

    // 获取标记文本
    var marker = bubble.closest('.ispace-inline-marker');
    var text = marker ? marker.textContent.replace(bubble.textContent, '') : '';

    var anchor = {
      text: text,
      anchorStart: anchorStart,
      anchorEnd: anchorEnd,
      anchorHash: md5(text),
    };
    currentSelection = anchor;
    // 点击气泡时也保存锚点快照
    pendingSubmitAnchor = {
      text: anchor.text,
      anchorStart: anchor.anchorStart,
      anchorEnd: anchor.anchorEnd,
      anchorHash: anchor.anchorHash,
    };
    showCommentPanel(anchor);
  });

  // ---- 复制选中文本 ----

  function copySelectedText() {
    if (!currentSelection) return;
    navigator.clipboard.writeText(currentSelection.text).catch(function () {
      // fallback
      var textarea = document.createElement('textarea');
      textarea.value = currentSelection.text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    });
  }

  // ---- 高亮选中文本 ----

  function getHighlightKey() {
    var docId = window._docId;
    return 'ispace_hl_' + (docId || 0);
  }

  function loadHighlights() {
    try {
      var raw = localStorage.getItem(getHighlightKey());
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  function saveHighlights(list) {
    try {
      localStorage.setItem(getHighlightKey(), JSON.stringify(list));
    } catch (e) { /* quota exceeded, ignore */ }
  }

  function highlightSelectedText() {
    if (!currentSelection) return;
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;

    var range = sel.getRangeAt(0);
    var span = document.createElement('span');
    span.className = 'ispace-inline-highlight';
    try {
      range.surroundContents(span);
    } catch (e) {
      document.execCommand('hiliteColor', false, '#ffeb3b');
    }

    // 持久化到 localStorage
    var list = loadHighlights();
    var entry = {
      anchor_start: currentSelection.anchorStart,
      anchor_end: currentSelection.anchorEnd,
      text: currentSelection.text,
    };
    // 去重：相同锚点不重复添加
    var dup = false;
    for (var i = 0; i < list.length; i++) {
      if (list[i].anchor_start === entry.anchor_start && list[i].anchor_end === entry.anchor_end) {
        dup = true; break;
      }
    }
    if (!dup) { list.push(entry); saveHighlights(list); }
  }

  function renderHighlights() {
    var highlights = loadHighlights();
    if (!highlights.length) return;

    highlights.forEach(function (hl) {
      // 收集锚点范围内的所有文本节点
      var walker = document.createTreeWalker(docContent, NodeFilter.SHOW_TEXT, null);
      var pos = 0;
      var node;
      var rangeNodes = [];

      while ((node = walker.nextNode())) {
        var len = node.textContent.length;
        var nodeEnd = pos + len;
        if (nodeEnd > hl.anchor_start && pos < hl.anchor_end) {
          rangeNodes.push({
            node: node,
            localStart: Math.max(0, hl.anchor_start - pos),
            localEnd: Math.min(len, hl.anchor_end - pos),
          });
        }
        pos = nodeEnd;
        if (pos >= hl.anchor_end) break;
      }

      if (rangeNodes.length === 0) return;

      // 从后往前处理
      for (var i = rangeNodes.length - 1; i >= 0; i--) {
        var item = rangeNodes[i];
        var textNode = item.node;
        var text = textNode.textContent;
        var before = text.substring(0, item.localStart);
        var selected = text.substring(item.localStart, item.localEnd);
        var after = text.substring(item.localEnd);

        var span = document.createElement('span');
        span.className = 'ispace-inline-highlight';
        span.textContent = selected;
        span.title = '双击取消高亮';

        var fragment = document.createDocumentFragment();
        if (before) fragment.appendChild(document.createTextNode(before));
        fragment.appendChild(span);
        if (after) fragment.appendChild(document.createTextNode(after));

        textNode.parentNode.replaceChild(fragment, textNode);
        textNode.parentNode.normalize();
      }
    });
  }

  // 双击高亮区域取消高亮
  docContent.addEventListener('dblclick', function (e) {
    var hl = e.target.closest('.ispace-inline-highlight');
    if (!hl) return;

    e.preventDefault();
    var text = hl.textContent;
    var parent = hl.parentNode;

    // 计算锚点以从 localStorage 中移除对应条目
    var anchorStart = getTextOffset(docContent, hl.firstChild || hl, 0);
    var anchorEnd = anchorStart + text.length;

    var list = loadHighlights();
    for (var i = list.length - 1; i >= 0; i--) {
      if (list[i].anchor_start === anchorStart && list[i].anchor_end === anchorEnd) {
        list.splice(i, 1);
      }
    }
    saveHighlights(list);

    parent.replaceChild(document.createTextNode(text), hl);
    parent.normalize();
  });

  // ---- CSRF Token ----

  function getCsrfToken() {
    var cookie = document.cookie.match(/csrftoken=([^;]+)/);
    return cookie ? cookie[1] : '';
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /** 设置/清除回复目标 */
  function setReplyTarget(commentId, itemEl) {
    var indicator = document.getElementById('inline-reply-indicator');
    var nameEl = document.getElementById('inline-reply-target-name');
    var textarea = document.getElementById('inline-comment-input');
    var submitBtn = document.getElementById('inline-comment-submit');

    if (!commentId || !itemEl) {
      // 取消回复
      if (indicator) indicator.style.display = 'none';
      if (nameEl) nameEl.textContent = '';
      if (textarea) textarea.placeholder = '发表评论...';
      if (submitBtn) submitBtn.textContent = '发表';
      // 移除所有回复高亮
      if (commentPanel) {
        commentPanel.querySelectorAll('.ispace-inline-comment-reply-target').forEach(function (el) {
          el.classList.remove('ispace-inline-comment-reply-target');
        });
      }
      return;
    }

    // 设置回复目标
    var userName = itemEl.querySelector('strong');
    var targetName = userName ? userName.textContent : '用户';
    if (indicator) indicator.style.display = 'flex';
    if (nameEl) nameEl.textContent = targetName;
    if (textarea) {
      textarea.placeholder = '回复 ' + targetName + '...';
      textarea.focus();
    }
    if (submitBtn) submitBtn.textContent = '回复';

    // 高亮被回复的评论
    if (commentPanel) {
      commentPanel.querySelectorAll('.ispace-inline-comment-reply-target').forEach(function (el) {
        el.classList.remove('ispace-inline-comment-reply-target');
      });
    }
    itemEl.classList.add('ispace-inline-comment-reply-target');
  }

  // ---- 初始化：加载已有标记 ----

  function init() {
    var docId = window._docId;
    if (!docId) return;

    fetch('/pages/' + docId + '/inline-comments/')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (resp.status && resp.data && resp.data.length > 0) {
          renderMarkers(resp.data);
        }
      })
      .catch(function () { /* 忽略初始化加载失败 */ })
      .finally(function () {
        // 渲染持久化高亮
        renderHighlights();
      });
  }

  // 延迟初始化，等待 Vditor 渲染完成
  setTimeout(init, 800);

  // 导出 API
  window.InlineComments = {
    refresh: refreshAllInlineComments,
    getCount: function () {
      return docContent.querySelectorAll('.ispace-inline-marker').length;
    },
  };
})();
