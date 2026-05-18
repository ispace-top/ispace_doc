/*
 * 左右两栏文集文档视图 - 交互控制
 * 左侧文集列表，右侧文档列表
 */

class DualPaneProjectView {
  constructor() {
    this.currentView = localStorage.getItem('project-view') || 'list';
    this.selectedProjectId = null;
    this.selectedProjectName = '';
    this.init();
  }

  init() {
    this.bindEvents();
    this.loadView();
  }

  bindEvents() {
    // 视图切换
    document.addEventListener('click', (e) => {
      if (e.target.matches('.view-switcher__option')) {
        this.switchView(e.target.dataset.view);
      }
    });

    // 文集项点击 - 用于选择文集并显示文档
    document.addEventListener('click', (e) => {
      const projectItem = e.target.closest('.project-list__item');
      if (projectItem && !e.target.closest('.project-list__item-action, .project-list__item-actions')) {
        e.preventDefault(); // 阻止跳转到文集页面
        this.selectProject(projectItem);
      }
    });

    // 网格/紧凑视图点击
    document.addEventListener('click', (e) => {
      const gridItem = e.target.closest('.project-grid__card, .project-compact__item');
      if (gridItem && !e.target.closest('.project-grid__card-action, .project-compact__item-actions')) {
        e.preventDefault();
        const projectId = gridItem.dataset.projectId;
        const projectName = gridItem.querySelector('.project-grid__card-title, .project-compact__item-title')?.textContent?.trim();
        this.selectProjectById(projectId, projectName);
      }
    });

    // 文档项点击
    document.addEventListener('click', (e) => {
      const docItem = e.target.closest('.document-item');
      if (docItem && !e.target.closest('.document-item__action')) {
        const docId = docItem.dataset.docId;
        if (docId) {
          window.open(`/doc/${docId}/`, '_blank');
        }
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

    // 文档面板按钮
    document.addEventListener('click', (e) => {
      if (e.target.matches('#refresh-docs')) {
        this.loadProjectDocuments(this.selectedProjectId, this.selectedProjectName);
      }
      if (e.target.matches('#new-doc')) {
        window.open(`/project/${this.selectedProjectId}/create_doc/`, '_blank');
      }
    });

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
      this.handleKeyboard(e);
    });
  }

  selectProject(projectElement) {
    const projectId = projectElement.dataset.projectId;
    const projectName = projectElement.querySelector('.project-list__item-title span:last-child')?.textContent?.trim();
    
    // 更新选中状态
    document.querySelectorAll('.project-list__item').forEach(item => {
      item.classList.remove('project-list__item--selected');
    });
    projectElement.classList.add('project-list__item--selected');
    
    // 加载文档
    this.selectedProjectId = projectId;
    this.selectedProjectName = projectName || '未命名文集';
    this.loadProjectDocuments(projectId, this.selectedProjectName);
  }

  selectProjectById(projectId, projectName) {
    // 通过ID选择项目（用于网格/紧凑视图）
    const projectElement = document.querySelector(`[data-project-id="${projectId}"]`);
    if (projectElement && projectElement.classList.contains('project-list__item')) {
      this.selectProject(projectElement);
    } else {
      // 直接设置选中项目
      this.selectedProjectId = projectId;
      this.selectedProjectName = projectName || '未命名文集';
      this.loadProjectDocuments(projectId, this.selectedProjectName);
    }
  }

  async loadProjectDocuments(projectId, projectName) {
    if (!projectId) return;

    // 更新面板标题
    const titleElement = document.getElementById('selected-project-name');
    if (titleElement) {
      titleElement.textContent = projectName;
    }

    // 显示操作按钮
    document.getElementById('refresh-docs')?.setAttribute('style', 'display: flex;');
    document.getElementById('new-doc')?.setAttribute('style', 'display: flex;');

    // 隐藏空状态，显示加载状态
    const emptyState = document.querySelector('.document-panel__empty');
    const documentList = document.getElementById('document-list');
    
    if (emptyState) emptyState.style.display = 'none';
    if (documentList) {
      documentList.style.display = 'block';
      documentList.innerHTML = this.renderLoadingState();
    }

    try {
      // 获取文档数据
      const documents = await this.fetchProjectDocuments(projectId);
      
      if (documentList) {
        if (documents && documents.length > 0) {
          documentList.innerHTML = this.renderDocumentList(documents);
        } else {
          documentList.innerHTML = this.renderEmptyDocuments(projectName);
        }
      }
    } catch (error) {
      console.error('加载文档失败:', error);
      if (documentList) {
        documentList.innerHTML = this.renderErrorState();
      }
    }
  }

  async fetchProjectDocuments(projectId) {
    // 模拟API请求 - 实际应用中需要替换为真实的API调用
    // 这里我们从页面现有数据中获取文档信息
    const projectElement = document.querySelector(`[data-project-id="${projectId}"]`);
    const existingDocs = projectElement?.querySelectorAll('.project-list__doc-item') || [];
    
    // 转换现有文档数据
    const documents = Array.from(existingDocs).map((docElement, index) => {
      const link = docElement.querySelector('.project-list__doc-link');
      const nameElement = docElement.querySelector('.project-list__doc-name');
      const timeElement = docElement.querySelector('.project-list__doc-time');
      
      return {
        id: this.extractDocIdFromUrl(link?.href || ''),
        name: nameElement?.textContent?.trim() || `文档 ${index + 1}`,
        modify_time: timeElement?.textContent?.trim() || '未知时间',
        view_count: Math.floor(Math.random() * 100), // 模拟查看次数
        word_count: Math.floor(Math.random() * 5000) + 500, // 模拟字数
        author: '作者', // 可以从其他地方获取
      };
    });

    // 如果没有现有文档，生成一些示例文档
    if (documents.length === 0) {
      const exampleDocs = [
        { id: `${projectId}_doc_1`, name: '项目介绍', modify_time: '2天前', view_count: 45, word_count: 1200, author: '系统' },
        { id: `${projectId}_doc_2`, name: '使用指南', modify_time: '5天前', view_count: 32, word_count: 800, author: '系统' },
        { id: `${projectId}_doc_3`, name: '常见问题', modify_time: '1周前', view_count: 28, word_count: 600, author: '系统' },
      ];
      return exampleDocs;
    }

    return documents;
  }

  extractDocIdFromUrl(url) {
    const matches = url.match(/\/doc\/(\d+)\//);
    return matches ? matches[1] : Math.random().toString(36).substr(2, 9);
  }

  renderLoadingState() {
    return `
      <div class="document-loading">
        <div class="document-loading__spinner"></div>
        <p class="document-loading__text">正在加载文档...</p>
      </div>
    `;
  }

  renderDocumentList(documents) {
    return documents.map(doc => `
      <a href="/doc/${doc.id}/" class="document-item" data-doc-id="${doc.id}" target="_blank">
        <div class="document-item__header">
          <h3 class="document-item__title">${doc.name}</h3>
          <div class="document-item__actions">
            <button class="document-item__action" title="编辑">✏️</button>
            <button class="document-item__action" title="分享">🔗</button>
            <button class="document-item__action" title="更多">⋮</button>
          </div>
        </div>
        <div class="document-item__meta">
          <span class="document-item__stat">
            <span>👁️</span>
            <span>${doc.view_count || 0} 次查看</span>
          </span>
          <span class="document-item__stat">
            <span>📝</span>
            <span>${doc.word_count || 0} 字</span>
          </span>
          <span class="document-item__stat">
            <span>🕒</span>
            <span>${doc.modify_time}</span>
          </span>
          <span class="document-item__stat">
            <span>👤</span>
            <span>${doc.author || '未知'}</span>
          </span>
        </div>
      </a>
    `).join('');
  }

  renderEmptyDocuments(projectName) {
    return `
      <div class="document-panel__empty">
        <div class="document-panel__empty-icon">📝</div>
        <h3 class="document-panel__empty-title">暂无文档</h3>
        <p class="document-panel__empty-desc">
          "${projectName}" 中还没有文档<br>
          <button class="btn btn-primary" style="margin-top: 1rem;" onclick="document.getElementById('new-doc').click()">
            创建第一个文档
          </button>
        </p>
      </div>
    `;
  }

  renderErrorState() {
    return `
      <div class="document-panel__empty">
        <div class="document-panel__empty-icon">⚠️</div>
        <h3 class="document-panel__empty-title">加载失败</h3>
        <p class="document-panel__empty-desc">
          无法加载文档列表，请稍后重试<br>
          <button class="btn btn-secondary" style="margin-top: 1rem;" onclick="document.getElementById('refresh-docs').click()">
            重新加载
          </button>
        </p>
      </div>
    `;
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
          <div class="project-grid__card" data-project-id="${project.id}">
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
          </div>
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
              <div class="project-compact__item" data-project-id="${project.id}">
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
              </div>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
  }

  // 工具方法
  getProjectData() {
    const projectElements = document.querySelectorAll('.project-list__item');
    return Array.from(projectElements).map(el => ({
      id: el.dataset.projectId || Math.random().toString(36),
      name: el.querySelector('.project-list__item-title span:last-child')?.textContent?.trim() || '未命名项目',
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
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  new DualPaneProjectView();
});

// 附加样式
const additionalCSS = `
.document-loading {
  text-align: center;
  padding: var(--space-16) var(--space-6);
  color: var(--text-tertiary);
}

.document-loading__spinner {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-primary);
  border-radius: var(--radius-full);
  border-top-color: var(--brand-primary);
  animation: spin 1s ease-in-out infinite;
  margin-bottom: var(--space-4);
}

.document-loading__text {
  margin: 0;
  font-size: var(--text-base);
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
style.textContent = additionalCSS;
document.head.appendChild(style);