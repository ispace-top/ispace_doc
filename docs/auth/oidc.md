# OIDC 认证接入

OIDC (OpenID Connect) 是基于 OAuth 2.0 的身份认证协议。i·Space Doc 支持接入任意标准 OIDC IdP（Identity Provider）。

## 支持的 IdP

已验证兼容以下平台：

- **Keycloak** — 开源身份认证平台
- **Auth0** — 托管身份认证服务
- **Azure AD** — 微软企业身份认证
- **Okta** — 企业级身份认证平台

## 配置说明

### config.ini 配置

```ini
[auth.oidc]
enabled = true
provider_name = Keycloak
client_id = ispace-doc
client_secret = your_client_secret
scope = openid profile email

# 方式一：Discovery URL（推荐，自动获取端点）
discovery_url = https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration

# 方式二：手动指定端点（discovery_url 为空时使用）
# authorize_url = https://idp.example.com/authorize
# token_url = https://idp.example.com/token
# userinfo_url = https://idp.example.com/userinfo
# logout_url = https://idp.example.com/logout
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `provider_name` | 否 | 显示名称，默认 "OIDC" |
| `discovery_url` | 推荐 | OIDC Discovery 端点，程序自动获取 authorize/token/userinfo 端点 |
| `client_id` | 是 | OAuth 客户端 ID |
| `client_secret` | 是 | OAuth 客户端密钥 |
| `scope` | 否 | 授权范围，默认 `openid profile email` |
| `authorize_url` | 否 | 手动指定授权端点（discovery_url 为空时使用） |
| `token_url` | 否 | 手动指定 Token 端点 |
| `userinfo_url` | 否 | 手动指定用户信息端点 |
| `logout_url` | 否 | 手动指定登出端点 |

### 各平台配置示例

#### Keycloak

1. 在 Keycloak 管理后台创建 Client，类型为 `openid-connect`
2. 设置 `Valid Redirect URIs` 为 `https://your-domain.com/auth/oidc/callback/`
3. 获取 Client ID 和 Client Secret
4. Discovery URL 格式：`https://<keycloak-host>/realms/<realm>/.well-known/openid-configuration`

#### Auth0

1. 在 Auth0 Dashboard 创建 Application，类型为 `Regular Web Application`
2. 设置 `Allowed Callback URLs` 为 `https://your-domain.com/auth/oidc/callback/`
3. Discovery URL 格式：`https://<tenant>.auth0.com/.well-known/openid-configuration`

#### Azure AD

1. 在 Azure Portal 注册应用
2. 设置 Redirect URI 为 `https://your-domain.com/auth/oidc/callback/`
3. 使用 v2.0 端点，手动指定：
   ```ini
   authorize_url = https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize
   token_url = https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
   userinfo_url = https://graph.microsoft.com/oidc/userinfo
   ```

## 用户属性映射

OIDC userinfo 返回的字段映射规则：

| OIDC claim | i·Space Doc 字段 |
|------------|----------------|
| `sub` | `provider_uid`（格式：`oidc:<sub>`） |
| `preferred_username` | `username` |
| `nickname` / `name` | `nickname` |
| `email` | `email` |
| `picture` | `avatar_url` |

## 登录流程

1. 用户在登录页点击 "OIDC 登录"
2. 重定向到 IdP 登录页面
3. 用户输入凭据并授权
4. IdP 回调 `/auth/oidc/callback/?code=xxx&state=xxx`
5. i·Space Doc 用 code 换取 access_token + userinfo
6. 查找或创建本地用户，Django login() 建立会话
7. 重定向到首页

## 测试连接

在管理后台 "认证配置" 页面，配置 OIDC 后点击 "测试连接"，系统会请求 Discovery 端点并显示 Issuer 和端点信息。
