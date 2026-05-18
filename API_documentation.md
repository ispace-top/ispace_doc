# iSpaceDoc 前后端交互接口文档

本文档旨在详细说明 iSpaceDoc 项目的前后端交互接口，为前端重构和后续开发提供依据。

项目中的接口主要分为三类：
1.  **管理后台REST API** (`/admin/api/`)：基于 Django Rest Framework (DRF)，用于后台管理功能，仅限超级管理员访问。
2.  **核心交互AJAX API** (`backend.apps.doc`)：基于Django的普通视图，通过返回 `JsonResponse` 实现前端的动态交互，如文档编辑、项目管理等。这类接口通常需要用户登录（Session认证）。
3.  **通用REST API** (`/api/`)：基于Token认证的接口，为客户端或第三方应用提供数据交互能力。

---

## 第一部分: 管理后台 REST API

这类接口位于 `/admin/` 路径下，通用要求如下：

*   **认证**: 支持Session认证（浏览器后台）和Token认证 (`?token=...` 查询参数)。
*   **权限**: **超级管理员 (Superuser)**。

### 1.1 用户管理

#### 1.1.1 获取用户列表

*   **Path**: `GET /admin/api/users`
*   **描述**: 获取系统中的用户列表，支持分页和筛选。
*   **请求参数**:
    *   `page` (number, optional): 页码。
    *   `limit` (number, optional): 每页数量。
    *   `username` (string, optional): 按用户名筛选。
*   **成功响应 (200 OK)**:
    ```json
    {
        "code": 0,
        "data": [
            {
                "id": 1,
                "last_login": "2023-10-27T10:00:00Z",
                "is_superuser": true,
                "username": "admin",
                "email": "admin@example.com",
                "date_joined": "2023-10-27T09:00:00Z",
                "is_active": true,
                "first_name": "Admin"
            }
        ],
        "count": 1
    }
    ```

#### 1.1.2 新增用户

*   **Path**: `POST /admin/api/users`
*   **描述**: 创建一个新用户。
*   **请求体 (JSON)**:
    *   `username` (string, required): 用户名。
    *   `email` (string, required): 电子邮箱。
    *   `password` (string, required): 密码。
    *   `user_type` (number, optional): 用户类型，`0` 为普通用户，`1` 为管理员。
*   **成功响应 (200 OK)**:
    ```json
    { "code": 0 }
    ```

#### 1.1.3 获取/修改/删除单个用户

*   **Path**: `/admin/api/user/<int:id>`
*   **描述**: 对指定ID的用户进行操作。
*   **方法**:
    *   `GET`: 获取用户详情。
    *   `PUT`: 修改用户信息。
    *   `DELETE`: 删除用户。
*   **PUT 请求体 (JSON)**:
    *   修改资料: `{"obj": "info", "username": "...", "nickname": "...", "email": "...", "is_active": "on", "is_superuser": "true"}`
    *   修改密码: `{"obj": "pwd", "password": "...", "password2": "..."}`
*   **成功响应 (200 OK)**:
    *   GET: `{"code": 0, "data": { ...user_details... }}`
    *   PUT/DELETE: `{"code": 0, "data": "操作成功"}`

---

### 1.2 资源管理 (图片、附件、注册码等)

#### 1.2.1 图片列表

*   **Path**: `GET /admin/api/imgs/`
*   **描述**: 获取图片列表，支持分页和筛选。
*   **请求参数**: `page`, `limit`, `kw` (关键词), `username`, `mode` ('scan' 查找未使用图片)。
*   **成功响应 (200 OK)**: `{"code": 0, "data": [ ...ImageSerializer... ], "count": ...}`

#### 1.2.2 删除图片

*   **Path**: `DELETE /admin/api/imgs/` (批量) 或 `DELETE /admin/api/img/<int:id>/` (单个)
*   **描述**: 删除图片。
*   **批量删除请求体 (JSON)**: `{"id": "1,2,3"}`
*   **成功响应 (200 OK)**: `{"code": 0, "data": "删除成功"}`

#### 1.2.3 附件列表

*   **Path**: `GET /admin/api/attachments/`
*   **描述**: 获取附件列表。
*   **请求参数**: `page`, `limit`, `kw`, `username`.
*   **成功响应 (200 OK)**: `{"code": 0, "data": [ ...AttachmentSerializer... ], "count": ...}`

#### 1.2.4 删除附件

