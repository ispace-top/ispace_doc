# LDAP 认证与同步

LDAP (Lightweight Directory Access Protocol) 是企业常用的目录服务协议。i·Space Doc 支持 LDAP 用户名密码认证和目录同步。

## 一、配置

### config.ini

```ini
[auth.ldap]
enabled = true
server_uri = ldap://ldap.example.com:389
bind_dn = cn=admin,dc=example,dc=com
bind_password = admin_password
user_base_dn = ou=users,dc=example,dc=com
user_filter = (uid=%(user)s)
username_attr = uid
email_attr = mail
use_tls = false

# 目录同步时使用的组织单位配置（可选）
org_base_dn = ou=groups,dc=example,dc=com
org_filter = (objectClass=organizationalUnit)
org_name_attr = ou
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `server_uri` | 是 | LDAP 服务器地址，如 `ldap://ldap.example.com:389` 或 `ldaps://...:636` |
| `bind_dn` | 搜索模式必填 | 管理员绑定 DN，用于搜索用户 |
| `bind_password` | 搜索模式必填 | 管理员绑定密码 |
| `user_base_dn` | 搜索模式必填 | 用户搜索基准 DN |
| `user_filter` | 否 | 用户搜索过滤器，`%(user)s` 会被替换为登录用户名，默认 `(uid=%(user)s)` |
| `username_attr` | 否 | 用户名属性名，默认 `uid` |
| `email_attr` | 否 | 邮箱属性名，默认 `mail` |
| `use_tls` | 否 | 是否启用 StartTLS，默认 `false` |
| `org_base_dn` | 否 | 组织单位搜索基准 DN（仅用于目录同步） |
| `org_filter` | 否 | 组织单位过滤器，默认 `(objectClass=organizationalUnit)` |
| `org_name_attr` | 否 | 组织单位名称属性，默认 `ou` |

## 二、认证模式

### 搜索模式（推荐）

配置 `bind_dn` + `user_base_dn`，认证流程：

1. 使用管理员 DN 绑定 LDAP
2. 用 `user_filter` 搜索目标用户 DN
3. 使用目标用户 DN 和输入的密码重新绑定，验证凭据

```ini
[auth.ldap]
server_uri = ldap://ldap.example.com:389
bind_dn = cn=admin,dc=example,dc=com
bind_password = admin_password
user_base_dn = ou=users,dc=example,dc=com
user_filter = (uid=%(user)s)
```

### 直接绑定模式

不配置 `bind_dn` 和 `user_base_dn`，直接使用用户 DN 模板绑定：

```ini
[auth.ldap]
server_uri = ldap://ldap.example.com:389
bind_dn = uid=%(user)s,ou=users,dc=example,dc=com
bind_password =
```

`%(user)s` 会被替换为登录用户名。

## 三、登录流程

1. 用户在登录页点击 "LDAP 登录"
2. 弹出 LDAP 用户名密码表单（与 OAuth 重定向流程不同）
3. 表单提交到 `POST /auth/ldap/login/form/`
4. 后端调用 `LDAPAuthBackend.authenticate()` 验证凭据
5. 验证通过后查找或创建本地用户，Django login() 建立会话

## 四、目录同步

从 LDAP 拉取组织单位 (OU) 和用户，同步至本地 `OrgNode` / `OrgUser` / `User`。

### 触发方式

**方式一：管理后台按钮**

`/admin/system/auth/` → LDAP 卡片 → 点击"同步"

**方式二：管理命令**

```bash
python manage.py sync_ldap
python manage.py sync_ldap --dry-run   # 预览不写入
python manage.py sync_ldap --full       # 全量更新
```

**方式三：API 调用**

```bash
curl -X POST https://<domain>/api/sync/ldap/trigger/ \
  -b cookies.txt -H 'X-CSRFToken: <token>'
```

查询同步状态：

```bash
curl https://<domain>/api/sync/ldap/status/
```

### 字段映射

| LDAP 属性 | i·Space Doc 模型 | i·Space Doc 字段 |
|-----------|---------------|---------------|
| DN | OrgNode | `external_id` |
| `ou` / `org_name_attr` | OrgNode | `name` |
| DN parent | OrgNode | `parent` |
| `uid` / `username_attr` | User | `username` |
| `mail` / `email_attr` | User | `email` |
| `displayName` / `cn` | User | `first_name` |
| `ou` / `department` | OrgUser | 组织关联 |
| `title` | 待扩展 | 职位 |

### 同步策略

- **部门** — 从 LDAP 搜索 OU 条目，全量同步
- **用户** — 从 `user_base_dn` 搜索用户条目，新建或更新
- **组织关联** — 通过用户的 `department` 或 `ou` 属性匹配已同步的 OrgNode，建立 OrgUser 关联

### 定时同步（生产环境推荐）

```cron
# 每天凌晨 3:00 同步 LDAP
0 3 * * * cd /path/to/ispace && python manage.py sync_ldap >> /var/log/ispace/sync.log 2>&1
```

## 五、测试连接

在管理后台 LDAP 卡片点击"测试连接"，系统会尝试绑定 LDAP 服务器并验证凭据，返回连接结果。
