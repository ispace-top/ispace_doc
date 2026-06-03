/**
 * 代码块自动格式化 — 通过正则解析 Markdown 代码块再写回。
 * 完全不依赖 Vditor DOM，避免 IR 模式渲染冲突。
 *
 * 用法: CodeFormatter.init()
 * Ctrl+Shift+F / 工具栏按钮: 格式化所有代码块
 */
(function () {
  'use strict';

  var FORMAT_API = '/api/format-code/';
  var csrfToken = '';

  function init() {
    csrfToken = (window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken) || '';
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
        e.preventDefault();
        formatFocusedCodeBlock();
      }
    });
  }

  function formatFocusedCodeBlock() {
    if (!window._inlineEditor) {
      showToast('warning', '编辑器未就绪');
      return;
    }

    var md = window._inlineEditor.getValue();
    if (!md) {
      showToast('warning', '文档内容为空');
      return;
    }

    // Parse fenced code blocks from Markdown: ```lang\n...\n```
    var blocks = [];
    var regex = /```(\w+)\n([\s\S]*?)```/g;
    var match;
    while ((match = regex.exec(md)) !== null) {
      blocks.push({
        lang: match[1].toLowerCase(),
        code: match[2],
        fullMatch: match[0],
        index: match.index,
      });
    }

    if (blocks.length === 0) {
      showToast('info', '未找到代码块');
      return;
    }

    // Fire all API requests in parallel, then single setValue
    var fetches = blocks.map(function (b) {
      return fetch(FORMAT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ code: b.code, language: b.lang }),
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.code === 0 && data.data && data.data.formatted && data.data.formatted !== b.code) {
          return { index: b.index, oldCode: b.fullMatch, newCode: '```' + b.lang + '\n' + data.data.formatted + '```' };
        }
        return null;
      });
    });

    Promise.all(fetches).then(function (results) {
      var changed = 0;
      var unchanged = 0;
      // Apply from end to start to preserve indices
      results = results.filter(function (r) { return r; });
      results.sort(function (a, b) { return b.index - a.index; });
      results.forEach(function (r) {
        var pos = md.indexOf(r.oldCode);
        if (pos >= 0 && pos === r.index) {
          md = md.substring(0, pos) + r.newCode + md.substring(pos + r.oldCode.length);
          changed++;
        }
      });
      unchanged = blocks.length - changed - (blocks.length - results.length);

      if (changed > 0) {
        window._inlineEditor.setValue(md);
      }
      var msg = '格式化完成 ' + changed + ' 个';
      if (unchanged > 0) msg += '，' + unchanged + ' 个无需修改';
      showToast(changed > 0 ? 'success' : 'info', msg);
    });
  }

  function showToast(type, msg) {
    if (window.iSpaceDoc && window.iSpaceDoc.Toast) {
      var fn = type === 'success' ? 'success' : type === 'error' ? 'error' : 'info';
      window.iSpaceDoc.Toast[fn](msg);
    } else if (typeof layer !== 'undefined') {
      layer.msg(msg);
    } else {
      console.log('[' + type + '] ' + msg);
    }
  }

  window.CodeFormatter = {
    init: init,
    formatFocused: formatFocusedCodeBlock,
  };
})();
