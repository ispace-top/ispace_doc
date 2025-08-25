/*
 * 重新设计的界面交互逻辑
 * 实现左右两栏布局的文集文档管理
 */

class RedesignedProjectInterface {
  constructor() {
    this.selectedProjectId = null;
    this.selectedProjectName = '';
    this.currentView = localStorage.getItem('project-view') || 'list';
    this.init();
  }

  init() {
    this.bindEvents();
    this.initializeView();
  }

  bindEvents() {
    // 视图切换
    document.addEventListener('click', (e) => {
      if (e.target.matches('.view-btn')) {
        this.switchView(e.target.dataset.view);
      }
    });

    // 项目卡片点击
    document.addEventListener('click', (e) => {
      if (e.target.closest('.project-card') && !e.target.closest('.card-actions')) {
        const card = e.target.closest('.project-card');
        const projectId = card.dataset.projectId;
        const projectName = card.dataset.projectName;
        this.selectProject(projectId, projectName, card);
      }
    });

    // 文档项点击
    document.addEventListener('click', (e) => {
      if (e.target.closest('.doc-item') && !e.target.closest('.doc-actions')) {
        const docItem = e.target.closest('.doc-item');
        this.openDocument(docItem);
      }
    });
  }

  initializeView() {
    // 恢复视图状态
    this.updateViewButtons();
    this.renderProjectView();
  }

  switchView(viewType) {
    this.currentView = viewType;
    localStorage.setItem('project-view', viewType);
    this.updateViewButtons();
    this.renderProjectView();
  }

