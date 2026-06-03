/**
 * 表格列宽拖拽调整 — 所有列（含最后一列）支持拖拽，宽度持久化。
 *
 * 用法: TableResize.init(containerSelector)
 * 默认容器: '.markdown-body, #vditor-doc-content'
 */
(function () {
  'use strict';

  var CONTAINER_SELECTOR = '.markdown-body, #vditor-doc-content';
  var MIN_COL_WIDTH = 60;

  var state = null;

  function init(containerSelector) {
    containerSelector = containerSelector || CONTAINER_SELECTOR;
    var containers = document.querySelectorAll(containerSelector);
    Array.prototype.forEach.call(containers, function (container) {
      makeTablesResizable(container);
      if (window.MutationObserver) {
        var timer = null;
        var observer = new MutationObserver(function () {
          clearTimeout(timer);
          timer = setTimeout(function () { makeTablesResizable(container); }, 200);
        });
        observer.observe(container, { childList: true, subtree: true });
      }
    });
  }

  function makeTablesResizable(container) {
    var tables = container.querySelectorAll('table');
    Array.prototype.forEach.call(tables, function (table, tableIdx) {
      if (table.hasAttribute('data-table-resize')) return;
      table.setAttribute('data-table-resize', 'enabled');
      table.setAttribute('data-table-idx', tableIdx);
      addDragHandles(table);
    });
    // Load persisted widths for each table
    if (window._docId && tables.length > 0 && !container.hasAttribute('data-widths-loaded')) {
      container.setAttribute('data-widths-loaded', '1');
      loadWidths(tables);
    }
  }

  function loadWidths(tables) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/docs/' + window._docId + '/table-widths/load/', true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.onload = function () {
      try {
        var data = JSON.parse(xhr.responseText);
        if (!data.status) return;
        var widths = data.widths || [];
        if (!widths.length) return;
        Array.prototype.forEach.call(tables, function (table, ti) {
          // data.widths is a flat array of widths per column for the first table
          // For simplicity, apply to each table
          var rows = table.querySelectorAll('tr');
          if (!rows.length) return;
          var colEls = rows[0].querySelectorAll('th, td');
          widths.forEach(function (w, idx) {
            if (idx >= colEls.length) return;
            Array.prototype.forEach.call(rows, function (row) {
              var cell = row.querySelectorAll('th, td')[idx];
              if (cell) { cell.style.width = w + 'px'; cell.style.minWidth = w + 'px'; }
            });
          });
        });
      } catch (e) {}
    };
    xhr.send();
  }

  function addDragHandles(table) {
    var headerRow = table.querySelector('thead tr') || table.querySelector('tr');
    if (!headerRow) return;
    var cells = headerRow.querySelectorAll('th, td');
    Array.prototype.forEach.call(cells, function (cell, index) {
      // All columns get a handle (including last column)
      if (cell.querySelector('.ispace-col-resizer')) return;
      var resizer = document.createElement('div');
      resizer.className = 'ispace-col-resizer';
      resizer.setAttribute('data-col-idx', index);
      resizer.style.cssText =
        'position:absolute;top:0;right:-2px;width:8px;height:100%;' +
        'cursor:col-resize;z-index:10;' +
        'border-right:2px solid var(--ispace-color-surface-200,#ddd);';
      cell.style.position = 'relative';
      resizer.addEventListener('mousedown', function (e) {
        e.preventDefault();
        startResize(table, index, e.clientX);
      });
      cell.appendChild(resizer);
    });
  }

  function startResize(table, colIndex, startX) {
    var rows = table.querySelectorAll('tr');
    var cellWidths = [];
    Array.prototype.forEach.call(rows, function (row) {
      var cells = row.querySelectorAll('th, td');
      if (cells[colIndex]) {
        cellWidths.push({ cell: cells[colIndex], width: cells[colIndex].getBoundingClientRect().width });
      }
    });
    state = { table: table, colIndex: colIndex, startX: startX, cellWidths: cellWidths };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e) {
    if (!state) return;
    var delta = e.clientX - state.startX;
    var newWidth = Math.max(MIN_COL_WIDTH, state.cellWidths[0].width + delta);
    Array.prototype.forEach.call(state.cellWidths, function (item) {
      item.cell.style.width = newWidth + 'px';
      item.cell.style.minWidth = newWidth + 'px';
      item.cell.style.maxWidth = newWidth + 'px';
    });
    showWidthTooltip(e.clientX, e.clientY, Math.round(newWidth) + 'px');
  }

  function onMouseUp() {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    hideWidthTooltip();
    if (state && state.table && window._docId) {
      persistWidths(state.table);
    }
    state = null;
  }

  function persistWidths(table) {
    var rows = table.querySelectorAll('tr');
    if (!rows.length) return;
    var cells = rows[0].querySelectorAll('th, td');
    if (!cells.length) return;
    var widths = [];
    Array.prototype.forEach.call(cells, function (cell) {
      widths.push(Math.round(cell.getBoundingClientRect().width));
    });
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/docs/' + window._docId + '/table-widths/save/', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', (window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken) || '');
    xhr.onerror = function () { console.warn('[TableResize] 列宽保存失败'); };
    xhr.send(JSON.stringify({ widths: widths }));
  }

  var tooltipEl = null;

  function showWidthTooltip(x, y, text) {
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.className = 'ispace-col-resize-tooltip';
      tooltipEl.style.cssText =
        'position:fixed;background:#333;color:#fff;padding:2px 8px;' +
        'border-radius:4px;font-size:12px;z-index:10000;' +
        'pointer-events:none;white-space:nowrap;';
      document.body.appendChild(tooltipEl);
    }
    tooltipEl.style.left = (x + 12) + 'px';
    tooltipEl.style.top = (y - 24) + 'px';
    tooltipEl.textContent = text;
  }

  function hideWidthTooltip() {
    if (tooltipEl) { tooltipEl.remove(); tooltipEl = null; }
  }

  window.TableResize = { init: init };
})();
