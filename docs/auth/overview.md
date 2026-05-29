# 认证体系总览

i·Space Doc 支持多种企业级认证方式，统一通过 `config.ini` 配置管理，登录页自动展示已启用的认证入口。

## 支持的认证方式

| 认证方式 | 类型 | 说明 |
|----------|------|------|
| 本地密码 | 表单 | Django 默认用户名 + 密码登录 |
| OIDC | OAuth 2.0 重定向 | 支持 Keycloak / Auth0 / Azure AD / Okta 等标准 OIDC IdP |
| 企业微信 | OAuth 2.0 重定向 | QR 扫码登录 + 自建应用免登 |
| LDAP | 表单 | 用户名密码登录，支持搜索模式和直接绑定模式 |
| 钉钉 | OAuth 2.0 重定向 | 钉钉扫码登录 + 自建应用免登 |

## 架构

```
登录页 (/login)
    │
    ├── 本地密码表单 → Django auth.authenticate()
    │
    └── OAuth 按钮区
        │  fetch /auth/providers/ → 根据 config.ini 返回已启用列表
        │
        ├── redirect 类型 (OIDC/WeCom/DingTalk)
        │   → /auth/<provider>/login/ → 跳转 IdP → /auth/<provider>/callback/ → 登录
        │
        └── form 类型 (LDAP)
            → 弹出用户名密码表单 → POST /auth/<provider>/login/form/ → 登录
```

### 后端架构

```
backend/apps/doc/auth/
├── base.py          AuthBackend 抽象基类，定义 get_authorize_url / authenticate 接口
├── config.py        从 config.ini 读取配置，构建后端实例
├── views.py         统一 OAuth 视图（login / callback / sso / bind / providers）
├── urls.py          路由定义
├── oidc.py          OIDC 认证后端
├── wecom.py         企业微信认证后端
├── ldap.py          LDAP 认证后端
├── dingtalk.py      钉钉认证后端
└── adapter.py       用户创建/绑定适配器

backend/apps/doc/sync/
├── base.py          DirectorySyncBackend 抽象基类
├── wecom.py         企业微信通讯录同步
├── ldap.py          LDAP 目录同步
├── views.py         同步触发 API
└── urls.py          同步路由
```

## 配置方式

所有认证后端通过 `config/conf/config.ini` 配置。配置对应的 `[auth.<provider>]` section 即视为启用，移除 section 即禁用。

`enabled` 字段支持在不丢失配置的情况下临时关闭某个后端：

```ini
[auth.wecom]
enabled = true
corp_id = xxx
...

[auth.ldap]
enabled = false
server_uri = ldap://...
```

管理后台（`/admin/system/auth/`）提供完整的可视化配置界面，包括配置编辑、启用/禁用开关、连接测试和通讯录同步触发。

## 用户绑定

OAuth 登录用户通过 `IspOAuthBinding` 模型记录绑定关系：

- `provider` — 认证后端标识
- `provider_user_id` — 第三方用户唯一 ID
- `provider_user_name` — 第三方用户名
- `bound_at` — 绑定时间

登录时优先通过邮箱匹配已有用户，其次用户名匹配，最后自动创建新用户。

## 目录同步

企业微信和 LDAP 支持将远端通讯录同步至本地 `OrgNode` / `OrgUser` / `User` 模型：

- **企业微信** — API 拉取部门列表和成员列表，同步含组织架构
- **LDAP** — 搜索组织单位 (OU) 和用户条目，同步至本地

同步可通过管理后台按钮手动触发，或通过管理命令（`sync_wecom_contacts` / `sync_ldap`）在 cron 中定时执行。
