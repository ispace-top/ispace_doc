/**
 * iSpaceDoc 附件预览组件
 * 拦截文档正文中的附件链接，根据文件类型提供对应的预览方式
 */
(function() {
    'use strict';

    // 注入样式
    var styleEl = document.createElement('style');
    styleEl.textContent = '.attach-preview-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.45);z-index:9999;display:flex;align-items:center;justify-content:center;}.attach-preview-dialog{background:#fff;border-radius:12px;width:90%;max-width:960px;max-height:85vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.15);}.attach-preview-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #f1f5f9;}.attach-preview-title{font-size:15px;font-weight:600;color:#1e293b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:80%;}.attach-preview-close{width:32px;height:32px;border:none;background:none;cursor:pointer;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:20px;transition:all .15s;}.attach-preview-close:hover{background:#f1f5f9;color:#475569;}.attach-preview-body{flex:1;overflow:auto;padding:0;min-height:300px;display:flex;align-items:center;justify-content:center;}.attach-preview-body iframe,.attach-preview-body video{width:100%;height:65vh;border:none;}.attach-preview-body pre{padding:20px;margin:0;font-size:13px;line-height:1.6;overflow:auto; max-height:65vh;width:100%;background:#1e293b;color:#e2e8f0;white-space:pre-wrap;word-break:break-all;}.attach-preview-body table{border-collapse:collapse;font-size:13px;width:100%;}.attach-preview-body table td,.attach-preview-body table th{border:1px solid #e2e8f0;padding:6px 10px;text-align:left;}.attach-preview-body table th{background:#f8fafc;font-weight:600;}.attach-preview-unzip-tree{width:100%;padding:16px;overflow:auto;max-height:65vh;}.attach-preview-unzip-tree .tree-entry{display:flex;align-items:center;padding:4px 8px;font-size:13px;gap:6px;border-radius:4px;}.attach-preview-unzip-tree .tree-entry.is-dir{color:#6366f1;font-weight:500;}.attach-preview-unzip-tree .tree-entry .size{color:#94a3b8;margin-left:auto;font-size:12px;}.attach-preview-html-body{padding:20px;overflow:auto;max-height:65vh;width:100%;line-height:1.8;}.attach-preview-slide-list{width:100%;padding:16px;overflow:auto;max-height:65vh;}.attach-preview-slide-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin-bottom:8px;}.attach-preview-slide-card .slide-num{font-size:12px;color:#94a3b8;}.attach-preview-slide-card .slide-title{font-size:14px;font-weight:600;color:#1e293b;margin-top:2px;}.attach-preview-slide-card .slide-text{font-size:12px;color:#64748b;margin-top:4px;white-space:pre-wrap;}.attach-preview-footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:12px 20px;border-top:1px solid #f1f5f9;font-size:13px;color:#94a3b8;}.attach-preview-footer .attach-dl-btn{display:inline-flex;align-items:center;gap:4px;padding:6px 14px;border:1px solid #e2e8f0;border-radius:6px;color:#475569;text-decoration:none;font-size:13px;transition:all .15s;}.attach-preview-footer .attach-dl-btn:hover{background:#f8fafc;border-color:#6366f1;color:#6366f1;}.attach-preview-loading{display:flex;align-items:center;justify-content:center;height:200px;color:#94a3b8;font-size:14px;}.attach-preview-error{padding:40px;text-align:center;color:#ef4444;font-size:14px;}';
    document.head.appendChild(styleEl);

    var EXT_PREVIEW_MAP = {
        '.pdf': 'pdf',
        '.mp4': 'video',
        '.webm': 'video',
        '.ogg': 'video',
        '.docx': 'docx',
        '.xlsx': 'xlsx',
        '.xls': 'xlsx',
        '.pptx': 'pptx',
        '.txt': 'text',
        '.md': 'text',
        '.markdown': 'text',
        '.py': 'code',
        '.js': 'code',
        '.ts': 'code',
        '.html': 'code',
        '.css': 'code',
        '.json': 'code',
        '.xml': 'code',
        '.yaml': 'code',
        '.yml': 'code',
        '.csv': 'text',
        '.log': 'text',
        '.ini': 'text',
        '.cfg': 'text',
        '.conf': 'text',
        '.java': 'code',
        '.c': 'code',
        '.cpp': 'code',
        '.h': 'code',
        '.go': 'code',
        '.rs': 'code',
        '.rb': 'code',
        '.php': 'code',
        '.sh': 'code',
        '.sql': 'code',
        '.zip': 'zip',
        '.rar': 'unsupported',
        '.7z': 'unsupported',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.gif': 'image',
        '.svg': 'image',
        '.webp': 'image',
    };

    function getPreviewType(href) {
        var url = href.split('?')[0].toLowerCase();
        for (var ext in EXT_PREVIEW_MAP) {
            if (EXT_PREVIEW_MAP.hasOwnProperty(ext) && url.endsWith(ext)) {
                return EXT_PREVIEW_MAP[ext];
            }
        }
        return 'unsupported';
    }

    function getFileName(href) {
        var url = href.split('?')[0];
        var parts = url.split('/');
        return decodeURIComponent(parts[parts.length - 1] || 'file');
    }

    function openPreview(href) {
        var fileName = getFileName(href);
        var previewType = getPreviewType(href);

        var overlay = document.createElement('div');
        overlay.className = 'attach-preview-overlay';
        overlay.innerHTML =
            '<div class="attach-preview-dialog">' +
            '<div class="attach-preview-header">' +
                '<span class="attach-preview-title">' + escapeHTML(fileName) + '</span>' +
                '<button class="attach-preview-close" title="关闭">&times;</button>' +
            '</div>' +
            '<div class="attach-preview-body" id="previewBody"></div>' +
            '<div class="attach-preview-footer">' +
                '<a class="attach-dl-btn" href="' + href + '" download>' +
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
                    '下载文件' +
                '</a>' +
            '</div>' +
            '</div>';

        document.body.appendChild(overlay);

        // 关闭事件
        var closeBtn = overlay.querySelector('.attach-preview-close');
        closeBtn.addEventListener('click', function() { document.body.removeChild(overlay); });
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) document.body.removeChild(overlay);
        });
        document.addEventListener('keydown', function escHandler(e) {
            if (e.key === 'Escape') {
                document.body.removeChild(overlay);
                document.removeEventListener('keydown', escHandler);
            }
        });

        var body = overlay.querySelector('#previewBody');
        renderPreview(body, previewType, href);

        return false;
    }

    function renderPreview(container, previewType, href) {
        container.innerHTML = '<div class="attach-preview-loading">加载预览...</div>';

        switch (previewType) {
            case 'pdf':
                container.innerHTML = '<iframe src="' + href + '#toolbar=0&navpanes=0" frameborder="0"></iframe>';
                break;
            case 'video':
                container.innerHTML = '<video controls autoplay><source src="' + href + '">您的浏览器不支持视频播放</video>';
                break;
            case 'image':
                container.innerHTML = '<div style="padding:20px;display:flex;align-items:center;justify-content:center;"><img src="' + href + '" style="max-width:100%;max-height:65vh;object-fit:contain;"></div>';
                break;
            case 'code':
            case 'text':
                fetch(href)
                    .then(function(r) { return r.text(); })
                    .then(function(text) {
                        container.innerHTML = '<pre>' + escapeHTML(text) + '</pre>';
                    })
                    .catch(function() {
                        container.innerHTML = '<div class="attach-preview-error">文件加载失败，请下载后查看</div>';
                    });
                break;
            case 'docx':
            case 'xlsx':
            case 'pptx':
            case 'zip':
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#64748b;">' +
                    '<p style="font-size:16px;margin-bottom:8px;">此文件类型需要在服务端转换后预览</p>' +
                    '<p style="font-size:13px;color:#94a3b8;">请点击下方"下载文件"按钮下载到本地查看</p>' +
                    '</div>';
                break;
            default:
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#94a3b8;">' +
                    '<p style="font-size:14px;">不支持预览此文件类型</p>' +
                    '<p style="font-size:13px;">请点击下方"下载文件"按钮下载查看</p>' +
                    '</div>';
        }
    }

    function escapeHTML(str) {
        var div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    /**
     * 初始化附件预览：绑定文档内容区域中的附件链接点击事件
     * @param {HTMLElement} container - 包含附件链接的容器元素
     */
    function initAttachmentPreview(container) {
        if (!container) return;
        container.addEventListener('click', function(e) {
            var link = e.target.closest('a');
            if (!link) return;
            var href = link.getAttribute('href') || '';
            if (!href) return;
            // 匹配附件路径模式：/media/attachment/... 或包含 attachment 的路径
            if (href.indexOf('/media/') !== -1 || href.indexOf('/attachment') !== -1) {
                e.preventDefault();
                e.stopPropagation();
                openPreview(href);
            }
        });
    }

    // 暴露到全局
    window.AttachmentPreview = {
        open: openPreview,
        init: initAttachmentPreview
    };
})();
