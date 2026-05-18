/**
 * iSpaceDoc 主题切换器
 * 支持亮色/深色模式无缝切换
 */

class ThemeSwitcher {
  constructor() {
    this.init();
  }

  init() {
    // 获取存储的主题偏好，默认为系统偏好
    this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
    
    // 应用主题
    this.applyTheme(this.currentTheme);
    
    // 监听系统主题变化
    this.watchSystemTheme();
    
    // 创建切换器UI
    this.createThemeSwitcher();
  }

  /**
   * 获取系统主题偏好
   */
  getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  /**
   * 获取存储的主题偏好
   */
  getStoredTheme() {
    return localStorage.getItem('ispacedoc-theme');
  }

  /**
   * 存储主题偏好
   */
  setStoredTheme(theme) {
    localStorage.setItem('ispacedoc-theme', theme);
  }

  /**
   * 应用主题
   */
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
    
    // 更新favicon（如果有深色版本）
    this.updateFavicon(theme);
    
    // 触发自定义事件
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    
    // 更新切换器状态
    this.updateSwitcherState();
  }

  /**
   * 切换主题
   */
  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.applyTheme(newTheme);
    this.setStoredTheme(newTheme);
    
    // 添加切换动画
    this.animateThemeChange();
  }

  /**
   * 设置指定主题
   */
  setTheme(theme) {
    if (['light', 'dark', 'auto'].includes(theme)) {
      if (theme === 'auto') {
        localStorage.removeItem('ispacedoc-theme');
        this.applyTheme(this.getSystemTheme());
      } else {
        this.applyTheme(theme);
        this.setStoredTheme(theme);
      }
    }
  }

  /**
   * 监听系统主题变化
   */
  watchSystemTheme() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addListener(() => {
        // 只有在没有用户偏好时才跟随系统
        if (!this.getStoredTheme()) {
          this.applyTheme(this.getSystemTheme());
        }
      });
    }
  }

  /**
   * 更新favicon
   */
  updateFavicon(theme) {
    const favicon = document.querySelector('link[rel="icon"]');
    if (favicon) {
      const currentHref = favicon.getAttribute('href');
      if (theme === 'dark' && !currentHref.includes('dark')) {
        // 尝试加载深色favicon
        const darkFavicon = currentHref.replace(/(\.[^.]+)$/, '-dark$1');
        const img = new Image();
        img.onload = () => {
          favicon.setAttribute('href', darkFavicon);
        };
        img.src = darkFavicon;
      } else if (theme === 'light' && currentHref.includes('dark')) {
        // 恢复亮色favicon
        favicon.setAttribute('href', currentHref.replace('-dark', ''));
      }
    }
  }

  /**
   * 创建主题切换器UI
   */
  createThemeSwitcher() {
    const switcher = document.createElement('div');
    switcher.className = 'theme-switcher';
    switcher.innerHTML = `
      <button type="button" class="theme-switcher-btn" aria-label="切换主题" title="切换深色/亮色模式">
        <svg class="theme-icon theme-icon-light" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2"/>
          <path d="m12 2 0 2" stroke="currentColor" stroke-width="2"/>
          <path d="m12 20 0 2" stroke="currentColor" stroke-width="2"/>
          <path d="m22 12-2 0" stroke="currentColor" stroke-width="2"/>
          <path d="m4 12-2 0" stroke="currentColor" stroke-width="2"/>
          <path d="m19.07 4.93-1.41 1.41" stroke="currentColor" stroke-width="2"/>
          <path d="m6.34 17.66-1.41 1.41" stroke="currentColor" stroke-width="2"/>
          <path d="m19.07 19.07-1.41-1.41" stroke="currentColor" stroke-width="2"/>
          <path d="m6.34 6.34-1.41-1.41" stroke="currentColor" stroke-width="2"/>
        </svg>
        <svg class="theme-icon theme-icon-dark" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="2" fill="currentColor"/>
        </svg>
      </button>
    `;

    // 添加样式
    const style = document.createElement('style');
    style.textContent = `
      .theme-switcher {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 1000;
      }
      
      .theme-switcher-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        background-color: var(--bg-primary);
        border: 1px solid var(--border-primary);
        border-radius: 50%;
        box-shadow: var(--shadow-lg);
        cursor: pointer;
        transition: all 0.2s ease;
        color: var(--text-primary);
      }
      
      .theme-switcher-btn:hover {
        transform: scale(1.05);
        box-shadow: var(--shadow-xl);
      }
      
      .theme-icon {
        transition: all 0.2s ease;
      }
      
      [data-theme="light"] .theme-icon-dark {
        display: none;
      }
      
      [data-theme="dark"] .theme-icon-light {
        display: none;
      }
      
      @media (max-width: 768px) {
        .theme-switcher {
          bottom: 16px;
          right: 16px;
        }
        
        .theme-switcher-btn {
          width: 44px;
          height: 44px;
        }
      }
    `;
    
    document.head.appendChild(style);

    // 添加到页面
    document.body.appendChild(switcher);

    // 绑定点击事件
    switcher.querySelector('.theme-switcher-btn').addEventListener('click', () => {
      this.toggleTheme();
    });

    // 键盘快捷键支持 (Ctrl/Cmd + Shift + L)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        this.toggleTheme();
      }
    });
  }

  /**
   * 更新切换器状态
   */
  updateSwitcherState() {
    const btn = document.querySelector('.theme-switcher-btn');
    if (btn) {
      const title = this.currentTheme === 'light' ? '切换到深色模式' : '切换到亮色模式';
      btn.setAttribute('title', title);
      btn.setAttribute('aria-label', title);
    }
  }

  /**
   * 主题切换动画
   */
  animateThemeChange() {
    const transition = document.createElement('div');
    transition.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: ${this.currentTheme === 'dark' ? '#000' : '#fff'};
      opacity: 0;
      pointer-events: none;
      z-index: 9999;
      transition: opacity 0.3s ease;
    `;
    
    document.body.appendChild(transition);
    
    // 触发动画
    requestAnimationFrame(() => {
      transition.style.opacity = '0.3';
      setTimeout(() => {
        transition.style.opacity = '0';
        setTimeout(() => {
          document.body.removeChild(transition);
        }, 300);
      }, 150);
    });
  }

  /**
   * 获取当前主题
   */
  getCurrentTheme() {
    return this.currentTheme;
  }

  /**
   * 检查是否为深色模式
   */
  isDarkMode() {
    return this.currentTheme === 'dark';
  }

  /**
   * 销毁主题切换器
   */
  destroy() {
    const switcher = document.querySelector('.theme-switcher');
    if (switcher) {
      switcher.remove();
    }
  }
}

// 创建全局实例
window.themeSwitcher = new ThemeSwitcher();

// 为兼容性暴露一些方法到全局
window.toggleTheme = () => window.themeSwitcher.toggleTheme();
window.setTheme = (theme) => window.themeSwitcher.setTheme(theme);
window.getCurrentTheme = () => window.themeSwitcher.getCurrentTheme();

// 导出模块（如果支持）
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeSwitcher;
}