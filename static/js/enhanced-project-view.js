/*
 * 增强型文集展示界面 - 交互控制
 * 提供视图切换、搜索过滤、快速访问等功能
 */

class EnhancedProjectView {
  constructor() {
    this.currentView = localStorage.getItem('project-view') || 'list';
    this.searchTimeout = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.loadView();
    this.setupSearch();
    this.setupQuickAccess();
  }

  bindEvents() {
    // 视图切换
    document.addEventListener('click', (e) => {
      if (e.target.matches('.view-switcher__option')) {
        this.switchView(e.target.dataset.view);
      }
    });

    // 快速访问标签切换
    document.addEventListener('click', (e) => {
      if (e.target.matches('.quick-access__tab')) {
        this.switchQuickAccessTab(e.target);
      }
    });

    // 项目卡片/列表项点击
    document.addEventListener('click', (e) => {
      const projectItem = e.target.closest('.project-grid__card, .project-compact__item, .quick-access__item');
      if (projectItem && !e.target.closest('.project-grid__card-action, .project-compact__item-actions')) {
        this.openProject(projectItem.dataset.projectId);
      }
    });

    // 项目操作按钮
    document.addEventListener('click', (e) => {
      if (e.target.matches('.project-action')) {
        e.preventDefault();
        e.stopPropagation();
        this.handleProjectAction(e.target.dataset.action, e.target.dataset.projectId);
      }
    });

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
      this.handleKeyboard(e);
    });
  }

  switchView(viewType) {
    this.currentView = viewType;
    localStorage.setItem('project-view', viewType);
    
    // 更新按钮状态
    document.querySelectorAll('.view-switcher__option').forEach(btn => {
      btn.classList.toggle('view-switcher__option--active', btn.dataset.view === viewType);
    });

    // 切换视图
    this.loadView();
    
    // 添加切换动画
    this.animateViewSwitch();
  }

  loadView() {
    const container = document.querySelector('.project-container');
    if (!container) return;

    container.className = `project-container project-container--${this.currentView}`;
    
    // 根据视图类型加载不同的布局
    this.renderProjectsInView(this.currentView);
  }

  renderProjectsInView(viewType) {
    const projects = this.getProjectData();
    const container = document.querySelector('.project-list-content');
    
    if (!container || !projects) return;

    switch (viewType) {
      case 'grid':
        container.innerHTML = this.renderGridView(projects);
        break;
      case 'compact':
        container.innerHTML = this.renderCompactView(projects);
        break;
      default:
        // 保持原有的列表视图
        break;
    }
  }

  renderGridView(projects) {
    return `
      <div class="project-grid">
        ${projects.map(project => `
          <a href="/project/${project.id}/" class="project-grid__card" data-project-id="${project.id}">
            <div class="project-grid__card-header">
              <div class="project-grid__card-icon">
                ${this.getProjectIcon(project)}
              </div>
              <div class="project-grid__card-actions">
                <button class="project-grid__card-action project-action" data-action="edit" data-project-id="${project.id}" title="编辑">
                  ✏️
                </button>
                <button class="project-grid__card-action project-action" data-action="share" data-project-id="${project.id}" title="分享">
                  🔗
                </button>
                <button class="project-grid__card-action project-action" data-action="star" data-project-id="${project.id}" title="收藏">
                  ⭐
                </button>
              </div>
            </div>
            <h3 class="project-grid__card-title">${project.name}</h3>
            <p class="project-grid__card-desc">${project.description || '暂无描述'}</p>
            <div class="project-grid__card-stats">
              <span class="project-grid__card-stat">
                <span>📄</span>
                <span>${project.doc_count || 0} 篇文档</span>
              </span>
              <span class="project-grid__card-stat">
                <span>👁️</span>
                <span>${project.view_count || 0} 次查看</span>
              </span>
            </div>
            <div class="project-grid__card-footer">
              <div class="project-grid__card-tags">
                <span class="project-grid__card-tag">${this.getProjectRoleText(project.role)}</span>
                ${project.category ? `<span class="project-grid__card-tag">${project.category}</span>` : ''}
              </div>
              <span class="project-grid__card-time">${this.formatTime(project.modify_time)}</span>
            </div>
          </a>
        `).join('')}
      </div>
    `;
  }

  renderCompactView(projects) {
    return `
      <div class="project-compact">
        <div class="project-compact__header">
          <span>文集列表</span>
          <span class="project-compact__count">${projects.length} 个文集</span>
        </div>
        <ul class="project-compact__list">
          ${projects.map(project => `
            <li>
              <a href="/project/${project.id}/" class="project-compact__item" data-project-id="${project.id}">
                <div class="project-compact__item-icon">
                  ${this.getProjectIcon(project)}
                </div>
                <div class="project-compact__item-content">
                  <h4 class="project-compact__item-title">${project.name}</h4>
                  <div class="project-compact__item-meta">
                    <span>📄 ${project.doc_count || 0} 篇</span>
                    <span>👁️ ${project.view_count || 0} 次</span>
                    <span>🕒 ${this.formatTime(project.modify_time)}</span>
                    <span class="tag tag-${this.getProjectRoleClass(project.role)}">${this.getProjectRoleText(project.role)}</span>
                  </div>
                </div>
                <div class="project-compact__item-actions">
                  <button class="btn btn-sm btn-ghost project-action" data-action="edit" data-project-id="${project.id}">编辑</button>
                  <button class="btn btn-sm btn-ghost project-action" data-action="share" data-project-id="${project.id}">分享</button>
                </div>
              </a>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
  }

  setupSearch() {
    const searchInput = document.querySelector('.enhanced-search__input');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.performSearch(e.target.value);
      }, 300);
    });

    // 搜索建议
    this.setupSearchSuggestions(searchInput);
  }

  setupSearchSuggestions(input) {
    // 创建搜索建议容器
    const suggestionsContainer = document.createElement('div');
    suggestionsContainer.className = 'search-suggestions';
    input.parentNode.appendChild(suggestionsContainer);

    input.addEventListener('focus', () => {
      this.showSearchSuggestions(suggestionsContainer);
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.enhanced-search__input-group')) {
        suggestionsContainer.style.display = 'none';
      }
    });
  }

  showSearchSuggestions(container) {
    const recentSearches = JSON.parse(localStorage.getItem('recent-searches') || '[]');
    const suggestions = [
      '最近更新的文档',
      '我的收藏',
      '团队协作项目',
      ...recentSearches.slice(0, 3)
    ].filter(Boolean);

    container.innerHTML = `
      <div class="search-suggestions__content">
        <div class="search-suggestions__section">
          <h4 class="search-suggestions__title">快速搜索</h4>
          ${suggestions.map(suggestion => `
            <button class="search-suggestions__item" data-search="${suggestion}">
              <span class="search-suggestions__icon">🔍</span>
              <span>${suggestion}</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;
    container.style.display = 'block';

    // 绑定建议点击事件
    container.addEventListener('click', (e) => {
      if (e.target.closest('.search-suggestions__item')) {
        const searchTerm = e.target.closest('.search-suggestions__item').dataset.search;
        document.querySelector('.enhanced-search__input').value = searchTerm;
        this.performSearch(searchTerm);
        container.style.display = 'none';
      }
    });
  }

  performSearch(query) {
    if (!query.trim()) {
      this.showAllProjects();
      return;
    }

    // 保存搜索历史
    this.saveSearchHistory(query);

    // 执行搜索
    const results = this.searchProjects(query);
    this.displaySearchResults(results, query);
  }

  searchProjects(query) {
    const projects = this.getProjectData();
    const searchTerms = query.toLowerCase().split(/\\s+/);
    
    return projects.filter(project => {
      const searchText = [
        project.name,
        project.description || '',
        project.create_user || ''
      ].join(' ').toLowerCase();

      return searchTerms.every(term => searchText.includes(term));
    });
  }

  displaySearchResults(results, query) {
    const container = document.querySelector('.project-list-content');
    if (!container) return;

    if (results.length === 0) {
      container.innerHTML = this.renderEmptyState(query);
      return;
    }

    // 根据当前视图模式渲染结果
    this.renderProjectsInView(this.currentView);
    
    // 高亮搜索结果
    this.highlightSearchResults(query);
  }

  renderEmptyState(query) {
    return `
      <div class="project-list__empty">
        <div class="project-list__empty-icon">🔍</div>
        <h3 class="project-list__empty-title">未找到相关文集</h3>
        <p class="project-list__empty-description">
          没有找到包含"${query}"的文集，请尝试其他关键词或<a href="#" class="link">浏览所有文集</a>
        </p>
      </div>
    `;
  }

  setupQuickAccess() {
    this.loadQuickAccessData();
  }

  switchQuickAccessTab(tab) {
    // 更新标签状态
    document.querySelectorAll('.quick-access__tab').forEach(t => {
      t.classList.remove('quick-access__tab--active');
    });
    tab.classList.add('quick-access__tab--active');

    // 切换内容
    this.loadQuickAccessContent(tab.dataset.tab);
  }

  loadQuickAccessContent(tabType) {
    const container = document.querySelector('.quick-access__content');
    if (!container) return;

    const content = this.getQuickAccessData(tabType);
    container.innerHTML = this.renderQuickAccessItems(content);
  }

  getQuickAccessData(type) {
    const projects = this.getProjectData();
    
    switch (type) {
      case 'recent':
        return projects.slice(0, 6);
      case 'starred':
        return projects.filter(p => p.is_starred).slice(0, 6);
      case 'collaborative':
        return projects.filter(p => p.role === 99).slice(0, 6);
      default:
        return projects.slice(0, 6);
    }
  }

  renderQuickAccessItems(items) {
    return items.map(item => `
      <a href="/project/${item.id}/" class="quick-access__item" data-project-id="${item.id}">
        <div class="quick-access__item-icon">
          ${this.getProjectIcon(item)}
        </div>
        <div class="quick-access__item-content">
          <h4 class="quick-access__item-title">${item.name}</h4>
          <p class="quick-access__item-desc">${item.doc_count || 0} 篇文档 • ${this.formatTime(item.modify_time)}</p>
        </div>
      </a>
    `).join('');
  }

  // 工具方法
  getProjectData() {
    // 从页面中获取项目数据，或从API获取
    const projectElements = document.querySelectorAll('.project-list__item');
    return Array.from(projectElements).map(el => ({
      id: el.dataset.projectId || Math.random().toString(36),
      name: el.querySelector('.project-list__item-title')?.textContent?.trim() || '未命名项目',
      description: el.querySelector('.project-list__item-description')?.textContent?.trim() || '',
      role: parseInt(el.dataset.role) || 0,
      doc_count: parseInt(el.dataset.docCount) || 0,
      view_count: parseInt(el.dataset.viewCount) || 0,
      modify_time: el.dataset.modifyTime || new Date().toISOString(),
      create_user: el.dataset.createUser || '',
      is_starred: el.classList.contains('project-list__item--starred')
    }));
  }

  getProjectIcon(project) {
    const icons = ['📚', '📖', '📝', '📋', '📊', '🔖', '📑', '📄'];
    return icons[project.id % icons.length] || '📚';
  }

  getProjectRoleText(role) {
    const roleMap = {
      0: '公开',
      1: '私密',
      3: '密码',
      99: '协作'
    };
    return roleMap[role] || '公开';
  }

  getProjectRoleClass(role) {
    const classMap = {
      0: 'success',
      1: 'error',
      3: 'warning',
      99: 'primary'
    };
    return classMap[role] || 'success';
  }

  formatTime(timeString) {
    if (!timeString) return '刚刚';
    
    const time = new Date(timeString);
    const now = new Date();
    const diff = now - time;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (days > 0) return `${days}天前`;
    if (hours > 0) return `${hours}小时前`;
    if (minutes > 0) return `${minutes}分钟前`;
    return '刚刚';
  }

  saveSearchHistory(query) {
    const history = JSON.parse(localStorage.getItem('recent-searches') || '[]');
    const filteredHistory = history.filter(item => item !== query);
    const newHistory = [query, ...filteredHistory].slice(0, 10);
    localStorage.setItem('recent-searches', JSON.stringify(newHistory));
  }

  handleProjectAction(action, projectId) {
    switch (action) {
      case 'edit':
        window.location.href = `/manage/project/${projectId}/edit/`;
        break;
      case 'share':
        this.shareProject(projectId);
        break;
      case 'star':
        this.toggleStar(projectId);
        break;
      case 'delete':
        this.deleteProject(projectId);
        break;
    }
  }

  shareProject(projectId) {
    const url = `${window.location.origin}/project/${projectId}/`;
    if (navigator.share) {
      navigator.share({
        title: '分享文集',
        url: url
      });
    } else {
      navigator.clipboard.writeText(url).then(() => {
        this.showToast('链接已复制到剪贴板');
      });
    }
  }

  toggleStar(projectId) {
    // 实现收藏/取消收藏功能
    fetch(`/api/project/${projectId}/star/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        'Content-Type': 'application/json'
      }
    }).then(response => response.json())
      .then(data => {
        if (data.success) {
          this.updateStarStatus(projectId, data.is_starred);
          this.showToast(data.is_starred ? '已收藏' : '已取消收藏');
        }
      });
  }

  updateStarStatus(projectId, isStarred) {
    const elements = document.querySelectorAll(`[data-project-id="${projectId}"]`);
    elements.forEach(el => {
      el.classList.toggle('project-list__item--starred', isStarred);
    });
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('toast--show');
    }, 100);
    
    setTimeout(() => {
      toast.classList.remove('toast--show');
      setTimeout(() => {
        document.body.removeChild(toast);
      }, 300);
    }, 3000);
  }

  handleKeyboard(e) {
    // 快捷键处理
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'k':
          e.preventDefault();
          document.querySelector('.enhanced-search__input')?.focus();
          break;
        case '1':
          e.preventDefault();
          this.switchView('list');
          break;
        case '2':
          e.preventDefault();
          this.switchView('grid');
          break;
        case '3':
          e.preventDefault();
          this.switchView('compact');
          break;
      }
    }
  }

  animateViewSwitch() {
    const container = document.querySelector('.project-list-content');
    if (!container) return;

    container.style.opacity = '0';
    container.style.transform = 'translateY(10px)';
    
    setTimeout(() => {
      container.style.transition = 'all 0.3s ease';
      container.style.opacity = '1';
      container.style.transform = 'translateY(0)';
    }, 50);
  }

  showAllProjects() {
    this.loadView();
    document.querySelector('.enhanced-search__input').value = '';
  }

  loadQuickAccessData() {
    // 初始化快速访问面板
    this.loadQuickAccessContent('recent');
  }

  openProject(projectId) {
    if (projectId) {
      window.location.href = `/project/${projectId}/`;
    }
  }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  new EnhancedProjectView();
});

// 搜索建议样式
const searchSuggestionsCSS = `
.search-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-secondary);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 1000;
  display: none;
}

.search-suggestions__content {
  padding: var(--space-3);
}

.search-suggestions__title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-tertiary);
  margin: 0 0 var(--space-2) 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.search-suggestions__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  text-align: left;
  transition: all 0.2s ease;
}

.search-suggestions__item:hover {
  background: var(--bg-hover);
}

.search-suggestions__icon {
  opacity: 0.6;
}

.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: var(--bg-primary);
  color: var(--text-primary);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
  z-index: 2000;
  opacity: 0;
  transform: translateY(-10px);
  transition: all 0.3s ease;
}

.toast--show {
  opacity: 1;
  transform: translateY(0);
}
`;

// 注入样式
const style = document.createElement('style');
style.textContent = searchSuggestionsCSS;
document.head.appendChild(style);