  updateViewButtons() {
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('view-btn--active', btn.dataset.view === this.currentView);
    });
  }

  renderProjectView() {
    const container = document.getElementById('project-list');
    if (!container) return;

    const projects = this.getProjectsData();
    
    switch (this.currentView) {
      case 'grid':
        container.innerHTML = this.renderGridView(projects);
        break;
      case 'compact':
        container.innerHTML = this.renderCompactView(projects);
        break;
      default:
        // 保持原有的列表视图（已在HTML中）
        break;
    }
  }

  renderGridView(projects) {
    return `
      <div class="project-grid">
        ${projects.map(project => `
          <div class="project-grid-card" data-project-id="${project.id}" data-project-name="${project.name}">
            <div class="grid-card-header">
              <div class="grid-card-icon">
                ${this.getProjectIcon(project)}
              </div>
              <div class="grid-card-actions">
                ${project.canEdit ? `<button class="action-btn" onclick="editProject('${project.id}')" title="编辑">✏️</button>` : ''}
                <button class="action-btn" onclick="shareProject('${project.id}')" title="分享">🔗</button>
              </div>
            </div>
            <h3 class="grid-card-title">${project.name}</h3>
            ${project.description ? `<p class="grid-card-desc">${project.description}</p>` : ''}
            <div class="grid-card-stats">
              <span class="grid-stat">📄 ${project.docCount} 篇</span>
              <span class="grid-stat">👁️ ${project.viewCount} 次</span>
            </div>
            <div class="grid-card-footer">
              <span class="status-badge status-${project.role}">${this.getStatusText(project.role)}</span>
              <span class="time-stamp">${project.updateTime}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderCompactView(projects) {
    return `
      <div class="project-compact-list">
        ${projects.map(project => `
          <div class="compact-item" data-project-id="${project.id}" data-project-name="${project.name}">
            <div class="compact-icon">${this.getProjectIcon(project)}</div>
            <div class="compact-content">
              <h4 class="compact-title">${project.name}</h4>
              <div class="compact-meta">
                <span>📄 ${project.docCount}</span>
                <span>👁️ ${project.viewCount}</span>
                <span>🕒 ${project.updateTime}</span>
                <span class="status-badge status-${project.role}">${this.getStatusText(project.role)}</span>
              </div>
            </div>
            <div class="compact-actions">
              ${project.canEdit ? `<button class="action-btn" onclick="editProject('${project.id}')">编辑</button>` : ''}
              <button class="action-btn" onclick="shareProject('${project.id}')">分享</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  getProjectsData() {
    // 从页面现有数据中提取项目信息
    const projectCards = document.querySelectorAll('.project-card[data-project-id]');
    return Array.from(projectCards).map(card => {
      return {
        id: card.dataset.projectId,
        name: card.dataset.projectName,
        description: card.querySelector('.card-desc')?.textContent?.trim() || '',
        docCount: card.querySelector('.meta-item')?.textContent?.match(/\\d+/)?.[0] || '0',
        viewCount: card.querySelectorAll('.meta-item')?.[1]?.textContent?.match(/\\d+/)?.[0] || '0',
        role: this.extractStatusFromCard(card),
        updateTime: card.querySelector('.time-stamp')?.textContent || '未知',
        canEdit: card.querySelector('.card-actions .action-btn[onclick*="editProject"]') !== null
      };
    });
  }

  extractStatusFromCard(card) {
    const statusBadge = card.querySelector('.status-badge');
    if (statusBadge) {
      if (statusBadge.textContent.includes('公开')) return 0;
      if (statusBadge.textContent.includes('私密')) return 1;
      if (statusBadge.textContent.includes('密码')) return 3;
      if (statusBadge.textContent.includes('协作')) return 99;
    }
    return 0;
  }

  getProjectIcon(project) {
    const icons = ['📚', '📖', '📝', '📋', '📊', '🔖', '📑', '📄'];
    return icons[project.id % icons.length] || '📚';
  }

  getStatusText(role) {
    const statusMap = {
      0: '🌐 公开',
      1: '🔒 私密',
      3: '🔐 密码',
      99: '👥 协作'
    };
    return statusMap[role] || '🌐 公开';
  }

  selectProject(projectId, projectName, cardElement) {
    // 移除之前的选中状态
    document.querySelectorAll('.project-card').forEach(card => {
      card.classList.remove('selected');
    });

    // 添加选中状态
    cardElement.classList.add('selected');

    // 更新全局状态
    this.selectedProjectId = projectId;
    this.selectedProjectName = projectName;

    // 更新右侧面板
    this.updateDocumentPanel(projectId, projectName);
  }

  async updateDocumentPanel(projectId, projectName) {
    const titleElement = document.getElementById('selected-project-title');
    const actionsElement = document.getElementById('doc-actions');
    const welcomeState = document.getElementById('welcome-state');
    const documentList = document.getElementById('document-list');
    const loadingState = document.getElementById('loading-state');

    // 更新标题
    titleElement.textContent = projectName;
    
    // 显示操作按钮
    actionsElement.style.display = 'flex';

    // 显示加载状态
    welcomeState.style.display = 'none';
    documentList.style.display = 'none';
    loadingState.style.display = 'block';

    try {
      // 获取文档数据
      const documents = await this.fetchProjectDocuments(projectId);
      
      // 渲染文档列表
      this.renderDocumentList(documents);
      
      // 显示文档列表
      loadingState.style.display = 'none';
      documentList.style.display = 'block';
    } catch (error) {
      console.error('加载文档失败:', error);
      this.showErrorState();
    }
  }

  async fetchProjectDocuments(projectId) {
    // 实际项目中这里应该是API调用
    // 现在模拟API请求
    return new Promise((resolve) => {
      setTimeout(() => {
        // 模拟文档数据
        const mockDocs = [
          {
            id: `doc_${projectId}_1`,
            name: '项目介绍',
            updateTime: '2小时前',
            views: Math.floor(Math.random() * 100),
            words: Math.floor(Math.random() * 2000) + 500,
            author: '管理员'
          },
          {
            id: `doc_${projectId}_2`,
            name: '用户手册',
            updateTime: '1天前',
            views: Math.floor(Math.random() * 50),
            words: Math.floor(Math.random() * 1500) + 300,
            author: '编辑者'
          },
          {
            id: `doc_${projectId}_3`,
            name: '技术文档',
            updateTime: '3天前',
            views: Math.floor(Math.random() * 80),
            words: Math.floor(Math.random() * 3000) + 1000,
            author: '开发者'
          }
        ];
        resolve(mockDocs);
      }, 600);
    });
  }

  renderDocumentList(documents) {
    const container = document.getElementById('document-list');
    
    if (documents.length === 0) {
      container.innerHTML = this.renderEmptyDocuments();
      return;
    }

    const documentsHtml = documents.map(doc => `
      <div class="doc-item" data-doc-id="${doc.id}">
        <div class="doc-header">
          <div class="doc-icon">📄</div>
          <div class="doc-info">
            <h4 class="doc-title">${doc.name}</h4>
            <div class="doc-meta">
              <span class="doc-stat">👁️ ${doc.views}</span>
              <span class="doc-stat">📝 ${doc.words} 字</span>
              <span class="doc-stat">🕒 ${doc.updateTime}</span>
              <span class="doc-stat">👤 ${doc.author}</span>
            </div>
          </div>
          <div class="doc-actions">
            <button class="action-btn" onclick="editDocument('${doc.id}')" title="编辑">✏️</button>
            <button class="action-btn" onclick="shareDocument('${doc.id}')" title="分享">🔗</button>
          </div>
        </div>
      </div>
    `).join('');

    container.innerHTML = documentsHtml;
  }

  renderEmptyDocuments() {
    return `
      <div class="empty-state">
        <div class="empty-icon">📝</div>
        <h3 class="empty-title">暂无文档</h3>
        <p class="empty-desc">
          该文集中还没有文档
          <br><button class="btn-primary" onclick="createDocument()" style="margin-top: 1rem;">
            创建第一个文档
          </button>
        </p>
      </div>
    `;
  }

  showErrorState() {
    const container = document.getElementById('document-list');
    const loadingState = document.getElementById('loading-state');
    
    loadingState.style.display = 'none';
    container.innerHTML = `
      <div class="error-state">
        <div class="error-icon">⚠️</div>
        <h3 class="error-title">加载失败</h3>
        <p class="error-desc">
          无法加载文档列表，请稍后重试
          <br><button class="btn-secondary" onclick="refreshDocuments()" style="margin-top: 1rem;">
            重新加载
          </button>
        </p>
      </div>
    `;
    container.style.display = 'block';
  }

  openDocument(docItem) {
    const docId = docItem.dataset.docId;
    if (docId) {
      window.open(`/doc/${docId}/`, '_blank');
    }
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
  }
}

// 全局函数（供HTML内联事件使用）
function selectProject(projectId, projectName) {
  const card = document.querySelector(`[data-project-id="${projectId}"]`);
  if (card && window.projectInterface) {
    window.projectInterface.selectProject(projectId, projectName, card);
  }
}

function editProject(projectId) {
  window.location.href = `/manage/project/${projectId}/edit/`;
}

function shareProject(projectId) {
  const url = `${window.location.origin}/project/${projectId}/`;
  if (navigator.share) {
    navigator.share({ title: '分享文集', url: url });
  } else {
    navigator.clipboard.writeText(url).then(() => {
      window.projectInterface?.showToast('链接已复制到剪贴板');
    });
  }
}

function createDocument() {
  if (window.projectInterface?.selectedProjectId) {
    window.open(`/project/${window.projectInterface.selectedProjectId}/create_doc/`, '_blank');
  }
}

function editDocument(docId) {
  window.open(`/doc/${docId}/edit/`, '_blank');
}

function shareDocument(docId) {
  const url = `${window.location.origin}/doc/${docId}/`;
  if (navigator.share) {
    navigator.share({ title: '分享文档', url: url });
  } else {
    navigator.clipboard.writeText(url).then(() => {
      window.projectInterface?.showToast('链接已复制到剪贴板');
    });
  }
}

function refreshDocuments() {
  if (window.projectInterface?.selectedProjectId) {
    window.projectInterface.updateDocumentPanel(
      window.projectInterface.selectedProjectId, 
      window.projectInterface.selectedProjectName
    );
  }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  window.projectInterface = new RedesignedProjectInterface();
});

