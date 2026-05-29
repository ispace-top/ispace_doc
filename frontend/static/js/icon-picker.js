/**
 * iSpaceDoc 图标选择器组件
 * 用于 Vditor 编辑器工具栏，支持搜索、分类筛选、分页、自定义上传
 */
(function() {
    'use strict';

    // 注入图标选择器样式
    var styleEl = document.createElement('style');
    styleEl.textContent = '.icon-picker-toolbar{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid #f1f5f9;flex-wrap:wrap;}.icon-picker-search{display:flex;align-items:center;gap:6px;}.icon-picker-category select{height:34px;}.icon-picker-upload{margin-left:auto;}.icon-picker-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;padding:12px;max-height:320px;overflow-y:auto;min-height:200px;}.icon-picker-item{cursor:pointer;border:1px solid #f1f5f9;border-radius:8px;padding:10px 4px;text-align:center;transition:all .15s;display:flex;flex-direction:column;align-items:center;gap:6px;}.icon-picker-item:hover{border-color:#6366f1;background:#eef2ff;}.icon-picker-item-preview{width:28px;height:28px;display:flex;align-items:center;justify-content:center;overflow:hidden;}.icon-picker-item-preview svg{max-width:28px;max-height:28px;width:auto;height:auto;}.icon-picker-item-name{font-size:10px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:80px;}.icon-picker-loading,.icon-picker-empty{display:flex;align-items:center;justify-content:center;height:200px;color:#94a3b8;font-size:14px;}.icon-picker-pagination{display:flex;align-items:center;justify-content:center;gap:10px;padding:8px 0;}.icon-page-info{font-size:13px;color:#64748b;}.icon-picker-status{text-align:center;font-size:12px;color:#94a3b8;padding-bottom:8px;}';
    document.head.appendChild(styleEl);

    var ICON_SEARCH_URL = '/api/icons/search/';
    var ICON_CATEGORIES_URL = '/api/icons/categories/';
    var ICON_UPLOAD_URL = '/api/icons/upload/';

    var currentPage = 1;
    var currentQuery = '';
    var currentCategory = '';
    var pageSize = 48;
    var selectedCallback = null;

    /**
     * 打开图标选择器
     * @param {Function} onSelect - 选中图标时的回调，接收 SVG 字符串
     */
    function openIconPicker(onSelect) {
        selectedCallback = onSelect;
        currentPage = 1;
        currentQuery = '';
        currentCategory = '';

        if (typeof layer === 'undefined') {
            console.warn('IconPicker: layer 未加载');
            return;
        }

        layer.open({
            type: 1,
            title: '选择图标',
            area: ['720px', '520px'],
            content: buildPickerHTML(),
            success: function(layero) {
                bindEvents(layero);
                loadCategories();
                loadIcons();
            }
        });
    }

    function buildPickerHTML() {
        return '<div id="icon-picker-container">' +
            '<div class="icon-picker-toolbar">' +
                '<div class="icon-picker-search">' +
                    '<input type="text" id="icon-search-input" class="layui-input" placeholder="搜索图标..." style="width:200px;height:34px;">' +
                    '<button type="button" id="icon-search-btn" class="layui-btn layui-btn-sm layui-btn-normal">搜索</button>' +
                '</div>' +
                '<div class="icon-picker-category">' +
                    '<select id="icon-category-select" class="layui-input" style="width:140px;height:34px;"><option value="">全部分类</option></select>' +
                '</div>' +
                '<div class="icon-picker-upload">' +
                    '<button type="button" id="icon-upload-btn" class="layui-btn layui-btn-sm">上传自定义图标</button>' +
                    '<input type="file" id="icon-upload-input" accept=".svg" style="display:none;">' +
                '</div>' +
            '</div>' +
            '<div class="icon-picker-grid" id="icon-picker-grid">' +
                '<div class="icon-picker-loading">加载中...</div>' +
            '</div>' +
            '<div class="icon-picker-pagination" id="icon-picker-pagination"></div>' +
            '<div class="icon-picker-status" id="icon-picker-status"></div>' +
        '</div>';
    }

    function bindEvents(layero) {
        var searchInput = layero.find('#icon-search-input')[0];
        var searchBtn = layero.find('#icon-search-btn')[0];
        var categorySelect = layero.find('#icon-category-select')[0];
        var uploadBtn = layero.find('#icon-upload-btn')[0];
        var uploadInput = layero.find('#icon-upload-input')[0];
        var grid = layero.find('#icon-picker-grid')[0];

        searchBtn.addEventListener('click', function() {
            currentQuery = searchInput.value.trim();
            currentPage = 1;
            loadIcons();
        });

        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                currentQuery = searchInput.value.trim();
                currentPage = 1;
                loadIcons();
            }
        });

        categorySelect.addEventListener('change', function() {
            currentCategory = this.value;
            currentPage = 1;
            loadIcons();
        });

        uploadBtn.addEventListener('click', function() {
            uploadInput.click();
        });

        uploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                uploadCustomIcon(this.files[0]);
            }
        });

        grid.addEventListener('click', function(e) {
            var iconItem = e.target.closest('.icon-picker-item');
            if (!iconItem) return;

            var svg = iconItem.getAttribute('data-svg');
            if (svg && selectedCallback) {
                selectedCallback(svg);
                layer.closeAll();
            }
        });
    }

    function loadCategories() {
        fetch(ICON_CATEGORIES_URL)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var select = document.getElementById('icon-category-select');
                if (!select) return;
                var categories = data.categories || [];
                categories.forEach(function(cat) {
                    var opt = document.createElement('option');
                    opt.value = cat.name;
                    opt.textContent = cat.label || cat.name;
                    select.appendChild(opt);
                });
            })
            .catch(function() {});
    }

    function loadIcons() {
        var grid = document.getElementById('icon-picker-grid');
        var pagination = document.getElementById('icon-picker-pagination');
        var status = document.getElementById('icon-picker-status');
        if (!grid) return;

        grid.innerHTML = '<div class="icon-picker-loading">加载中...</div>';

        var params = new URLSearchParams();
        if (currentQuery) params.set('q', currentQuery);
        if (currentCategory) params.set('category', currentCategory);
        params.set('page', currentPage);
        params.set('page_size', pageSize);

        var url = ICON_SEARCH_URL + '?' + params.toString();

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var icons = data.icons || data.data || [];
                var total = data.total || icons.length;
                var totalPages = data.total_pages || Math.ceil(total / pageSize) || 1;

                if (icons.length === 0) {
                    grid.innerHTML = '<div class="icon-picker-empty">没有找到图标</div>';
                    pagination.innerHTML = '';
                    if (status) status.textContent = '';
                    return;
                }

                var html = '';
                icons.forEach(function(icon) {
                    var svg = icon.svg || '';
                    var name = icon.name || icon.id || '';
                    html += '<div class="icon-picker-item" data-svg="' + escapeHTML(svg) + '" title="' + escapeHTML(name) + '">' +
                        '<div class="icon-picker-item-preview">' + svg + '</div>' +
                        '<div class="icon-picker-item-name">' + escapeHTML(name) + '</div>' +
                    '</div>';
                });
                grid.innerHTML = html;

                // 分页
                var pagHTML = '';
                if (totalPages > 1) {
                    pagHTML += '<button class="layui-btn layui-btn-xs ' + (currentPage <= 1 ? 'layui-btn-disabled' : '') + '" ' + (currentPage <= 1 ? 'disabled' : '') + ' id="icon-page-prev">上一页</button>';
                    pagHTML += '<span class="icon-page-info">' + currentPage + ' / ' + totalPages + '</span>';
                    pagHTML += '<button class="layui-btn layui-btn-xs ' + (currentPage >= totalPages ? 'layui-btn-disabled' : '') + '" ' + (currentPage >= totalPages ? 'disabled' : '') + ' id="icon-page-next">下一页</button>';
                }
                pagination.innerHTML = pagHTML;
                if (status) status.textContent = '共 ' + total + ' 个图标';

                // 绑定分页事件
                var prevBtn = document.getElementById('icon-page-prev');
                var nextBtn = document.getElementById('icon-page-next');
                if (prevBtn) prevBtn.addEventListener('click', function() { if (currentPage > 1) { currentPage--; loadIcons(); } });
                if (nextBtn) nextBtn.addEventListener('click', function() { if (currentPage < totalPages) { currentPage++; loadIcons(); } });
            })
            .catch(function(err) {
                grid.innerHTML = '<div class="icon-picker-empty">加载失败: ' + err.message + '</div>';
            });
    }

    function uploadCustomIcon(file) {
        var formData = new FormData();
        formData.append('file', file);
        formData.append('name', file.name.replace(/\.svg$/i, ''));

        fetch(ICON_UPLOAD_URL, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.id && data.svg) {
                    if (selectedCallback) {
                        selectedCallback(data.svg);
                        layer.closeAll();
                    }
                } else if (data.error) {
                    if (typeof layer !== 'undefined') layer.msg(data.error, {icon: 2});
                }
            })
            .catch(function(err) {
                if (typeof layer !== 'undefined') layer.msg('上传失败: ' + err.message, {icon: 2});
            });

        var uploadInput = document.getElementById('icon-upload-input');
        if (uploadInput) uploadInput.value = '';
    }

    function getCSRFToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        var cookie = document.cookie.split('; ').find(function(row) { return row.startsWith('csrftoken='); });
        if (cookie) return cookie.split('=')[1];
        return '';
    }

    function escapeHTML(str) {
        var div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // 暴露到全局
    window.IconPicker = {
        open: openIconPicker
    };
})();
