/**
 * 代码块自动格式化 — 文档正文区代码块按语言类型格式化。
 *
 * 用法: CodeFormatter.init()
 * 快捷键: Ctrl+Shift+F 格式化当前焦点代码块
 */
(function () {
  'use strict';

  var FORMAT_API = '/api/format-code/';
  var LANG_MAP = {
    json: 'json', json5: 'json',
    py: 'python', python: 'python',
    js: 'generic', javascript: 'generic', jsx: 'generic',
    html: 'generic', css: 'generic',
    java: 'generic', go: 'generic', rust: 'generic',
    ts: 'generic', tsx: 'generic', sql: 'generic',
    sh: 'generic', bash: 'generic', php: 'generic', c: 'generic', cpp: 'generic',
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

  function getFocusedCodeBlock() {
    var active = document.activeElement;
    // Vditor IR mode: the code block might be inside a .vditor-ir container
    var codeBlock = active && active.closest && active.closest('pre code, .language-');
    if (codeBlock) return codeBlock;

    // Check if focus is inside vditor content
    var vditor = document.querySelector('.vditor-ir, .vditor-wysiwyg');
    if (vditor && vditor.contains(active)) {
      // Find the nearest code block
      var pre = active.closest('pre');
      if (pre) return pre.querySelector('code');
    }
    return null;
  }

  function formatFocusedCodeBlock() {
    var codeEl = getFocusedCodeBlock();
    if (!codeEl) {
      showToast('warning', '请将光标置于代码块中');
      return;
    }

    var code = codeEl.textContent || '';
    if (!code.trim()) {
      showToast('warning', '代码块内容为空');
      return;
    }

    // Detect language from class
    var lang = '';
    // Actually determine language
    var classStr = (codeEl.className || '') + ' ' + (codeEl.parentElement ? codeEl.parentElement.className || '' : '');
    var match = classStr.match(/language-(\w+)/);
    if (match) {
      lang = LANG_MAP[match[1]] || match[1];
    }
    if (!lang) {
      // Try to detect from content
      lang = detectLanguage(code);
    }

    // Visual feedback — add formatting pulse
    var pre = codeEl.closest('pre');
    if (pre) pre.style.boxShadow = 'inset 0 0 0 2px var(--ispace-color-brand-500, #d4843a)';

    fetch(FORMAT_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ code: code, language: lang }),
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (pre) pre.style.boxShadow = '';
      if (data.code === 0 && data.data && data.data.formatted) {
        codeEl.textContent = data.data.formatted;
        showToast('success', '格式化完成');
      } else {
        showToast('error', data.msg || '格式化失败');
      }
    })
    .catch(function () {
      if (pre) pre.style.boxShadow = '';
      showToast('error', '格式化请求失败');
    });
  }

  function detectLanguage(code) {
    var trimmed = code.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try { JSON.parse(trimmed); return 'json'; } catch(e) {}
    }
    if (trimmed.startsWith('import ') || trimmed.startsWith('def ') || trimmed.startsWith('class ')) {
      return 'python';
    }
    if (trimmed.startsWith('function ') || trimmed.startsWith('const ') || trimmed.startsWith('let ') || trimmed.startsWith('var ')) {
      return 'javascript';
    }
    if (trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html') || trimmed.startsWith('<div')) {
      return 'html';
    }
    return '';
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

  // Export API
  window.CodeFormatter = {
    init: init,
    formatFocused: formatFocusedCodeBlock,
  };
})();
