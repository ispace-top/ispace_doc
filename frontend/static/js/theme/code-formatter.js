/**
 * 代码块自动格式化 — 文档正文区代码块按语言类型格式化。
 *
 * 用法: CodeFormatter.init()
 * Ctrl+Shift+F: 格式化当前文档的第一个代码块
 * 工具栏按钮: 格式化当前文档的第一个代码块
 */
(function () {
  'use strict';

  var FORMAT_API = '/api/format-code/';
  var LANG_MAP = {
    json: 'json', json5: 'json',
    py: 'python', python: 'python',
    js: 'generic', javascript: 'generic',
    html: 'generic', css: 'generic',
    java: 'generic', go: 'generic', rust: 'generic',
    ts: 'generic', tsx: 'generic', sql: 'generic',
  };

  var csrfToken = window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken || '';

  function init() {
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
        e.preventDefault();
        formatFocusedCodeBlock();
      }
    });
  }

  function getCodeBlockContent() {
    // Try Vditor IR mode: find the first code block in the editor
    var codeBlock = document.querySelector('[data-type="code-block"]');
    if (codeBlock) {
      var codeEl = codeBlock.querySelector('code[class*="language-"]');
      if (codeEl) {
        var lang = '';
        var match = (codeEl.className || '').match(/language-(\w+)/);
        if (match) lang = LANG_MAP[match[1]] || match[1];
        return { code: codeEl.textContent || '', lang: lang, element: codeEl, isVditor: true };
      }
    }
    // View mode: find a pre code block
    var viewCode = document.querySelector('.markdown-body code[class*="language-"], #vditor-doc-content code[class*="language-"]');
    if (viewCode) {
      var lang2 = '';
      var match2 = (viewCode.className || '').match(/language-(\w+)/);
      if (match2) lang2 = LANG_MAP[match2[1]] || match2[1];
      return { code: viewCode.textContent || '', lang: lang2, element: viewCode, isVditor: false };
    }
    return null;
  }

  function formatFocusedCodeBlock() {
    var info = getCodeBlockContent();
    if (!info || !info.code.trim()) {
      showToast('warning', '未找到代码块或代码块内容为空');
      return;
    }

    // Visual feedback
    var codeBlock = info.element.closest('[data-type="code-block"]') || info.element.closest('pre');
    if (codeBlock) codeBlock.style.boxShadow = 'inset 0 0 0 2px var(--ispace-color-brand-500, #d4843a)';

    fetch(FORMAT_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ code: info.code, language: info.lang || '' }),
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (codeBlock) codeBlock.style.boxShadow = '';
      if (data.code === 0 && data.data && data.data.formatted && data.data.formatted !== info.code) {
        applyFormattedCode(data.data.formatted, info);
        showToast('success', '格式化完成');
      } else if (data.code === 0 && data.data && data.data.formatted === info.code) {
        showToast('info', '代码已格式良好');
      } else {
        showToast('error', data.msg || '格式化失败');
      }
    })
    .catch(function () {
      if (codeBlock) codeBlock.style.boxShadow = '';
      showToast('error', '格式化请求失败');
    });
  }

  function applyFormattedCode(formatted, info) {
    if (info.isVditor && window._inlineEditor) {
      // For Vditor: replace content via setValue/getValue
      var full = window._inlineEditor.getValue();
      var oldCode = info.code;
      var idx = full.indexOf(oldCode);
      if (idx >= 0) {
        var newFull = full.substring(0, idx) + formatted + full.substring(idx + oldCode.length);
        window._inlineEditor.setValue(newFull);
      } else {
        // Fallback: update DOM directly
        info.element.textContent = formatted;
      }
    } else {
      // View mode: update DOM
      info.element.textContent = formatted;
    }
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
