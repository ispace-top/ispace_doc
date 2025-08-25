/**
 * Modern Workspace - 现代化文档管理界面交互脚本
 */

// 全局状态管理
const WorkspaceState = {
    currentView: 'recent',
    currentSort: 'modified',
    selectedProjectId: null,
    viewMode: 'grid',
    sidebarCollapsed: false,
    searchQuery: '',
    
    // 获取状态
    get(key) {
        return this[key];
    },
    
    // 设置状态
    set(key, value) {
        this[key] = value;
        this.notify(key, value);
    },
    
    // 状态变化通知
    notify(key, value) {
        document.dispatchEvent(new CustomEvent('stateChange', {
            detail: { key, value }
        }));
    }
};

// 工具函数
const Utils = {
    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    },
    
    // 格式化时间
    formatTime(timeString) {
        const time = new Date(timeString);
        const now = new Date();
        const diff = now - time;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        
        return time.toLocaleDateString('zh-CN');
    },
    
    // 获取文档类型图标
    getDocTypeIcon(status) {
        const icons = {
            1: '📄', // 普通文档
            2: '📊', // 数据文档
            3: '📋', // 列表文档
            4: '📝', // 笔记
            5: '🎯', // 任务
        };
        return icons[status] || '📄';
    },
    
    // 截取文本
    truncateText(text, length = 100) {
        if (!text) return '';
        return text.length > length ? text.substring(0, length) + '...' : text;
    },
    
    // 本地存储
    storage: {
        get(key) {
            try {
                const value = localStorage.getItem(`workspace_${key}`);
                return value ? JSON.parse(value) : null;
            } catch {
                return null;
            }
        },
        
        set(key, value) {
            try {
                localStorage.setItem(`workspace_${key}`, JSON.stringify(value));
            } catch {
                console.warn('无法保存到本地存储');
            }
        },
        
        remove(key) {
            localStorage.removeItem(`workspace_${key}`);
        }
    }
};

// 侧边栏管理
const Sidebar = {
    init() {
        this.bindEvents();
        this.loadState();
    },
    
    bindEvents() {
        // 导航项点击
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                if (view) {
                    this.switchView(view);
                }
            });
        });
        
        // 文集项点击
        document.addEventListener('click', (e) => {
            if (e.target.closest('.project-item')) {
                const projectItem = e.target.closest('.project-item');
                const projectId = projectItem.dataset.projectId;
                const projectName = projectItem.querySelector('.project-name').textContent;
                this.selectProject(projectId, projectName);
            }
        });
    },
    
    switchView(view) {
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-view="${view}"]`).classList.add('active');
        
        // 更新状态
        WorkspaceState.set('currentView', view);
        
        // 更新面包屑
        this.updateBreadcrumb(view);
        
        // 加载对应内容
        DocumentGrid.loadByView(view);
    },
    
    selectProject(projectId, projectName) {
        // 更新项目选中状态
        document.querySelectorAll('.project-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-project-id="${projectId}"]`).classList.add('active');
        
        // 更新状态
        WorkspaceState.set('selectedProjectId', projectId);
        WorkspaceState.set('currentView', 'project');
        
        // 更新面包屑
        this.updateBreadcrumb('project', projectName);
        
        // 加载项目文档
        DocumentGrid.loadByProject(projectId);
    },
    
    updateBreadcrumb(view, extra = '') {
        const breadcrumb = document.querySelector('.current-view');
        const viewNames = {
            'recent': '最近访问',
            'favorites': '收藏夹',
            'shared': '共享文档',
            'project': extra || '文集'
        };
        breadcrumb.textContent = viewNames[view] || '工作区';
    },
    
    loadState() {
        const collapsed = Utils.storage.get('sidebarCollapsed');
        if (collapsed) {
            this.toggle();
        }
    },
    
    toggle() {
        const workspace = document.querySelector('.workspace');
        workspace.classList.toggle('sidebar-collapsed');
        
        const collapsed = workspace.classList.contains('sidebar-collapsed');
        WorkspaceState.set('sidebarCollapsed', collapsed);
        Utils.storage.set('sidebarCollapsed', collapsed);
    }
};

