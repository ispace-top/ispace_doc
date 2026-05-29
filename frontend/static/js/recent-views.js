/**
 * 最近浏览共享模块 — AJAX 加载 + 无限滚动
 * 用法：
 *   RecentViews.init({
 *     container: document.getElementById('xxx'),
 *     renderItem: function(item) { return HTMLElement },
 *     pageSize: 50,
 *     emptyHTML: '<p>暂无浏览记录</p>'
 *   });
 */
window.RecentViews = (function() {
  var API_URL = '/api/user/browse-history/';

  function init(options) {
    var container = options.container;
    var renderItem = options.renderItem;
    var pageSize = options.pageSize || 50;
    var emptyHTML = options.emptyHTML || '';

    if (!container || !renderItem) return;

    // 创建列表容器
    var listEl = document.createElement('div');
    listEl.className = options.listClassName || '';
    container.appendChild(listEl);

    // 创建 loading 指示器
    var loadingEl = document.createElement('div');
    loadingEl.style.cssText = 'text-align:center;padding:12px;color:var(--ispace-color-text-quaternary);font-size:var(--ispace-font-xs);display:none;';
    loadingEl.textContent = options.loadingText || '加载中...';
    container.appendChild(loadingEl);

    // 创建 "没有更多了" 指示器
    var endEl = document.createElement('div');
    endEl.style.cssText = 'text-align:center;padding:12px;color:var(--ispace-color-text-quaternary);font-size:var(--ispace-font-xs);display:none;';
    endEl.textContent = 'endText' in options ? options.endText : '— 没有更多了 —';
    container.appendChild(endEl);

    var page = 0;
    var hasMore = true;
    var loading = false;

    function loadPage() {
      if (loading || !hasMore) return;
      loading = true;
      page++;
      loadingEl.style.display = '';
      endEl.style.display = 'none';

      fetch(API_URL + '?page=' + page + '&page_size=' + pageSize, {
        credentials: 'same-origin'
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        loadingEl.style.display = 'none';
        if (!data.status || !data.items || data.items.length === 0) {
          hasMore = false;
          if (page === 1) {
            if (emptyHTML) container.insertAdjacentHTML('afterbegin', emptyHTML);
            if (options.onEmpty) options.onEmpty();
          } else {
            endEl.style.display = '';
          }
          return;
        }
        if (page === 1 && options.onLoaded) {
          options.onLoaded();
        }
        data.items.forEach(function(item) {
          listEl.appendChild(renderItem(item));
        });
        hasMore = data.has_more;
        if (!hasMore && page > 1) {
          endEl.style.display = '';
        }
        loading = false;
      })
      .catch(function() {
        loadingEl.style.display = 'none';
        loading = false;
      });
    }

    // IntersectionObserver 监听 loading 元素
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function(entries) {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadPage();
        }
      }, { rootMargin: '100px' });
      observer.observe(loadingEl);
    }

    // 初始加载
    loadPage();

    return {
      refresh: function() {
        listEl.innerHTML = '';
        page = 0;
        hasMore = true;
        loading = false;
        loadingEl.style.display = 'none';
        endEl.style.display = 'none';
        // 移除 empty 占位
        var emptyNode = container.querySelector('.ispace-empty-state');
        if (emptyNode) emptyNode.remove();
        loadPage();
      }
    };
  }

  return { init: init };
})();