// 附加样式（用于网格和紧凑视图）
const additionalStyles = `
/* 网格视图样式 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.project-grid-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  cursor: pointer;
  transition: all 0.3s ease;
}

.project-grid-card:hover {
  background: var(--bg-hover);
  border-color: var(--brand-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.grid-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3);
}

.grid-card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light);
  color: var(--brand-primary);
  border-radius: var(--radius-lg);
  font-size: var(--text-lg);
}

.grid-card-actions {
  display: flex;
  gap: var(--space-1);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.project-grid-card:hover .grid-card-actions {
  opacity: 1;
}

.grid-card-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-2) 0;
}

.grid-card-desc {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0 0 var(--space-3) 0;
  line-height: var(--leading-normal);
}

.grid-card-stats {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.grid-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-primary);
}

/* 紧凑视图样式 */
.project-compact-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.compact-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  transition: all 0.2s ease;
}

.compact-item:hover {
  background: var(--bg-hover);
  border-color: var(--brand-primary);
}

.compact-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light);
  color: var(--brand-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  flex-shrink: 0;
}

.compact-content {
  flex: 1;
  min-width: 0;
}

.compact-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 var(--space-1) 0;
}

.compact-meta {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.compact-actions {
  display: flex;
  gap: var(--space-1);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.compact-item:hover .compact-actions {
  opacity: 1;
}

/* 错误状态样式 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-16) var(--space-6);
  color: var(--text-tertiary);
}

.error-icon {
  font-size: 4rem;
  margin-bottom: var(--space-4);
  opacity: 0.6;
}

.error-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  margin: 0 0 var(--space-2) 0;
}

.error-desc {
  font-size: var(--text-base);
  color: var(--text-tertiary);
  margin: 0;
}
`;

// 注入附加样式
const styleElement = document.createElement('style');
styleElement.textContent = additionalStyles;
document.head.appendChild(styleElement);