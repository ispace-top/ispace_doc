/**
 * iSpaceDoc Sidebar Tree — toggle, collapse, context menu, drag & drop.
 * Requires SortableJS (loaded via CDN in sidebar_tree.html).
 */
(function(){
	// ---- SVG icons for tree toggle swapping ----
	var TREE_ICONS = {
		'folder-closed': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>',
		'folder-open': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/></svg>',
		'doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>'
	};

	function updateTreeIcon(toggle, state) {
		toggle.innerHTML = TREE_ICONS[state] || TREE_ICONS['doc'];
		toggle.setAttribute('data-icon-state', state);
	}

	// ---- Doc tree toggle: click icon -> expand/collapse children ----
	var sidebarNav = document.getElementById('sidebarNav');
	if (!sidebarNav) return;

	sidebarNav.addEventListener('click', function(e) {
		var toggle = e.target.closest('.ispace-tree-toggle');
		if (!toggle) return;
		if (toggle.getAttribute('data-has-children') !== '1') return;

		e.preventDefault();
		e.stopPropagation();

		var node = toggle.closest('.ispace-tree-node');
		var children = node.querySelector(':scope > .ispace-tree-children');
		if (!children) return;

		var expanded = toggle.getAttribute('data-expanded') === '1';
		if (expanded) {
			children.style.display = 'none';
			updateTreeIcon(toggle, 'folder-closed');
			toggle.setAttribute('data-expanded', '0');
		} else {
			// Accordion: collapse sibling nodes at the same level
			var parentContainer = node.parentElement;
			if (parentContainer) {
				var siblings = parentContainer.querySelectorAll(':scope > .ispace-tree-node');
				siblings.forEach(function(sibling) {
					if (sibling === node) return;
					var sibChildren = sibling.querySelector(':scope > .ispace-tree-children');
					var sibToggle = sibling.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
					if (sibChildren && sibToggle && sibToggle.getAttribute('data-expanded') === '1') {
						sibChildren.style.display = 'none';
						updateTreeIcon(sibToggle, 'folder-closed');
						sibToggle.setAttribute('data-expanded', '0');
					}
				});
			}
			children.style.display = 'block';
			updateTreeIcon(toggle, 'folder-open');
			toggle.setAttribute('data-expanded', '1');
		}
	});

	// ---- Sidebar collapse toggle ----
	var collapseBtn = document.getElementById('sidebarCollapse');
	var sidebar = document.getElementById('globalSidebar');
	var appLayout = document.querySelector('.ispace-app-layout.has-sidebar');
	if (collapseBtn && sidebar) {
		function _applySidebarState(collapsed) {
			if (collapsed) {
				sidebar.classList.add('ispace-sidebar--collapsed');
				if (appLayout) appLayout.classList.add('ispace-layout--sidebar-collapsed');
			} else {
				sidebar.classList.remove('ispace-sidebar--collapsed');
				if (appLayout) appLayout.classList.remove('ispace-layout--sidebar-collapsed');
			}
		}
		if (localStorage.getItem('sidebar-collapsed') === '1') {
			_applySidebarState(true);
		}
		collapseBtn.addEventListener('click', function(){
			var collapsed = !sidebar.classList.contains('ispace-sidebar--collapsed');
			_applySidebarState(collapsed);
			localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
		});
	}

	// ---- Highlight current document & expand ancestor tree nodes ----
	(function(){
		var path = window.location.pathname;
		var proMatch = path.match(/^\/docs\/(\d+)\//);
		if (proMatch) {
			var pid = proMatch[1];
			var docMatch = path.match(/\/docs\/\d+\/(\d+)\//);
			if (docMatch) {
				var docLink = document.querySelector('.ispace-tree-link[href*="/pages/' + pid + '/' + docMatch[1] + '/"]');
				if (docLink) {
					docLink.classList.add('ispace-active');
					var node = docLink.closest('.ispace-tree-node');
					var ownChildren = node.querySelector(':scope > .ispace-tree-children');
					if (ownChildren) {
						ownChildren.style.display = 'block';
						var ownToggle = node.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
						if (ownToggle && ownToggle.getAttribute('data-has-children') === '1') {
							updateTreeIcon(ownToggle, 'folder-open');
							ownToggle.setAttribute('data-expanded', '1');
						}
					}
					while (node) {
						var childrenContainer = node.parentElement;
						if (!childrenContainer || !childrenContainer.classList.contains('ispace-tree-children')) break;
						childrenContainer.style.display = 'block';
						var ancestorNode = childrenContainer.parentElement;
						if (!ancestorNode || !ancestorNode.classList.contains('ispace-tree-node')) break;
						var ancToggle = ancestorNode.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
						if (ancToggle && ancToggle.getAttribute('data-has-children') === '1') {
							updateTreeIcon(ancToggle, 'folder-open');
							ancToggle.setAttribute('data-expanded', '1');
						}
						node = ancestorNode;
					}
				}
			} else {
				var proLink = document.querySelector('.ispace-tree-link[href$="/pages/' + pid + '/"]');
				if (proLink) {
					proLink.classList.add('ispace-active');
					var proNode = proLink.closest('.ispace-tree-node');
					if (proNode) {
						var childrenContainer = proNode.querySelector(':scope > .ispace-tree-children');
						if (childrenContainer) {
							childrenContainer.style.display = 'block';
							var toggle = proNode.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
							if (toggle && toggle.getAttribute('data-has-children') === '1') {
								updateTreeIcon(toggle, 'folder-open');
								toggle.setAttribute('data-expanded', '1');
							}
						}
						// Expand ancestor chain up to the root
						var node = proNode;
						while (node) {
							var cc = node.parentElement;
							if (!cc || !cc.classList.contains('ispace-tree-children')) break;
							cc.style.display = 'block';
							var ancNode = cc.parentElement;
							if (!ancNode || !ancNode.classList.contains('ispace-tree-node')) break;
							var ancToggle = ancNode.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
							if (ancToggle && ancToggle.getAttribute('data-has-children') === '1') {
								updateTreeIcon(ancToggle, 'folder-open');
								ancToggle.setAttribute('data-expanded', '1');
							}
							node = ancNode;
						}
					}
				}
			}
		}
	})();

	// ---- Right-click Context Menu ----
	var contextMenu = document.getElementById('sidebarContextMenu');
	if (!contextMenu) {
		contextMenu = document.createElement('div');
		contextMenu.className = 'ispace-context-menu';
		contextMenu.id = 'sidebarContextMenu';
		contextMenu.style.display = 'none';
		document.body.appendChild(contextMenu);
	}

	var menuIcons = {
		'new-doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/><line x1="12" y1="13" x2="12" y2="19"/><line x1="9" y1="16" x2="15" y2="16"/></svg>',
		'new-child-doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/><line x1="12" y1="13" x2="12" y2="19"/><line x1="9" y1="16" x2="15" y2="16"/></svg>',
		'rename-doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>',
		'delete-pro': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
		'delete-doc': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
		'new-doc-root': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/><line x1="12" y1="13" x2="12" y2="19"/><line x1="9" y1="16" x2="15" y2="16"/></svg>',
		'new-table-root': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/><line x1="12" y1="3" x2="12" y2="21"/></svg>',
		'new-child-table': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/><line x1="12" y1="3" x2="12" y2="21"/></svg>',
	};

	var menuCls = {
		'delete-pro': ' ispace-context-menu-item--danger',
		'delete-doc': ' ispace-context-menu-item--danger'
	};

	function showContextMenu(e, items) {
		e.preventDefault();
		e.stopPropagation();
		currentContextTarget = e.currentTarget;
		contextMenu.innerHTML = items.map(function(item) {
			var icon = menuIcons[item.action.split(':')[0]] || '';
			var cls = menuCls[item.action.split(':')[0]] || '';
			return '<button class="ispace-context-menu-item' + cls + '" data-action="' + item.action + '">' + icon + '<span>' + item.label + '</span></button>';
		}).join('');
		contextMenu.style.display = 'block';
		var x = e.clientX, y = e.clientY;
		var mw = contextMenu.offsetWidth || 170;
		var mh = contextMenu.offsetHeight || 200;
		if (x + mw > window.innerWidth) x = window.innerWidth - mw - 8;
		if (y + mh > window.innerHeight) y = window.innerHeight - mh - 8;
		contextMenu.style.left = x + 'px';
		contextMenu.style.top = y + 'px';
	}

	function hideContextMenu() {
		contextMenu.style.display = 'none';
		currentContextTarget = null;
	}

	var _contextNode = null;

	// Context menu on sidebar nav — tree rows + empty space
	sidebarNav.addEventListener('contextmenu', function(e) {
		var row = e.target.closest('.ispace-tree-row');
		if (!row) {
			_contextNode = null;
			var items = [];
			items.push({label: '新建文档', action: 'new-doc-root:'});
			items.push({label: '新建表格', action: 'new-table-root:'});
			showContextMenu(e, items);
			return;
		}

		var node = row.parentElement;
		if (!node.classList.contains('ispace-tree-node')) return;

		_contextNode = node;

		var canCreate = node.getAttribute('data-can-create') === '1';
		var canManage = node.getAttribute('data-can-manage') === '1';
		if (!canCreate && !canManage) return;

		var docId = node.getAttribute('data-doc-id');
		var items = [];
		if (canCreate) items.push({label: '新建文档', action: 'new-child-doc:' + docId});
		if (canCreate) items.push({label: '新建表格', action: 'new-child-table:' + docId});
		if (canManage) items.push({label: '重命名', action: 'rename-doc:' + docId});
		if (canManage) items.push({label: '删除文档', action: 'delete-doc:' + docId});
		if (items.length === 0) return;
		showContextMenu(e, items);
	});

	// Context menu action handling
	contextMenu.addEventListener('click', function(e) {
		var item = e.target.closest('.ispace-context-menu-item');
		if (!item) return;
		var action = item.getAttribute('data-action');
		var parts = action.split(':');
		var type = parts[0], id = parts[1];
		hideContextMenu();
		handleContextAction(type, id);
	});

	function handleContextAction(type, id) {
		var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
		var csrfToken = csrf ? csrf.value : (window.__ISPACEDOC__ ? window.__ISPACEDOC__.csrfToken : '');
		function goto(url) {
			if (window.iSpaceDoc && window.iSpaceDoc.SPA) {
				window.iSpaceDoc.SPA.navigate(url);
			} else {
				window.location.href = url;
			}
		}
		if (type === 'new-doc') {
			goto('/pages/' + id + '/?create=1');
		} else if (type === 'new-doc-root') {
			if (id) {
				goto('/pages/' + id + '/?create=1');
			} else {
				goto('/?create=1');
			}
		} else if (type === 'new-table-root') {
			if (id) {
				goto('/pages/' + id + '/?create=1&eid=4');
			} else {
				goto('/?create=1&eid=4');
			}
		} else if (type === 'new-child-doc') {
			goto('/pages/' + id + '/?create_child=1');
		} else if (type === 'new-child-table') {
			goto('/pages/' + id + '/?create_child=1&eid=4');
		} else if (type === 'delete-doc') {
			var docName = '';
			if (_contextNode) {
				var nameEl = _contextNode.querySelector('.ispace-truncate');
				if (nameEl) docName = nameEl.textContent.trim();
			}
			function _cleanupDirtyNode() {
				if (_contextNode) {
					_contextNode.parentElement.removeChild(_contextNode);
					_contextNode = null;
				}
				var isCurrentDoc = window.location.pathname.indexOf('/pages/' + id + '/') !== -1;
				if (isCurrentDoc) {
					window.location.href = '/';
				}
			}
			// Check for children first (matches doc-settings.js triggerDeleteFlow)
			fetch('/documents/' + id + '/children/')
			.then(function(r) { return r.json(); })
			.then(function(data) {
				if (!data.status) {
					// 文档已不存在（脏数据），直接移除 DOM 节点
					if (data.data === '文档不存在') {
						_cleanupDirtyNode();
					} else {
						alert(data.data || '检查失败');
					}
					return;
				}
				function doDelete() {
					var fd = new FormData();
					fd.append('doc_id', id);
					fd.append('csrfmiddlewaretoken', csrfToken);
					var isCurrentDoc = window.location.pathname.indexOf('/pages/' + id + '/') !== -1;
					fetch('/documents/delete/', {method:'POST', body:fd})
					.then(function(r) { return r.json(); })
					.then(function(r) {
						if (r.status) {
							if (isCurrentDoc) {
								window.location.href = '/';
							} else {
								window.location.reload();
							}
						}
						else {
							// 文档已不存在（脏数据），直接移除 DOM 节点
							if (r.data === '文档不存在') {
								_cleanupDirtyNode();
							} else {
								alert(r.data);
							}
						}
					});
				}
				if (data.has_children) {
					window.iSpaceDoc.confirmDeleteWithCaptcha({
						docName: docName,
						totalChildren: data.total_children,
						directChildren: data.direct_children || [],
						csrfToken: csrfToken
					}).then(function(confirmed) {
						if (confirmed) doDelete();
					});
				} else {
					window.iSpaceDoc.confirm('确认删除《' + docName + '》？文档将被移入回收站。', { variant: 'danger' })
					.then(function(ok) {
						if (ok) doDelete();
					});
				}
			})
			.catch(function() { alert('网络异常，请重试'); });
		} else if (type === 'rename-doc') {
			var newName = prompt('请输入新名称：');
			if (!newName) return;
			var fd2 = new FormData();
			fd2.append('doc_id', id);
			fd2.append('doc_name', newName);
			fd2.append('csrfmiddlewaretoken', csrfToken);
			fetch('/documents/' + id + '/edit/', {method:'POST', body:fd2})
			.then(function(r) { return r.json(); })
			.then(function(r) {
				if (r.status) { window.location.reload(); }
				else { alert(r.data || '重命名失败'); }
			});
		} else if (type === 'delete-pro') {
			var fd3 = new FormData();
			fd3.append('doc_id', id);
			fd3.append('csrfmiddlewaretoken', csrfToken);
			fetch('/documents/delete/', {method:'POST', body:fd3})
			.then(function(r) { return r.json(); })
			.then(function(r) {
				if (r.status) { window.location.href = '/'; }
				else { alert(r.data); }
			});
		}
	}

	// Dismiss context menu on outside click
	document.addEventListener('click', hideContextMenu);

	// ---- Drag & Drop Sort ----
	if (typeof Sortable !== 'undefined') {
		var sortableInstances = [];
		var csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
		var csrf = csrfEl ? csrfEl.value : (window.__ISPACEDOC__ ? window.__ISPACEDOC__.csrfToken : '');
		var hoverExpandTimer = null;
		var hoverExpandTarget = null;
		// Save original position for revert on failure
		var dragOriginalContainer = null;
		var dragOriginalIndex = -1;

		function clearHoverExpand() {
			if (hoverExpandTimer) { clearTimeout(hoverExpandTimer); hoverExpandTimer = null; }
			if (hoverExpandTarget) {
				hoverExpandTarget.classList.remove('ispace-drop-target');
				hoverExpandTarget = null;
			}
		}

		function expandNodeIfCollapsed(node) {
			var toggle = node.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
			if (!toggle || toggle.getAttribute('data-has-children') !== '1') return false;
			if (toggle.getAttribute('data-expanded') === '1') return true;
			// Accordion: collapse siblings at the same level first
			var parentContainer = node.parentElement;
			if (parentContainer) {
				var siblings = parentContainer.querySelectorAll(':scope > .ispace-tree-node');
				siblings.forEach(function(sibling) {
					if (sibling === node) return;
					var sibChildren = sibling.querySelector(':scope > .ispace-tree-children');
					var sibToggle = sibling.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
					if (sibChildren && sibToggle && sibToggle.getAttribute('data-expanded') === '1') {
						sibChildren.style.display = 'none';
						updateTreeIcon(sibToggle, 'folder-closed');
						sibToggle.setAttribute('data-expanded', '0');
					}
				});
			}
			var children = node.querySelector(':scope > .ispace-tree-children');
			if (children) {
				children.style.display = 'block';
				updateTreeIcon(toggle, 'folder-open');
				toggle.setAttribute('data-expanded', '1');
			}
			return true;
		}

		function createSortableOptions() {
			return {
				group: 'doc-tree',
				animation: 150,
				ghostClass: 'ispace-sortable-ghost',
				dragClass: 'ispace-sortable-drag',
				handle: '.ispace-tree-row',
				delay: 200,
				delayOnTouchOnly: false,
				fallbackOnBody: true,
				forceFallback: true,
				swapThreshold: 0.65,
				scroll: true,
				scrollSensitivity: 30,
				scrollSpeed: 10,
				onStart: function(evt) {
					document.body.style.cursor = 'grabbing';
					var item = evt.item;
					dragOriginalContainer = item.parentElement;
					var origSiblings = dragOriginalContainer.querySelectorAll(':scope > .ispace-tree-node');
					dragOriginalIndex = Array.prototype.indexOf.call(origSiblings, item);
				},
				onEnd: handleDragEnd,
				onMove: handleDragMove,
				onChange: handleDragChange
			};
		}
		function initSortable() {
			if (sidebarNav) {
				sortableInstances.push(new Sortable(sidebarNav, createSortableOptions()));
			}
			var containers = document.querySelectorAll('#sidebarNav .ispace-tree-children');
			containers.forEach(function(container) {
				sortableInstances.push(new Sortable(container, createSortableOptions()));
			});
		}
		function handleDragMove(evt) {
			var dragged = evt.dragged;
			var draggedNode = dragged.closest('.ispace-tree-node');

			// Try multiple ways to locate the hover target node
			var targetNode = null;
			// 1) evt.related (Sortable-provided related element)
			if (evt.related) {
				targetNode = evt.related.closest('.ispace-tree-node');
			}
			// 2) evt.to container (when dragging into .ispace-tree-children)
			if (!targetNode && evt.to && evt.to.classList.contains('ispace-tree-children')) {
				targetNode = evt.to.closest('.ispace-tree-node');
			}

			if (!targetNode) { clearHoverExpand(); return true; }

			// Skip self or ancestor (prevent circular drag)
			if (draggedNode && (targetNode === draggedNode || draggedNode.contains(targetNode))) {
				return true;
			}

			var targetId = parseInt(targetNode.getAttribute('data-doc-id'));
			if (isNaN(targetId)) { clearHoverExpand(); return true; }
			if (isDescendant(draggedNode, targetId)) {
				clearHoverExpand();
				return false;
			}

			// Check if target has collapsed children → auto-expand on hover
			var toggle = targetNode.querySelector(':scope > .ispace-tree-row > .ispace-tree-toggle');
			var hasChildren = toggle && toggle.getAttribute('data-has-children') === '1';
			var isCollapsed = toggle && toggle.getAttribute('data-expanded') !== '1';

			if (hasChildren && isCollapsed && hoverExpandTarget !== targetNode) {
				clearHoverExpand();
				hoverExpandTarget = targetNode;
				targetNode.classList.add('ispace-drop-target');
				hoverExpandTimer = setTimeout(function() {
					if (expandNodeIfCollapsed(targetNode)) {
						sortableInstances.forEach(function(s) {
							try { s.option('disabled', false); } catch(e) {}
						});
					}
					targetNode.classList.remove('ispace-drop-target');
				}, 700);
			} else if (!hasChildren || !isCollapsed) {
				clearHoverExpand();
			}
			return true;
		}
		var _lastDropZoneEl = null;
		function handleDragChange(evt) {
			// Highlight child-list containers as drop zones when dragging near them
			var to = evt.to;
			var newZone = null;
			if (to && to.classList.contains('ispace-tree-children')) {
				var draggedNode = evt.dragged;
				if (draggedNode && to.contains(draggedNode) && draggedNode.parentElement === to) {
					newZone = to;
				}
			}
			if (_lastDropZoneEl !== newZone) {
				if (_lastDropZoneEl) _lastDropZoneEl.classList.remove('ispace-drop-zone');
				if (newZone) newZone.classList.add('ispace-drop-zone');
				_lastDropZoneEl = newZone;
			}
		}

		function handleDragEnd(evt) {
			document.body.style.cursor = '';
			clearHoverExpand();
			if (_lastDropZoneEl) { _lastDropZoneEl.classList.remove('ispace-drop-zone'); _lastDropZoneEl = null; }
			var item = evt.item;
			var newParentContainer = item.parentElement;
			var isInChildren = newParentContainer.classList.contains('ispace-tree-children');
			var newParentNode = isInChildren ? newParentContainer.closest('.ispace-tree-node') : null;
			var docId = parseInt(item.getAttribute('data-doc-id'));
			var newParentId = newParentNode ? parseInt(newParentNode.getAttribute('data-doc-id')) : 0;
			if (!newParentId) newParentId = 0;
			var siblings = newParentContainer.querySelectorAll(':scope > .ispace-tree-node');
			var newIndex = Array.prototype.indexOf.call(siblings, item);
			if (docId && !isNaN(newIndex)) {
				var fd = new FormData();
				fd.append('doc_id', docId);
				fd.append('pro_id', 0);
				fd.append('move_type', '3');
				fd.append('parent_id', newParentId);
				fd.append('new_parent_id', newParentId);
				fd.append('new_index', newIndex);
				fd.append('csrfmiddlewaretoken', csrf);
				fetch('/documents/move/', { method: 'POST', body: fd })
					.then(function(r) { return r.json(); })
					.then(function(data) {
						if (!data.status) {
							// Revert: move item back to original position
							if (dragOriginalContainer && dragOriginalIndex >= 0) {
								var origSiblings = dragOriginalContainer.querySelectorAll(':scope > .ispace-tree-node');
								var refNode = origSiblings[dragOriginalIndex];
								if (refNode && refNode !== item) {
									dragOriginalContainer.insertBefore(item, refNode);
								} else {
									dragOriginalContainer.appendChild(item);
								}
							}
							if (window.showError) {
								window.showError(data.data || '移动失败，请检查权限');
							}
						}
					})
					.catch(function() {
						// Network error: revert
						if (dragOriginalContainer && dragOriginalIndex >= 0) {
							var origSiblings = dragOriginalContainer.querySelectorAll(':scope > .ispace-tree-node');
							var refNode = origSiblings[dragOriginalIndex];
							if (refNode && refNode !== item) {
								dragOriginalContainer.insertBefore(item, refNode);
							} else {
								dragOriginalContainer.appendChild(item);
							}
						}
						if (window.showError) {
							window.showError('网络异常，移动失败');
						}
					});
			}
		}

		function isDescendant(node, targetId) {
			var ids = [];
			var children = node.querySelectorAll('.ispace-tree-node');
			children.forEach(function(c) {
				ids.push(parseInt(c.getAttribute('data-doc-id')));
			});
			return ids.indexOf(targetId) !== -1;
		}

		initSortable();
	}

})();