*   **Path**: `DELETE /admin/api/attachments/` (批量) 或 `DELETE /admin/api/attachment/<int:id>/` (单个)
*   **描述**: 删除附件。
*   **批量删除请求体 (JSON)**: `{"id": "1,2,3"}`
*   **成功响应 (200 OK)**: `{"code": 0, "data": "删除成功"}`

---
## 第二部分: 核心交互 AJAX API

这类接口是项目的主要交互方式，通用要求如下：

*   **认证**: **用户需登录 (Session-based)**。通过 `@login_required` 装饰器实现。
*   **请求格式**: 通常为 `application/x-www-form-urlencoded` (表单提交)。
*   **响应格式**: `JsonResponse`，通常包含 `status` (boolean) 和 `data` 字段。

### 2.1 文集 (Project) 操作

#### 2.1.1 创建文集

*   **Path**: `POST /create_project/`
*   **描述**: 创建一个新的文集。
*   **请求体 (Form-data)**:
    *   `pname` (string, required): 文集名称。
    *   `picon` (string, optional): 图标URL。
    *   `desc` (string, optional): 简介。
    *   `role` (number, optional): 权限, `0`公开, `1`私密, `2`指定用户, `3`访问码。
*   **成功响应 (200 OK)**: `{"status": true, "data": {"id": ..., "name": "...", "role": ...}}`

#### 2.1.2 修改文集

*   **Path**: `POST /modify_pro/`
*   **描述**: 修改文集基本信息。
*   **权限**: 文集创建者或超级管理员。
*   **请求体 (Form-data)**: `pro_id`, `name`, `picon`, `desc`, `is_watermark`, `watermark_value`。
*   **成功响应 (200 OK)**: `{"status": true, "data": "修改成功"}`

#### 2.1.3 删除文集

*   **Path**: `POST /del_project/`
*   **描述**: 删除一个或多个文集。
*   **权限**: 文集创建者或超级管理员。
*   **请求体 (Form-data)**:
    *   `pro_id` (string, required): 单个ID或逗号分隔的ID列表。
    *   `range` (string, optional): `single` (默认) 或 `multi`。
*   **成功响应 (200 OK)**: `{"status": true}`

#### 2.1.4 获取文集文档树

*   **Path**: `POST /get_pro_doc_tree/`
*   **描述**: 获取文集的层级式文档结构。
*   **请求体 (Form-data)**: `pro_id` (required)。
*   **成功响应 (200 OK)**: `{"status": true, "data": [ ...tree_structure... ]}`

---

### 2.2 文档 (Doc) 操作

#### 2.2.1 创建文档

*   **Path**: `POST /create_doc/`
*   **描述**: 创建一篇新文档。
*   **权限**: 文集创建者或协作者。
*   **请求体 (Form-data)**:
    *   `project` (number, required): 所属文集ID。
    *   `doc_name` (string, required): 文档标题。
    *   `parent_doc` (number, optional): 上级文档ID。
    *   `content` (string, optional): HTML内容。
    *   `pre_content` (string, optional): Markdown内容。
    *   `editor_mode` (number, optional): 编辑器模式。
    *   `status` (number, optional): `1`为发布, `0`为草稿。
*   **成功响应 (200 OK)**: `{"status": true, "data": {"pro": ..., "doc": ...}}`

#### 2.2.2 修改文档

*   **Path**: `POST /modify_doc/<int:doc_id>/`
*   **描述**: 修改一篇已存在的文档。
*   **权限**: 文档创建者、文集创建者或高级协作者。
*   **请求体 (Form-data)**: 同创建文档，但`doc_id`在URL中。
*   **成功响应 (200 OK)**: `{"status": true, "data": "修改成功"}`

#### 2.2.3 删除文档 (软删除)

*   **Path**: `POST /del_doc/`
*   **描述**: 将文档移入回收站 (`status=3`)。
*   **权限**: 文档创建者、文集创建者、高级协作者或超级管理员。
*   **请求体 (Form-data)**:
    *   `doc_id` (string, required): 单个ID或逗号分隔的ID列表。
    *   `range` (string, optional): `single` (默认) 或 `multi`。
*   **成功响应 (200 OK)**: `{"status": true, "data": "删除完成"}`

---

### 2.3 文件上传

#### 2.3.1 编辑器图片上传

*   **Path**: `POST /upload_doc_img/`
*   **描述**: 通用图片上传接口，供editormd编辑器使用。
*   **请求体**: `multipart/form-data` (包含 `editormd-image-file` 文件), 或 Base64 字符串, 或远程URL。
*   **成功响应 (200 OK)**: `{"success": 1, "url": "image_url", "message": "..."}`