// 工具栏管理
const Toolbar = {
    init() {
        this.bindEvents();
        this.loadState();
    },
    
    bindEvents() {
        // 侧边栏切换
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                Sidebar.toggle();
            });
        }
        
        // 视图模式切换
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchViewMode(view);
            });
        });
        
        // 排序方式改变
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                const sort = e.target.value;
                this.changeSortMode(sort);
            });
        }
        
        // 新建文档
        const createBtn = document.querySelector('.create-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.createDocument();
            });
        }
    },
    
    switchViewMode(mode) {
        // 更新按钮状态
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${mode}"]`).classList.add('active');
        
        // 更新状态
        WorkspaceState.set('viewMode', mode);
        
        // 重新渲染文档列表
        DocumentGrid.updateViewMode(mode);
        
        // 保存状态
        Utils.storage.set('viewMode', mode);
    },
    
    changeSortMode(sort) {
        WorkspaceState.set('currentSort', sort);
        DocumentGrid.resort(sort);
        Utils.storage.set('sortMode', sort);
    },
    
    createDocument() {
        const currentProject = WorkspaceState.get('selectedProjectId');
        if (currentProject) {
            window.location.href = `/create_doc/?project=${currentProject}`;
        } else {
            window.location.href = '/create_doc/';
        }
    },
    
    loadState() {
        // 加载视图模式
        const viewMode = Utils.storage.get('viewMode') || 'grid';
        this.switchViewMode(viewMode);
        
        // 加载排序模式
        const sortMode = Utils.storage.get('sortMode') || 'modified';
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.value = sortMode;
            this.changeSortMode(sortMode);
        }
    }
};

// 搜索功能
const Search = {
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        const searchInput = document.getElementById('globalSearch');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.handleSearch(e.target.value);
            }, 300));
            
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.clearSearch();
                }
            });
        }
    },
    
    handleSearch(query) {
        WorkspaceState.set('searchQuery', query);
        
        if (query.trim()) {
            this.performSearch(query);
        } else {
            this.clearSearch();
        }
    },
    
    performSearch(query) {
        // 更新面包屑
        document.querySelector('.current-view').textContent = `搜索: ${query}`;
        
        // 执行搜索
        DocumentGrid.search(query);
    },
    
    clearSearch() {
        const searchInput = document.getElementById('globalSearch');
        if (searchInput) {
            searchInput.value = '';
        }
        WorkspaceState.set('searchQuery', '');
        
        // 恢复当前视图
        const currentView = WorkspaceState.get('currentView');
        DocumentGrid.loadByView(currentView);
    }
};

