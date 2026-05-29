# 企业微信认证与同步

企业微信集成包含三部分能力：QR 扫码登录、自建应用免登、组织架构与用户同步。

## 前置条件

1. 拥有企业微信管理员权限
2. 在 [企业微信管理后台](https://work.weixin.qq.com/) 创建自建应用
3. 配置可信域名

## 一、配置

### config.ini

```ini
[auth.wecom]
enabled = true
corp_id = ww1234567890abcdef
corp_secret = your_corp_secret_from_admin
agent_id = 1000002
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `corp_id` | 是 | 企业微信 CorpID（在"我的企业" → "企业信息"中查看） |
| `corp_secret` | 是 | 自建应用的 Secret（在应用详情页查看） |
| `agent_id` | 否 | 自建应用的 AgentId（免登认证时需要） |

### 企业微信管理后台配置

1. **可信域名** — 应用管理 → 自建应用 → 网页授权及 JS-SDK → 设置可信域名
2. **授权回调域** — 同上页面，填写部署域名（不含协议和路径）

## 二、QR 扫码登录

用户在登录页点击"企业微信登录"，系统构造企业微信 OAuth 授权 URL：

```
https://open.work.weixin.qq.com/wwopen/sso/qrConnect
  ?appid=<corp_id>
  &agentid=<agent_id>
  &redirect_uri=https://<domain>/auth/wecom/callback/
  &state=<random_state>
```

回调后系统用 code 换取 userid 和用户信息，完成登录。

## 三、自建应用免登

企业微信工作台中的应用入口可配置为免登跳转，用户点击后无需扫码直接进入系统。

### 工作台配置

在应用管理 → 自建应用 → 工作台应用主页，设置：

```
https://<domain>/auth/wecom/sso/
```

### 免登流程

1. 用户在企业微信工作台点击应用
2. 企业微信携带 code 参数跳转到 `/auth/wecom/sso/?code=xxx`
3. `oauth_sso` 视图调用 `WeComAuthBackend.authenticate_sso()` 获取用户信息
4. 获取 userid 后调用 `/cgi-bin/user/get` 获取用户详情
5. 创建或匹配本地用户，Django login() 建立会话
6. 重定向到首页

### 与 QR 登录的区别

- QR 登录使用 `/cgi-bin/auth/getuserinfo`（无需应用可见范围）
- 免登使用 OAuth 2.0 授权码流程（用户在应用可见范围内才可获取）

## 四、组织架构同步

将企业微信通讯录的部门和成员同步至本地 `OrgNode` / `OrgUser` / `User`。

### 触发方式

**方式一：管理后台按钮**

`/admin/system/auth/` → 企业微信卡片 → 点击"同步"

**方式二：管理命令**

```bash
python manage.py sync_wecom_contacts
python manage.py sync_wecom_contacts --dry-run   # 预览不写入
python manage.py sync_wecom_contacts --corp-id=xxx --corp-secret=xxx
```

**方式三：API 调用**

```bash
curl -X POST https://<domain>/api/sync/wecom/trigger/ \
  -b cookies.txt -H 'X-CSRFToken: <token>'
```

查询同步状态：

```bash
curl https://<domain>/api/sync/wecom/status/
```

### 字段映射

| 企业微信字段 | i·Space Doc 模型 | i·Space Doc 字段 |
|-------------|---------------|---------------|
| 部门 id | OrgNode | `external_id` |
| 部门 name | OrgNode | `name` |
| 部门 parentid | OrgNode | `parent`（通过 external_id 关联） |
| 部门 order | OrgNode | `sort_order` |
| 成员 userid | UserProfile | `wecom_userid` |
| 成员 name | User | `last_name` |
| 成员 email | User | `email` |
| 成员 mobile | UserProfile | `phone` |
| 成员 department | OrgUser | `org_node` 关联 |
| 成员 position | 待扩展 | — |

### 同步策略

- **部门** — 全量同步，不在远端列表中的本地部门删除
- **用户** — 新建或更新（邮箱、姓名），已在本地但不在远端的用户停用
- **组织关联** — 按部门 ID 重新计算 OrgUser 关系

### 定时同步（生产环境推荐）

通过 cron 定时执行管理命令：

```cron
# 每天凌晨 2:00 同步企业微信通讯录
0 2 * * * cd /path/to/ispace && python manage.py sync_wecom_contacts >> /var/log/ispace/sync.log 2>&1
```