#### 2.3.2 导入本地文档

*   **Path**: `POST /api/import_local_doc/`
*   **描述**: 上传本地 `.md`, `.txt`, `.docx` 文件并创建为草稿。
*   **请求体 (`multipart/form-data`)**:
    *   `project` (number, required): 目标文集ID。
    *   `local_doc` (file, required): 文档文件。
*   **成功响应 (200 OK)**: `{"code": 0, "data": {"doc_id": ..., "doc_name": ...}}`

---

## 第三部分: 通用 REST API

这类接口位于 `/api/` 路径下，通用要求如下：

*   **认证**: **Token认证**。所有请求都需要在URL中附加 `?token=<USER_TOKEN>`。
*   **响应格式**: `JsonResponse`，包含 `status` (boolean) 和 `data` 字段。

### 3.1 认证与Token

#### 3.1.1 获取服务器时间戳

*   **Path**: `GET /api/get_timestamp/`
*   **描述**: 获取服务器时间戳，用于 `oauth0` 登录验证。
*   **成功响应 (200 OK)**: `{"status": true, "data": "timestamp_string"}`

#### 3.1.2 验证Token

*   **Path**: `GET /api/check_token/`
*   **描述**: 检查一个Token是否有效。
*   **请求参数**: `token` (string, required)。
*   **成功响应 (200 OK)**: `{"status": true, "data": {"is_writer": ..., "username": ..., "user_type": ...}}`

---

### 3.2 数据获取

#### 3.2.1 获取文集列表

*   **Path**: `GET /api/get_projects/`
*   **描述**: 获取Token对应用户可见的文集列表。
*   **请求参数**:
    *   `token` (string, required)
    *   `filter_name` (string, optional): `self`, `colla` 或 all。
    *   `kw` (string, optional): 搜索关键词。
*   **成功响应 (200 OK)**: `{"status": true, "data": [ ...project_list... ]}`

#### 3.2.2 获取文集层级文档列表

*   **Path**: `GET /api/get_level_docs/`
*   **描述**: 获取一个文集的所有文档，并按层级结构组织。
*   **请求参数**:
    *   `token` (string, required)
    *   `pid` (number, required): 文集ID。
*   **成功响应 (200 OK)**: `{"status": true, "data": [ ...hierarchical_doc_list... ], "total": ...}`

#### 3.2.3 获取单个文档

*   **Path**: `GET /api/get_doc/`
*   **描述**: 获取一篇文档的完整内容（包括Markdown原文）。
*   **请求参数**:
    *   `token` (string, required)
    *   `did` (number, required): 文档ID。
*   **成功响应 (200 OK)**: `{"status": true, "data": { ...doc_details_with_content... }}`

---

### 3.3 数据操作

#### 3.3.1 创建文集

*   **Path**: `POST /api/create_project/`
*   **描述**: 创建一个新文集。
*   **请求参数**: `token` (string, required)。
*   **请求体 (JSON or Form-data)**:
    *   `name` (string, required): 文集名称。
    *   `desc` (string, optional): 简介。
    *   `role` (number, optional): 权限。
*   **成功响应 (200 OK)**: `{"status": true, "data": new_project_id}`

#### 3.3.2 创建文档

*   **Path**: `POST /api/create_doc/`
*   **描述**: 创建一篇新文档。
*   **请求参数**: `token` (string, required)。
*   **请求体 (JSON or Form-data)**:
    *   `pid` (number, required): 所属文集ID。
    *   `title` (string, required): 文档标题。
    *   `doc` (string, required): 文档内容。
*   **成功响应 (200 OK)**: `{"status": true, "data": new_doc_id}`

#### 3.3.3 修改文档

*   **Path**: `POST /api/modify_doc/`
*   **描述**: 修改一篇已存在的文档。
*   **请求参数**: `token` (string, required)。
*   **请求体 (JSON or Form-data)**:
    *   `did` (number, required): 文档ID。
    *   `pid` (number, required): 所属文集ID。
    *   `title` (string, required): 新标题。
    *   `doc` (string, required): 新内容。
*   **成功响应 (200 OK)**: `{"status": true, "data": "ok"}`

#### 3.3.4 删除文档 (软删除)

*   **Path**: `POST /api/delete_doc/`
*   **描述**: 将一篇文档移入回收站。
*   **请求参数**: `token` (string, required)。
*   **请求体 (JSON or Form-data)**:
    *   `did` (number, required): 文档ID。
*   **成功响应 (200 OK)**: `{"status": true, "data": "ok"}`
