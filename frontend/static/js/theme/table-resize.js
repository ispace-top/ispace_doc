/**
 * 表格列宽拖拽调整 — 文档正文区内所有表格支持列边框拖拽调整宽度。
 *
 * 用法: TableResize.init(containerSelector)
 * 默认容器: '.markdown-body, #vditor-doc-content'
 */
(function () {
  'use strict';

  var CONTAINER_SELECTOR = '.markdown-body, #vditor-doc-content';
  var MIN_COL_WIDTH = 40;

  var state = null; // { table, colIndex, startX, startWidth, colWidths, cells }

  function init(containerSelector) {
    containerSelector = containerSelector || CONTAINER_SELECTOR;
    var containers = document.querySelectorAll(containerSelector);
    containers.forEach(function (container) {
      makeTablesResizable(container);
      // 监 hearing 动态插入的内容（SPA 页面切换后重新绑定）
      if (window.MutationObserver) {
        var observer = new MutationObserver(function () {
          makeTablesResizable(container);
        });
        observer.observe(container, { childList: true, subtree: true });
      }
    });
  }

  function makeTablesResizable(container) {
    var tables = container.querySelectorAll('table');
    tables.forEach(function (table) {
      if (table.hasAttribute('data-table-resize')) return;
      table.setAttribute('data-table-resize', 'enabled');
      addDragHandles(table);
    });
  }

  function addDragHandles(table) {
    var headerRow = table.querySelector('thead tr') || table.querySelector('tr');
    if (!headerRow) return;

    var cells = headerRow.querySelectorAll('th, td');
    cells.forEach(function (cell, index) {
      if (index === cells.length - 1) return; // 最后一列不需要拖拽手柄
      if (cell.querySelector('.ispace-col-resizer')) return;

      var resizer = document.createElement('div');
      resizer.className = 'ispace-col-resizer';
      resizer.style.cssText =
        'position:absolute;top:0;right:-4px;width:8px;height:100%;' +
        'cursor:col-resize;z-index:10;' +
        'background:transparent;';

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

    rows.forEach(function (row) {
      var cells = row.querySelectorAll('th, td');
      if (cells[colIndex]) {
        cellWidths.push({
          cell: cells[colIndex],
          width: cells[colIndex].getBoundingClientRect().width,
        });
      }
    });

    state = {
      table: table,
      colIndex: colIndex,
      startX: startX,
      cellWidths: cellWidths,
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e) {
    if (!state) return;

    var delta = e.clientX - state.startX;
    var newWidth = Math.max(MIN_COL_WIDTH, state.cellWidths[0].width + delta);

    state.cellWidths.forEach(function (item) {
      item.cell.style.width = newWidth + 'px';
      item.cell.style.minWidth = newWidth + 'px';
      item.cell.style.maxWidth = newWidth + 'px';
    });

    // 显示当前宽度 tooltip
    showWidthTooltip(e.clientX, e.clientY, Math.round(newWidth) + 'px');
  }

  function onMouseUp() {
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    hideWidthTooltip();
    state = null;
  }

  // Tooltip 显示当前列宽
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
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  // 导出 API
  window.TableResize = {
    init: init,
  };
})();