// 文档网格管理
const DocumentGrid = {
    currentDocuments: [],
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        // 监听状态变化
        document.addEventListener('stateChange', (e) => {
            const { key, value } = e.detail;
            if (key === 'viewMode') {
                this.updateViewMode(value);
            }
        });
    },
    
    // 根据视图加载文档
    loadByView(view) {
        switch (view) {
            case 'recent':
                this.loadRecentDocuments();
                break;
            case 'favorites':
                this.loadFavoriteDocuments();
                break;
            case 'shared':
                this.loadSharedDocuments();
                break;
            default:
                this.loadRecentDocuments();
        }
    },
    
    // 根据项目加载文档
    loadByProject(projectId) {
        // 这里需要从服务器获取项目文档
        this.loadDocuments(`/api/projects/${projectId}/documents/`);
    },
    
    // 搜索文档
    search(query) {
        const filtered = this.currentDocuments.filter(doc => 
            doc.name.toLowerCase().includes(query.toLowerCase()) ||
            (doc.summary && doc.summary.toLowerCase().includes(query.toLowerCase()))
        );
        this.renderDocuments(filtered);
    },
    
    // 重新排序
    resort(sortMode) {
        const sorted = [...this.currentDocuments].sort((a, b) => {
            switch (sortMode) {
                case 'name':
                    return a.name.localeCompare(b.name);
                case 'created':
                    return new Date(b.create_time) - new Date(a.create_time);
                case 'modified':
                default:
                    return new Date(b.modify_time) - new Date(a.modify_time);
            }
        });
        this.renderDocuments(sorted);
    },
    
    // 更新视图模式
    updateViewMode(mode) {
        const container = document.getElementById('documentsGrid');
        if (container) {
            container.className = `documents-${mode}`;
        }
    },
    
    // 加载最近文档
    loadRecentDocuments() {
        this.loadDocuments('/api/documents/recent/');
    },
    
    // 加载收藏文档
    loadFavoriteDocuments() {
        this.loadDocuments('/api/documents/favorites/');
    },
    
    // 加载共享文档
    loadSharedDocuments() {
        this.loadDocuments('/api/documents/shared/');
    },
    
    // 通用文档加载函数
    async loadDocuments(url) {
        try {
            // 显示加载状态
            this.showLoading();
            
            // 这里应该从服务器加载数据
            // 临时使用全局数据
            const documents = window.allDocuments || [];
            this.currentDocuments = documents;
            
            // 应用当前排序
            const sortMode = WorkspaceState.get('currentSort');
            this.resort(sortMode);
            
        } catch (error) {
            console.error('加载文档失败:', error);
            this.showError();
        }
    },
    
    // 渲染文档列表
    renderDocuments(documents) {
        const container = document.getElementById('documentsGrid');
        const emptyState = document.getElementById('emptyWorkspace');
        
        if (!documents || documents.length === 0) {
            container.style.display = 'none';
            emptyState.style.display = 'flex';
            return;
        }
        
        container.style.display = 'grid';
        emptyState.style.display = 'none';
        
        const viewMode = WorkspaceState.get('viewMode');
        container.className = `documents-${viewMode}`;
        
        container.innerHTML = documents.map(doc => this.renderDocumentCard(doc)).join('');
        
        // 为新渲染的卡片绑定事件
        this.bindDocumentEvents();
    },
    
    // 渲染单个文档卡片
    renderDocumentCard(doc) {
        return `
            <div class="document-card" data-doc-id="${doc.id}" onclick="openDocument('${doc.id}')">
                <div class="doc-header">
                    <div class="doc-type">
                        ${Utils.getDocTypeIcon(doc.status)}
                    </div>
                    <div class="doc-actions">
                        <button class="action-btn" onclick="event.stopPropagation(); favoriteDocument('${doc.id}')" title="收藏">
                            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                            </svg>
                        </button>
                        <button class="action-btn" onclick="event.stopPropagation(); shareDocument('${doc.id}')" title="分享">
                            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor">
                                <path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="doc-content">
                    <h3 class="doc-title">${doc.name}</h3>
                    ${doc.summary ? `<p class="doc-summary">${Utils.truncateText(doc.summary, 120)}</p>` : ''}
                </div>
                
                <div class="doc-footer">
                    <div class="doc-meta">
                        <span class="doc-project">${doc.project_name || '未分类'}</span>
                        <span class="doc-time">${Utils.formatTime(doc.modify_time)}</span>
                    </div>
                </div>
            </div>
        `;
    },
    
    // 绑定文档卡片事件
    bindDocumentEvents() {
        // 文档卡片点击事件已在HTML中通过onclick处理
        // 这里可以添加其他需要的事件处理
    },
    
    // 显示加载状态
    showLoading() {
        const container = document.getElementById('documentsGrid');
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 60px;">
                <div style="display: inline-block; width: 24px; height: 24px; border: 2px solid #e5e7eb; border-top: 2px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <p style="margin-top: 16px; color: #6b7280;">加载中...</p>
            </div>
        `;
    },
    
    // 显示错误状态
    showError() {
        const container = document.getElementById('documentsGrid');
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 60px;">
                <p style="color: #ef4444;">加载失败，请刷新重试</p>
            </div>
        `;
    }
};

// 主题管理
const Theme = {
    init() {
        this.loadTheme();
    },
    
    toggle() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'light' ? 'dark' : 'light';
        this.setTheme(next);
    },
    
    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        Utils.storage.set('theme', theme);
    },
    
    loadTheme() {
        const saved = Utils.storage.get('theme') || 'light';
        this.setTheme(saved);
    }
};

// 全局函数（供HTML内联事件使用）
window.toggleSidebar = () => Sidebar.toggle();
window.toggleTheme = () => Theme.toggle();
window.selectProject = (id, name) => Sidebar.selectProject(id, name);

window.openDocument = (docId) => {
    window.location.href = `/doc/${docId}/`;
};

window.createDocument = () => {
    const currentProject = WorkspaceState.get('selectedProjectId');
    if (currentProject) {
        window.location.href = `/create_doc/?project=${currentProject}`;
    } else {
        window.location.href = '/create_doc/';
    }
};

window.createProject = () => {
    window.location.href = '/create_project/';
};

window.favoriteDocument = async (docId) => {
    try {
        // 发送收藏请求
        console.log('收藏文档:', docId);
        // 这里应该调用API
    } catch (error) {
        console.error('收藏失败:', error);
    }
};

window.shareDocument = async (docId) => {
    try {
        // 显示分享对话框
        console.log('分享文档:', docId);
        // 这里应该显示分享对话框
    } catch (error) {
        console.error('分享失败:', error);
    }
};

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    // 初始化各个组件
    Sidebar.init();
    Toolbar.init();
    Search.init();
    DocumentGrid.init();
    Theme.init();
    
    // 加载初始数据
    DocumentGrid.loadRecentDocuments();
});

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);