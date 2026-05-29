/**
 * iSpaceDoc Document Settings — dropdown menu + permission modal + delete flow
 */
window.iSpaceDoc = window.iSpaceDoc || {};
window.iSpaceDoc.DocSettings = (() => {
  var modal = null;
  var currentDocId = null;
  var currentDocName = '';
  var permissions = [];
  var currentTargetType = 'user';
  // v1.0: pending changes queue for batch save
  var _pendingChanges = {};  // key: "type:id", value: {action:'grant'|'update'|'revoke', target_type, target_id, permission, display_name, perm_id?}
  var _originalPermissions = [];  // snapshot of server state for diff
  var _selectedTargets = {};  // key: "type:id", value: {target_type, target_id, display_name} — checked items
  var _roleChanged = false;  // 访问模式是否发生变化
  var _syncChildrenDirty = false;  // “同步到所有子文档”复选框是否变化
  var _currentIsPublic = true;  // 当前 is_public 值
  var _currentAccessPassword = '';  // 当前访问密码

  var PERM_OPTIONS = [
    { value: 'view', label: '仅查看' },
    { value: 'edit', label: '可编辑' },
    { value: 'admin', label: '管理员' },
  ];

  /* ================================================================
     Settings Dropdown
     ================================================================ */
  var dropdownEl = null;
  var _dropdownDocId = null;
  var _dropdownDocName = '';
  var _dropdownCanDelete = true;

  function ensureDropdown() {
    if (dropdownEl) return;
    dropdownEl = document.createElement('div');
    dropdownEl.className = 'ispace-settings-dropdown';
    dropdownEl.id = 'docSettingsDropdown';
    dropdownEl.style.display = 'none';
    dropdownEl.innerHTML =
      '<button class="ispace-context-menu-item" data-action="permissions" id="ds-dropdown-permissions">'
      + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
      + '<span>权限设置</span></button>'
      + '<button class="ispace-context-menu-item ispace-context-menu-item--danger" data-action="delete" id="ds-dropdown-delete">'
      + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>'
      + '<span>删除文件</span></button>';
    document.body.appendChild(dropdownEl);

    dropdownEl.addEventListener('click', function(e) {
      var btn = e.target.closest('[data-action]');
      if (!btn) return;
      hideDropdown();
      var action = btn.getAttribute('data-action');
      if (action === 'permissions') {
        open(_dropdownDocId, _dropdownDocName, false);
      } else if (action === 'delete') {
        triggerDeleteFlow(_dropdownDocId, _dropdownDocName);
      }
    });
  }

  function showDropdown(anchor, docId, docName, canDelete, canManagePermissions) {
    ensureDropdown();
    _dropdownDocId = docId;
    _dropdownDocName = docName;
    _dropdownCanDelete = canDelete;
    var deleteBtn = document.getElementById('ds-dropdown-delete');
    if (deleteBtn) deleteBtn.style.display = canDelete ? '' : 'none';
    var permBtn = document.getElementById('ds-dropdown-permissions');
    if (permBtn) permBtn.style.display = canManagePermissions ? '' : 'none';
    var rect = anchor.getBoundingClientRect();
    dropdownEl.style.display = 'block';
    dropdownEl.style.position = 'fixed';
    dropdownEl.style.left = Math.min(rect.left, window.innerWidth - 180) + 'px';
    dropdownEl.style.top = (rect.bottom + 4) + 'px';
    dropdownEl.style.zIndex = '1100';
  }

  function hideDropdown() {
    if (dropdownEl) dropdownEl.style.display = 'none';
  }

  /* ================================================================
     Trigger delete flow
     ================================================================ */
  function triggerDeleteFlow(docId, docName) {
    var csrf = getCSRF();
    fetch('/documents/' + docId + '/children/', { headers: { 'X-CSRFToken': csrf } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.status) {
          if (window.showError) window.showError(data.data || '检查失败');
          return;
        }
        if (data.has_children) {
          iSpaceDoc.confirmDeleteWithCaptcha({
            docName: docName,
            totalChildren: data.total_children,
            directChildren: data.direct_children || [],
            csrfToken: csrf
          }).then(function(confirmed) {
            if (confirmed) executeDelete(docId);
          });
        } else {
          iSpaceDoc.confirm('确认删除《' + docName + '》？文档将被移入回收站。', { variant: 'danger' }).then(function(confirmed) {
            if (confirmed) executeDelete(docId);
          });
        }
      })
      .catch(function() {
        if (window.showError) window.showError('网络异常，请重试');
      });
  }

  function executeDelete(docId) {
    var csrf = getCSRF();
    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', csrf);
    fd.append('doc_id', docId);
    fetch('/documents/delete/', { method: 'POST', body: fd })
      .then(function(r) { return r.json(); })
      .then(function(r) {
        if (r.status) {
          var proMatch = window.location.pathname.match(/^\/pages\/(\d+)\//);
          if (proMatch) {
            window.location.href = '/pages/' + proMatch[1] + '/';
          } else {
            window.location.reload();
          }
        } else {
          if (window.showError) window.showError(r.data || '删除失败');
        }
      });
  }

  /* ================================================================
     Init — gear button → dropdown
     ================================================================ */
  function init() {
    document.addEventListener('click', function(e) {
      var gearBtn = e.target.closest('[data-action="doc-settings"]');
      if (gearBtn) {
        e.preventDefault();
        e.stopPropagation();
        var docId = parseInt(gearBtn.getAttribute('data-doc-id'));
        var docName = gearBtn.getAttribute('data-doc-name') || '';
        var canDelete = gearBtn.getAttribute('data-can-delete') !== '0';
        var canManagePermissions = gearBtn.getAttribute('data-can-manage-permissions') !== '0';
        showDropdown(gearBtn, docId, docName, canDelete, canManagePermissions);
        return;
      }

      if (dropdownEl && dropdownEl.style.display === 'block' && !dropdownEl.contains(e.target)) {
        hideDropdown();
      }

      if (modal && e.target.classList.contains('ispace-modal-backdrop') && e.target.closest('#doc-settings-modal')) {
        close();
      }
    });
  }

  /* ================================================================
     Permission Modal
     ================================================================ */
  function open(docId, docName, showDangerTab) {
    currentDocId = docId;
    currentDocName = docName;
    currentTargetType = 'user';
    permissions = [];
    _pendingChanges = {};
    _originalPermissions = [];
    _selectedTargets = {};
    _roleChanged = false;
    _currentIsPublic = true;
    _currentAccessPassword = '';
    ensureModal();
    modal.classList.add('ispace-active');
    document.body.style.overflow = 'hidden';
    loadDocAccess();
    loadPermissions();
    setTargetType('user');
    loadTargetList();
    _updatePendingButton();
  }

  function close() {
    // Warn if unsaved changes
    if (Object.keys(_pendingChanges).length > 0) {
      iSpaceDoc.confirm('您有未保存的权限更改，确定要关闭吗？', { variant: 'warning' }).then(function(confirmed) {
        if (confirmed) {
          _doClose();
        }
      });
    } else {
      _doClose();
    }
  }

  function _doClose() {
    if (modal) modal.classList.remove('ispace-active');
    document.body.style.overflow = '';
    currentDocId = null;
    _roleChanged = false;
    _currentIsPublic = true;
    _currentAccessPassword = '';
    _pendingChanges = {};
    _originalPermissions = [];
    _selectedTargets = {};
  }

  function ensureModal() {
    if (modal) return;
    var container = document.getElementById('ispace-modals-container');
    modal = document.createElement('div');
    modal.className = 'ispace-modal-backdrop';
    modal.id = 'doc-settings-modal';
    modal.innerHTML =
      '<div class="ispace-modal ispace-modal-lg ispace-active" style="max-width:700px;">'
      + '<div class="ispace-modal-header">'
      + '<div class="ispace-modal-title">权限管理</div>'
      + '<button class="ispace-modal-close" onclick="iSpaceDoc.DocSettings.close()">'
      + '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
      + '</button></div>'
      + '<div class="ispace-modal-body" style="padding:0;">'
      // ---- Access Mode Selector ----
      + '<div style="padding:12px 16px;border-bottom:1px solid var(--ispace-color-border-light);">'
      + '<div style="display:flex;gap:8px;">'
      + '<label class="ispace-ds-role-opt" style="display:flex;align-items:center;gap:6px;padding:8px 16px;border:1px solid var(--ispace-color-border-light);border-radius:8px;cursor:pointer;font-size:13px;transition:all 0.15s;">'
      + '<input type="radio" name="ds-access-role" value="public" onchange="iSpaceDoc.DocSettings._onRoleChange()" style="margin:0;"> 公开'
      + '</label>'
      + '<label class="ispace-ds-role-opt" style="display:flex;align-items:center;gap:6px;padding:8px 16px;border:1px solid var(--ispace-color-border-light);border-radius:8px;cursor:pointer;font-size:13px;transition:all 0.15s;">'
      + '<input type="radio" name="ds-access-role" value="password" onchange="iSpaceDoc.DocSettings._onRoleChange()" style="margin:0;"> 密码访问'
      + '</label>'
      + '<label class="ispace-ds-role-opt" style="display:flex;align-items:center;gap:6px;padding:8px 16px;border:1px solid var(--ispace-color-border-light);border-radius:8px;cursor:pointer;font-size:13px;transition:all 0.15s;">'
      + '<input type="radio" name="ds-access-role" value="restricted" onchange="iSpaceDoc.DocSettings._onRoleChange()" style="margin:0;"> 授权访问'
      + '</label>'
      + '</div>'
      + '<div id="ds-pwd-wrap" style="display:none;margin-top:8px;">'
      + '<input type="text" class="ispace-form-input" id="ds-access-pwd" placeholder="输入访问密码" style="max-width:260px;">'
      + '</div>'
      + '</div>'
      // ---- Detail Permission Panel (visible only for 授权访问) ----
      + '<div id="ds-perm-detail" style="display:none;">'
      + '<div id="ds-panel-permission" class="ispace-ds-panel">'
      + '<div class="ispace-ds-perm-layout">'
      + '<div class="ispace-ds-perm-left">'
      + '<div class="ispace-ds-search-wrap">'
      + '<div class="ispace-ds-type-tabs">'
      + '<button class="ispace-ds-type-tab ispace-active" data-type="user" onclick="iSpaceDoc.DocSettings._setTargetType(\'user\')">用户</button>'
      + '<button class="ispace-ds-type-tab" data-type="group" onclick="iSpaceDoc.DocSettings._setTargetType(\'group\')">分组</button>'
      + '<button class="ispace-ds-type-tab" data-type="org" onclick="iSpaceDoc.DocSettings._setTargetType(\'org\')">组织</button>'
      + '</div>'
      + '<input type="text" class="ispace-form-input" id="ds-user-search" placeholder="搜索用户..." oninput="iSpaceDoc.DocSettings._search()">'
      + '</div>'
      + '<div style="padding:4px 8px;font-size:11px;border-bottom:1px solid var(--ispace-color-border-light);">'
      + '<label style="cursor:pointer;display:inline-flex;align-items:center;gap:4px;"><input type="checkbox" id="ds-select-all" onchange="iSpaceDoc.DocSettings._toggleSelectAll(this.checked)" style="margin:0;"> 全选</label>'
      + '<span style="margin-left:8px;color:var(--ispace-color-text-tertiary);">已选 <b id="ds-selected-count">0</b> 项</span>'
      + '</div>'
      + '<div id="ds-search-results" class="ispace-ds-search-results"></div>'
      + '</div>'
      + '<div class="ispace-ds-perm-right">'
      + '<div class="ispace-ds-granted-header">权限级别</div>'
      + '<div id="ds-perm-radios" style="padding:8px 12px;display:flex;flex-direction:column;gap:6px;">'
      + PERM_OPTIONS.map(function(opt, i) {
        return '<label style="display:flex;align-items:center;gap:6px;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:13px;' + (i === 0 ? 'background:var(--ispace-color-primary-light, #e8f0fe);' : '') + '">'
        + '<input type="radio" name="ds-perm-level" value="' + opt.value + '"' + (i === 0 ? ' checked' : '') + ' onchange="iSpaceDoc.DocSettings._onPermRadioChange()"> '
        + opt.label + '</label>';
      }).join('')
      + '</div>'
      + '<div class="ispace-ds-granted-header">已授权 (<span id="ds-granted-count">0</span>)</div>'
      + '<div id="ds-granted-list" class="ispace-ds-granted-list"></div>'
      + '</div>'
      + '</div>'
      + '</div>'
      // ---- Footer ----
      + '<div class="ispace-ds-perm-footer">'
      + '<label class="ispace-ds-checkbox-label">'
      + '<input type="checkbox" id="ds-sync-children" onchange="iSpaceDoc.DocSettings._onSyncChildrenChange()"> 同步到所有子文档'
      + '</label>'
      + '<button class="ispace-btn ispace-btn-primary ispace-btn-sm" id="ds-save-permissions" onclick="iSpaceDoc.DocSettings._saveAll()" style="margin-left:auto;">'
      + '保存更改 (<span id="ds-pending-count">0</span>)'
      + '</button>'
      + '</div>'
      + '</div>'
      + '</div></div>';
    container.appendChild(modal);
  }

  /* ---- Pending changes helpers ---- */
  function _pendingKey(type, id) {
    return type + ':' + id;
  }

  function _updatePendingButton() {
    _updateSaveBtnForSelection();
  }

  /* ---- Load current doc access mode ---- */
  function loadDocAccess() {
    if (!currentDocId) return;
    var csrf = getCSRF();
    fetch('/api/docs/' + currentDocId + '/access/', { headers: { 'X-CSRFToken': csrf } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status !== undefined && data.status) {
          _currentIsPublic = data.is_public;
          _currentAccessPassword = data.access_password || '';
        } else if (data.code === 0 && data.data) {
          _currentIsPublic = data.data.is_public;
          _currentAccessPassword = data.data.access_password || '';
        }
        _updateRoleSelectorUI();
      })
      .catch(function() {});
  }

  function _updateRoleSelectorUI() {
    var mappedRole;
    if (!_currentIsPublic) {
      mappedRole = 'restricted';
    } else if (_currentAccessPassword) {
      mappedRole = 'password';
    } else {
      mappedRole = 'public';
    }
    var radio = document.querySelector('input[name="ds-access-role"][value="' + mappedRole + '"]');
    if (radio) radio.checked = true;
    var pwdWrap = document.getElementById('ds-pwd-wrap');
    if (pwdWrap) {
      pwdWrap.style.display = mappedRole === 'password' ? '' : 'none';
      var pwdInput = document.getElementById('ds-access-pwd');
      if (pwdInput && _currentAccessPassword) pwdInput.value = _currentAccessPassword;
    }
    _toggleDetailPanel(mappedRole);
    _updateRoleHighlight(mappedRole);
  }

  function _onRoleChange() {
    var radio = document.querySelector('input[name="ds-access-role"]:checked');
    if (!radio) return;
    var newMappedRole = radio.value;
    // Determine if role actually changed
    var currentMappedRole = (!_currentIsPublic ? 'restricted' : (_currentAccessPassword ? 'password' : 'public'));
    _roleChanged = newMappedRole !== currentMappedRole;
    var pwdInput = document.getElementById('ds-access-pwd');
    if (newMappedRole === 'password' && pwdInput && pwdInput.value !== _currentAccessPassword) {
      _roleChanged = true;
    } else if (newMappedRole !== 'password' && _currentAccessPassword) {
      _roleChanged = true;
    }
    _toggleDetailPanel(newMappedRole);
    _updateRoleHighlight(newMappedRole);
    // If switching away from restricted and there are unsaved perm changes, warn
    if (newMappedRole !== 'restricted' && (Object.keys(_pendingChanges).length > 0 || Object.keys(_selectedTargets).length > 0)) {
      iSpaceDoc.confirm('切换到非授权访问模式将丢失未保存的权限更改，确定继续吗？', { variant: 'warning' })
        .then(function(ok) {
          if (ok) {
            _pendingChanges = {};
            _selectedTargets = {};
            _updateSelectedCount();
            renderGranted();
          } else {
            var prevRadio = document.querySelector('input[name="ds-access-role"][value="' + currentMappedRole + '"]');
            if (prevRadio) prevRadio.checked = true;
            _toggleDetailPanel(currentMappedRole);
            _updateRoleHighlight(currentMappedRole);
            _roleChanged = false;
            return;
          }
          _updateSaveBtnForSelection();
        });
      return;
    }
    _updateSaveBtnForSelection();
  }

  function _updateRoleHighlight(mappedRole) {
    document.querySelectorAll('.ispace-ds-role-opt').forEach(function(opt) {
      var radio = opt.querySelector('input[name="ds-access-role"]');
      if (radio && radio.value === mappedRole) {
        opt.classList.add('ispace-active');
      } else {
        opt.classList.remove('ispace-active');
      }
    });
  }

  function _toggleDetailPanel(mappedRole) {
    var detail = document.getElementById('ds-perm-detail');
    var pwdWrap = document.getElementById('ds-pwd-wrap');
    if (mappedRole === 'restricted') {
      if (detail) detail.style.display = '';
      if (pwdWrap) pwdWrap.style.display = 'none';
    } else if (mappedRole === 'password') {
      if (detail) detail.style.display = 'none';
      if (pwdWrap) pwdWrap.style.display = '';
    } else {
      if (detail) detail.style.display = 'none';
      if (pwdWrap) pwdWrap.style.display = 'none';
    }
  }

  /* ---- Load granted permissions ---- */
  function loadPermissions() {
    var csrf = getCSRF();
    fetch('/api/docs/' + currentDocId + '/permissions/', { headers: { 'X-CSRFToken': csrf } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var perms = null;
        // Handle both response formats: {status, permissions} and {code, data: {permissions}}
        if (data.status !== undefined) {
          if (data.status) perms = data.permissions;
        } else if (data.code === 0 && data.data && data.data.permissions) {
          perms = data.data.permissions;
        }
        if (perms) {
          permissions = perms;
          _originalPermissions = JSON.parse(JSON.stringify(permissions));
          renderGranted();
        }
      })
      .catch(function() {});
  }

  function renderGranted() {
    // Merge server permissions with pending changes
    var merged = [];
    var seenKeys = {};
    permissions.forEach(function(p) {
      var key = _pendingKey(p.target_type, p.target_id);
      seenKeys[key] = true;
      var change = _pendingChanges[key];
      if (change && change.action === 'revoke') return; // removed
      var perm = JSON.parse(JSON.stringify(p));
      if (change && change.action === 'update') {
        perm.permission = change.permission;
        perm._pending = true;
      }
      merged.push(perm);
    });
    // Add pending grants not yet on server
    Object.keys(_pendingChanges).forEach(function(key) {
      if (!seenKeys[key]) {
        var change = _pendingChanges[key];
        if (change.action === 'grant') {
          merged.push({
            id: null,
            target_type: change.target_type,
            target_id: change.target_id,
            display_name: change.display_name || ('@' + change.target_id),
            permission: change.permission || 'view',
            _pending: true,
            _new: true
          });
        }
      }
    });

    document.getElementById('ds-granted-count').textContent = merged.length;
    _updateSaveBtnForSelection();

    var list = document.getElementById('ds-granted-list');
    if (!merged.length) {
      list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">暂无授权</div>';
      return;
    }

    // Group by target_type
    var groups = { user: [], group: [], org: [] };
    var groupConfig = {
      user: { label: '个人', icon: '👤' },
      group: { label: '分组', icon: '👥' },
      org: { label: '组织', icon: '🏢' },
    };
    merged.forEach(function(p) {
      groups[p.target_type] = groups[p.target_type] || [];
      groups[p.target_type].push(p);
    });

    var html = '';
    Object.keys(groupConfig).forEach(function(type) {
      var items = groups[type];
      if (!items || items.length === 0) return;
      var cfg = groupConfig[type];
      html += '<div class="ispace-ds-granted-group">'
        + '<div class="ispace-ds-granted-group-header">' + cfg.icon + ' ' + cfg.label + ' <span class="ispace-ds-granted-group-count">' + items.length + '</span></div>';
      items.forEach(function(p) {
        var pendingClass = p._pending ? ' ispace-ds-pending-item' : '';
        var pendingBadge = p._pending ? ' <span style="font-size:10px;color:#E67E22;font-weight:600;">待保存</span>' : '';
        var selectAttrs = 'class="ispace-ds-perm-select" style="font-size:12px;padding:2px 4px;border-radius:4px;border:1px solid var(--ispace-color-border);background:var(--ispace-color-bg);color:var(--ispace-color-text-primary);cursor:pointer;"';
        var onChangeHandler = p._new
          ? 'iSpaceDoc.DocSettings._updatePendingPerm(\'' + p.target_type + '\',' + p.target_id + ',this.value)'
          : 'iSpaceDoc.DocSettings._updatePerm(' + (p.id || -1) + ',this.value)';
        html += '<div class="ispace-ds-granted-item' + pendingClass + '">'
          + '<span class="ispace-ds-granted-name"' + (p.target_type === 'user' ? ' data-user-id="' + p.target_id + '"' : '') + '>' + esc(p.display_name) + pendingBadge + '</span>'
          + '<select ' + selectAttrs + ' onchange="' + onChangeHandler + '">'
          + '<option value="view"' + (p.permission === 'view' ? ' selected' : '') + '>仅读</option>'
          + '<option value="edit"' + (p.permission === 'edit' ? ' selected' : '') + '>读写</option>'
          + '<option value="admin"' + (p.permission === 'admin' ? ' selected' : '') + '>管理员</option>'
          + '</select>'
          + '<button class="ispace-ds-remove-btn" onclick="iSpaceDoc.DocSettings._removePerm(' + (p.id || -1) + ',\'' + p.target_type + '\',' + p.target_id + ')" title="移除授权">✕</button>'
          + '</div>';
      });
      html += '</div>';
    });
    list.innerHTML = html;
  }

  /* ---- Target type selector ---- */
  function setTargetType(type) {
    currentTargetType = type;
    var placeholder = type === 'user' ? '搜索用户...' : (type === 'group' ? '搜索分组...' : '搜索组织...');
    var searchInput = document.getElementById('ds-user-search');
    searchInput.placeholder = placeholder;
    searchInput.value = '';
    document.querySelectorAll('#doc-settings-modal .ispace-ds-type-tab').forEach(function(t) {
      t.classList.toggle('ispace-active', t.getAttribute('data-type') === type);
    });
    loadTargetList();
  }

  /* ---- Load initial list for current target type ---- */
  function loadTargetList() {
    var resultsEl = document.getElementById('ds-search-results');
    resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);">加载中...</div>';
    var csrf = getCSRF();
    var url;
    if (currentTargetType === 'user') {
      url = '/api/users/search/';
    } else if (currentTargetType === 'group') {
      url = '/api/groups/search/';
    } else {
      url = '/api/my/organization/';
    }
    fetch(url, { headers: { 'X-CSRFToken': csrf } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (currentTargetType === 'org') {
          var tree = data.tree || [];
          if (!tree.length) {
            resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">暂无组织</div>';
            return;
          }
          resultsEl.innerHTML = renderOrgTree(tree, 0);
          return;
        }
        var items = data.results || data.groups || [];
        if (!items.length) {
          var label = currentTargetType === 'user' ? '用户' : (currentTargetType === 'group' ? '分组' : '组织');
          resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">暂无' + label + '</div>';
          return;
        }
        var html = '';
        if (currentTargetType === 'user') {
          html = renderUserResults(items);
        } else if (currentTargetType === 'group') {
          html = renderGroupResults(items);
        }
        resultsEl.innerHTML = html;
      })
      .catch(function() {
        resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">加载失败</div>';
      });
  }

  /* ---- Search (type-aware) ---- */
  var searchTimer = null;
  function search() {
    clearTimeout(searchTimer);
    var q = document.getElementById('ds-user-search').value.trim();
    var resultsEl = document.getElementById('ds-search-results');
    if (!q || q.length < 1) {
      var label = currentTargetType === 'user' ? '用户' : (currentTargetType === 'group' ? '分组' : '组织');
      resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">输入关键词搜索' + label + '</div>';
      return;
    }
    searchTimer = setTimeout(function() {
      resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);">搜索中...</div>';
      var csrf = getCSRF();
      var url;
      if (currentTargetType === 'user') {
        url = '/api/users/search/?q=' + encodeURIComponent(q);
      } else if (currentTargetType === 'group') {
        url = '/api/groups/search/?q=' + encodeURIComponent(q);
      } else {
        url = '/api/org/nodes/search/?q=' + encodeURIComponent(q);
      }
      fetch(url, { headers: { 'X-CSRFToken': csrf } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          var items = data.results || data.groups || [];
          if (!items.length) {
            resultsEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--ispace-color-text-quaternary);font-size:13px;">未找到匹配结果</div>';
            return;
          }
          var html = '';
          if (currentTargetType === 'user') {
            html = renderUserResults(items);
          } else if (currentTargetType === 'group') {
            html = renderGroupResults(items);
          } else {
            html = renderOrgResults(items);
          }
          resultsEl.innerHTML = html;
        })
        .catch(function() {});
    }, 300);
  }

  function renderUserResults(users) {
    var html = '';
    users.forEach(function(u) {
      var key = _pendingKey('user', u.id);
      var already = permissions.some(function(p) { return p.target_type === 'user' && p.target_id === u.id; });
      var pendingRemoved = _pendingChanges[key] && _pendingChanges[key].action === 'revoke';
      var effectiveAlready = already && !pendingRemoved;
      var checked = !!_selectedTargets[key];
      html += '<label class="ispace-ds-search-item' + (effectiveAlready ? ' ispace-ds-already' : '') + '">'
        + (effectiveAlready
          ? '<span style="width:14px;flex-shrink:0;margin-right:8px;"></span>'
          : '<input type="checkbox" class="ispace-ds-checkbox" value="' + key + '"'
            + (checked ? ' checked' : '')
            + ' onchange="iSpaceDoc.DocSettings._onCheckTarget(\'user\',' + u.id + ',\'' + esc(u.display_name || u.username) + '\',this.checked)"'
            + ' style="margin:0 8px 0 0;flex-shrink:0;">')
        + '<span class="ispace-ds-search-avatar" data-user-id="' + u.id + '" style="background:' + (u.avatar_color || '#4A90D9') + '">' + (u.avatar_url ? '<img src="' + esc(u.avatar_url) + '" alt="">' : (u.avatar_initial || '?')) + '</span>'
        + '<span class="ispace-ds-search-name">' + esc(u.display_name || u.username) + '</span>'
        + '<span class="ispace-ds-search-username">@' + esc(u.username) + '</span>'
        + (effectiveAlready ? '<span style="font-size:11px;color:var(--ispace-color-text-quaternary);">已授权</span>' : '')
        + '</label>';
    });
    return html;
  }

  function renderGroupResults(groups) {
    var html = '';
    groups.forEach(function(g) {
      var key = _pendingKey('group', g.id);
      var already = permissions.some(function(p) { return p.target_type === 'group' && p.target_id === g.id; });
      var pendingRemoved = _pendingChanges[key] && _pendingChanges[key].action === 'revoke';
      var effectiveAlready = already && !pendingRemoved;
      var checked = !!_selectedTargets[key];
      html += '<label class="ispace-ds-search-item' + (effectiveAlready ? ' ispace-ds-already' : '') + '">'
        + (effectiveAlready
          ? '<span style="width:14px;flex-shrink:0;margin-right:8px;"></span>'
          : '<input type="checkbox" class="ispace-ds-checkbox" value="' + key + '"'
            + (checked ? ' checked' : '')
            + ' onchange="iSpaceDoc.DocSettings._onCheckTarget(\'group\',' + g.id + ',\'' + esc(g.name) + '\',this.checked)"'
            + ' style="margin:0 8px 0 0;flex-shrink:0;">')
        + '<span class="ispace-ds-search-avatar" style="background:#27AE60;">' + (g.name || 'G')[0].toUpperCase() + '</span>'
        + '<span class="ispace-ds-search-name">' + esc(g.name) + '</span>'
        + '<span class="ispace-ds-search-username">' + (g.member_count || 0) + ' 人</span>'
        + (effectiveAlready ? '<span style="font-size:11px;color:var(--ispace-color-text-quaternary);">已授权</span>' : '')
        + '</label>';
    });
    return html;
  }

  function _renderOrgItem(n, depth) {
    var key = _pendingKey('org', n.id);
    var already = permissions.some(function(p) { return p.target_type === 'org' && p.target_id === n.id; });
    var pendingRemoved = _pendingChanges[key] && _pendingChanges[key].action === 'revoke';
    var effectiveAlready = already && !pendingRemoved;
    var checked = !!_selectedTargets[key];
    var hasChildren = n.children && n.children.length > 0;
    var indent = depth * 20;
    var html = '';
    html += '<div class="ispace-ds-org-tree-row' + (effectiveAlready ? ' ispace-ds-already' : '') + '" style="padding-left:' + indent + 'px;">';
    if (hasChildren) {
      html += '<span class="ispace-ds-org-toggle" data-org-id="' + n.id + '" onclick="iSpaceDoc.DocSettings._toggleOrgNode(' + n.id + ')">&#9654;</span>';
    } else {
      html += '<span class="ispace-ds-org-toggle" style="visibility:hidden;">&#9654;</span>';
    }
    if (effectiveAlready) {
      html += '<span style="width:14px;flex-shrink:0;margin-right:8px;"></span>';
    } else {
      html += '<input type="checkbox" class="ispace-ds-checkbox" value="' + key + '"'
        + (checked ? ' checked' : '')
        + ' onchange="iSpaceDoc.DocSettings._onCheckTarget(\'org\',' + n.id + ',\'' + esc(n.name) + '\',this.checked)"'
        + ' style="margin:0 8px 0 0;flex-shrink:0;">';
    }
    html += '<span class="ispace-ds-search-avatar" style="background:#E67E22;flex-shrink:0;">' + (n.name || 'O')[0].toUpperCase() + '</span>';
    html += '<span class="ispace-ds-search-name">' + esc(n.name) + '</span>';
    html += '<span class="ispace-ds-search-username" style="flex-shrink:0;">' + (n.member_count || 0) + ' 人</span>';
    if (effectiveAlready) {
      html += '<span style="font-size:11px;color:var(--ispace-color-text-quaternary);flex-shrink:0;">已授权</span>';
    }
    html += '</div>';
    if (hasChildren) {
      html += '<div class="ispace-ds-org-children" id="org-children-' + n.id + '" style="display:none;">';
      n.children.forEach(function(child) {
        html += _renderOrgItem(child, depth + 1);
      });
      html += '</div>';
    }
    return html;
  }

  function renderOrgTree(tree, depth) {
    var html = '';
    tree.forEach(function(n) {
      html += _renderOrgItem(n, depth || 0);
    });
    return html;
  }

  function _toggleOrgNode(nodeId) {
    var container = document.getElementById('org-children-' + nodeId);
    var toggle = document.querySelector('.ispace-ds-org-toggle[data-org-id="' + nodeId + '"]');
    if (!container || !toggle) return;
    var isOpen = container.style.display !== 'none';
    if (isOpen) {
      container.style.display = 'none';
      toggle.innerHTML = '&#9654;';
      toggle.classList.remove('ispace-ds-org-open');
    } else {
      container.style.display = 'block';
      toggle.innerHTML = '&#9660;';
      toggle.classList.add('ispace-ds-org-open');
    }
  }

  function renderOrgSearchResults(nodes) {
    var html = '';
    nodes.forEach(function(n) {
      var key = _pendingKey('org', n.id);
      var already = permissions.some(function(p) { return p.target_type === 'org' && p.target_id === n.id; });
      var pendingRemoved = _pendingChanges[key] && _pendingChanges[key].action === 'revoke';
      var effectiveAlready = already && !pendingRemoved;
      var checked = !!_selectedTargets[key];
      var pathStr = n.path ? n.path.split('/').filter(Boolean).join(' > ') : '';
      html += '<label class="ispace-ds-search-item' + (effectiveAlready ? ' ispace-ds-already' : '') + '">'
        + (effectiveAlready
          ? '<span style="width:14px;flex-shrink:0;margin-right:8px;"></span>'
          : '<input type="checkbox" class="ispace-ds-checkbox" value="' + key + '"'
            + (checked ? ' checked' : '')
            + ' onchange="iSpaceDoc.DocSettings._onCheckTarget(\'org\',' + n.id + ',\'' + esc(n.name) + '\',this.checked)"'
            + ' style="margin:0 8px 0 0;flex-shrink:0;">')
        + '<span class="ispace-ds-search-avatar" style="background:#E67E22;">' + (n.name || 'O')[0].toUpperCase() + '</span>'
        + '<div style="flex:1;min-width:0;">'
        + '<div class="ispace-ds-search-name">' + esc(n.name) + '</div>'
        + (pathStr ? '<div style="font-size:10px;color:var(--ispace-color-text-quaternary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(pathStr) + '</div>' : '')
        + '</div>'
        + '<span class="ispace-ds-search-username">' + (n.member_count || 0) + ' 人</span>'
        + (effectiveAlready ? '<span style="font-size:11px;color:var(--ispace-color-text-quaternary);">已授权</span>' : '')
        + '</label>';
    });
    return html;
  }


  /* ---- Checkbox selection handlers ---- */
  function _onCheckTarget(targetType, targetId, displayName, checked) {
    var key = _pendingKey(targetType, targetId);
    if (checked) {
      _selectedTargets[key] = { target_type: targetType, target_id: targetId, display_name: displayName };
    } else {
      delete _selectedTargets[key];
    }
    _updateSelectedCount();
    _updateSaveBtnForSelection();
    _syncPermRadioFromSelection();
  }

  function _syncPermRadioFromSelection() {
    var selKeys = Object.keys(_selectedTargets);
    if (selKeys.length === 1) {
      // Single item selected — check its existing permission
      var sel = _selectedTargets[selKeys[0]];
      // Check server-side permissions first, then pending changes
      var existing = permissions.find(function(p) {
        return p.target_type === sel.target_type && p.target_id === sel.target_id;
      });
      var change = _pendingChanges[selKeys[0]];
      var permLevel;
      if (change && change.action === 'revoke') {
        permLevel = null; // Was revoked, no current permission
      } else if (change && (change.action === 'grant' || change.action === 'update')) {
        permLevel = change.permission;
      } else if (existing) {
        permLevel = existing.permission;
      }
      if (permLevel) {
        var radio = document.querySelector('input[name="ds-perm-level"][value="' + permLevel + '"]');
        if (radio) radio.checked = true;
      } else {
        // No existing permission — default to first option
        var defaultRadio = document.querySelector('input[name="ds-perm-level"][value="view"]');
        if (defaultRadio) defaultRadio.checked = true;
      }
    } else if (selKeys.length === 0) {
      // No selection — reset to default
      var r = document.querySelector('input[name="ds-perm-level"][value="view"]');
      if (r) r.checked = true;
    }
    // Multiple selections (>1) — keep current radio state unchanged
  }

  function _toggleSelectAll(checked) {
    var checkboxes = document.querySelectorAll('#ds-search-results .ispace-ds-checkbox');
    checkboxes.forEach(function(cb) {
      var label = cb.closest('.ispace-ds-already');
      if (label) return; // skip already-granted items
      if (cb.checked !== checked) {
        cb.checked = checked;
        var parts = cb.value.split(':');
        if (checked) {
          _selectedTargets[cb.value] = { target_type: parts[0], target_id: parseInt(parts[1]), display_name: '' };
        } else {
          delete _selectedTargets[cb.value];
        }
      }
    });
    _updateSelectedCount();
    _updateSaveBtnForSelection();
    _syncPermRadioFromSelection();
  }

  function _onPermRadioChange() {
    _updateSaveBtnForSelection();
  }

  function _onSyncChildrenChange() {
    _syncChildrenDirty = true;
    _updateSaveBtnForSelection();
  }

  function _getSelectedPermLevel() {
    var radio = document.querySelector('input[name="ds-perm-level"]:checked');
    return radio ? radio.value : 'view';
  }

  function _updateSelectedCount() {
    var count = Object.keys(_selectedTargets).length;
    var el = document.getElementById('ds-selected-count');
    if (el) el.textContent = count;
  }

  function _updateSaveBtnForSelection() {
    var selCount = Object.keys(_selectedTargets).length;
    var pendingCount = Object.keys(_pendingChanges).length;
    var count = selCount + pendingCount;
    var hasChanges = count > 0 || _roleChanged || _syncChildrenDirty;
    var btn = document.getElementById('ds-save-permissions');
    if (btn) {
      btn.disabled = !hasChanges;
      btn.textContent = '保存更改 (' + count + ')';
    }
    var countEl = document.getElementById('ds-pending-count');
    if (countEl) countEl.textContent = count;
  }

  /* ---- Update permission level — queue pending change ---- */
  function updatePerm(permId, newLevel) {
    var perm = permissions.find(function(p) { return p.id === permId; });
    if (!perm) return;
    var key = _pendingKey(perm.target_type, perm.target_id);
    if (perm.permission === newLevel) {
      if (_pendingChanges[key]) {
        delete _pendingChanges[key];
      }
    } else {
      _pendingChanges[key] = {
        action: 'update',
        target_type: perm.target_type,
        target_id: perm.target_id,
        permission: newLevel,
        display_name: perm.display_name,
        perm_id: permId
      };
    }
    renderGranted();
  }

  /* ---- Remove permission — queue pending change ---- */
  function removePerm(permId, targetType, targetId) {
    if (permId && permId > 0) {
      var perm = permissions.find(function(p) { return p.id === permId; });
      if (perm) {
        targetType = perm.target_type;
        targetId = perm.target_id;
      }
    }
    var key = _pendingKey(targetType, targetId);
    // Check if it's a new pending grant — just remove from queue
    var change = _pendingChanges[key];
    if (change && change.action === 'grant') {
      delete _pendingChanges[key];
    } else {
      _pendingChanges[key] = {
        action: 'revoke',
        target_type: targetType,
        target_id: targetId,
        permission: null,
        display_name: null,
        perm_id: permId && permId > 0 ? permId : null
      };
    }
    renderGranted();
  }

  /* ---- Update permission for pending (not-yet-saved) new items ---- */
  function _updatePendingPerm(targetType, targetId, newLevel) {
    var key = _pendingKey(targetType, targetId);
    var change = _pendingChanges[key];
    if (change) {
      change.permission = newLevel;
    }
    renderGranted();
  }

  /* ---- Save all pending changes ---- */
  function _saveAll() {
    // First, convert checked items into pending changes using the selected permission level
    var selPerm = _getSelectedPermLevel();
    Object.keys(_selectedTargets).forEach(function(key) {
      var sel = _selectedTargets[key];
      var existing = permissions.find(function(p) { return p.target_type === sel.target_type && p.target_id === sel.target_id; });
      var existingChange = _pendingChanges[key];
      if (existingChange && existingChange.action === 'revoke') {
        // Was marked for revoke, now re-grant
        existingChange.action = existing ? 'update' : 'grant';
        existingChange.permission = selPerm;
      } else if (!existingChange) {
        if (existing && existing.permission === selPerm) return; // no change needed
        _pendingChanges[key] = {
          action: existing ? 'update' : 'grant',
          target_type: sel.target_type,
          target_id: sel.target_id,
          permission: selPerm,
          display_name: sel.display_name,
          perm_id: existing ? existing.id : null
        };
      } else {
        existingChange.permission = selPerm;
      }
    });
    _selectedTargets = {};
    _updateSelectedCount();

    var changes = [];
    var seen = {};
    Object.keys(_pendingChanges).forEach(function(key) {
      var c = _pendingChanges[key];
      var changeKey = c.target_type + ':' + c.target_id + ':' + c.action;
      if (seen[changeKey]) return;
      seen[changeKey] = true;
      changes.push({
        action: c.action,
        target_type: c.target_type,
        target_id: c.target_id,
        permission: c.permission,
        perm_id: c.perm_id
      });
    });
    // 如果只变更了"同步到所有子文档"复选框，将现有权限也加入提交
    if (_syncChildrenDirty && !changes.length) {
      permissions.forEach(function(p) {
        if (p._new || p._pending) return;
        var key = p.target_type + ':' + p.target_id + ':update';
        if (seen[key]) return;
        seen[key] = true;
        changes.push({
          action: 'update',
          target_type: p.target_type,
          target_id: p.target_id,
          permission: p.permission,
          perm_id: p.id
        });
      });
    }

    if (!changes.length && !_roleChanged && !_syncChildrenDirty) return;

    var btn = document.getElementById('ds-save-permissions');
    if (btn) { btn.disabled = true; btn.textContent = '保存中...'; }

    var csrf = getCSRF();
    var syncChildren = document.getElementById('ds-sync-children').checked;

    // Build permission change promises
    var promises = changes.map(function(c) {
      if (c.action === 'revoke' && c.perm_id) {
        return fetch('/api/docs/' + currentDocId + '/permissions/revoke/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ permission_id: c.perm_id })
        }).then(function(r) { return r.json(); });
      } else {
        return fetch('/api/docs/' + currentDocId + '/permissions/grant/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ target_type: c.target_type, target_id: c.target_id, permission: c.permission || 'view', apply_to_children: syncChildren })
        }).then(function(r) { return r.json(); });
      }
    });

    // Build access mode save promise if role changed
    var accessPromise = null;
    var newIsPublic, newPassword;
    if (_roleChanged) {
      var radio = document.querySelector('input[name="ds-access-role"]:checked');
      var newRole = radio ? radio.value : 'public';
      newIsPublic = newRole !== 'restricted';
      var pwdInput = document.getElementById('ds-access-pwd');
      newPassword = newRole === 'password' ? (pwdInput ? pwdInput.value.trim() : '') : '';
      accessPromise = fetch('/api/docs/' + currentDocId + '/access/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ is_public: newIsPublic, access_password: newPassword })
      }).then(function(r) { return r.json(); });
    }

    var allPromises = promises.slice();
    if (accessPromise) allPromises.push(accessPromise);

    Promise.all(allPromises)
      .then(function(results) {
        var permResults = results.slice(0, promises.length);
        var accessResult = accessPromise ? results[results.length - 1] : null;
        var successCount = permResults.filter(function(r) { return r.status || r.code === 0; }).length;
        var failCount = permResults.length - successCount;
        var accessOk = !accessResult || accessResult.status || accessResult.code === 0;

        _pendingChanges = {};
        _roleChanged = false;
        _syncChildrenDirty = false;
        if (accessResult && accessOk) {
          _currentIsPublic = newIsPublic;
          _currentAccessPassword = newPassword;
        }
        _updateSaveBtnForSelection();
        loadPermissions();

        var msg = '';
        if (permResults.length > 0) {
          if (failCount === 0) {
            msg += '已保存 ' + successCount + ' 项权限更改';
          } else {
            msg += '保存完成：' + successCount + ' 成功，' + failCount + ' 失败';
          }
        }
        if (accessResult) {
          if (msg) msg += '，';
          msg += accessOk ? '访问模式已更新' : '访问模式保存失败';
        }
        if (msg) {
          if (failCount === 0 && accessOk) {
            if (window.showSuccess) window.showSuccess(msg);
          } else {
            if (window.showError) window.showError(msg);
          }
        }
        // Restore save button after success
        if (btn) { btn.disabled = false; btn.textContent = '保存更改'; }
        var currentMapped = (!_currentIsPublic ? 'restricted' : (_currentAccessPassword ? 'password' : 'public'));
        _updateRoleHighlight(currentMapped);
      })
      .catch(function() {
        if (btn) { btn.disabled = false; btn.textContent = '保存更改'; }
        if (window.showError) window.showError('保存失败，请重试');
      });
  }

  /* ---- Trigger delete from dropdown ---- */
  function triggerDelete() {
    close();
    triggerDeleteFlow(currentDocId, currentDocName);
  }

  /* ---- Helpers ---- */
  function getCSRF() {
    return (window.__ISPACEDOC__ && window.__ISPACEDOC__.csrfToken) || '';
  }

  function esc(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    open: open,
    close: close,
    _setTargetType: setTargetType,
    _search: search,
    _onCheckTarget: _onCheckTarget,
    _toggleSelectAll: _toggleSelectAll,
    _onPermRadioChange: _onPermRadioChange,
    _onSyncChildrenChange: _onSyncChildrenChange,
    _onRoleChange: _onRoleChange,
    _syncPermRadioFromSelection: _syncPermRadioFromSelection,
    _updatePerm: updatePerm,
    _updatePendingPerm: _updatePendingPerm,
    _removePerm: removePerm,
    _toggleOrgNode: _toggleOrgNode,
    _saveAll: _saveAll,
    _triggerDelete: triggerDelete,
  };
})();
