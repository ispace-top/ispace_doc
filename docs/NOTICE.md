# i·Space Doc 第三方依赖与许可证声明

> 本文档按照 GPL-3.0 第 5 条要求，列出 i·Space Doc 项目中使用的所有第三方组件及其许可证。

## 后端依赖（Python）

| 包名 | 版本 | 许可证 | 版权归属 |
|------|------|--------|----------|
| Django | 4.2 | BSD-3-Clause | Django Software Foundation |
| djangorestframework | 3.x | BSD | Encode OSS Ltd |
| django-cors-headers | 4.x | MIT | Otto Yiu |
| django-haystack | 3.x | BSD | Daniel Lindsley |
| celery | 5.x | BSD-3-Clause | Celery Project |
| whoosh | 2.7 | BSD-2 | Matt Chaput |
| jieba | 0.42 | MIT | Sun Junyi |
| beautifulsoup4 | 4.x | MIT | Leonard Richardson |
| lxml | 5.x | BSD-3-Clause | lxml dev team |
| Pillow | 10.x | Historical (BSD-like) | Jeffrey A. Clark |
| requests | 2.x | Apache-2.0 | Kenneth Reitz |
| PyYAML | 6.x | MIT | Kirill Simonov |
| Markdown | 3.x | BSD-3-Clause | Python-Markdown Project |
| mammoth | 1.x | BSD-2 | Michael Williamson |
| markdownify | 0.x | MIT | Matthew Tretter |
| selenium | 4.x | Apache-2.0 | Software Freedom Conservancy |
| qiniu | 7.x | MIT | Qiniu Cloud |
| mysqlclient | 2.x | GPL-2.0 | MySQL AB |
| fastapi | 0.x | MIT | Sebastián Ramírez |
| uvicorn | 0.x | BSD | Encode OSS Ltd |
| python-multipart | 0.x | Apache-2.0 | Marcelo Trylesinski |
| sqlalchemy | 2.x | MIT | SQLAlchemy Authors |
| asyncpg | 0.x | Apache-2.0 | MagicStack Inc |
| aiosqlite | 0.x | MIT | aiosqlite Contributors |
| psycopg2-binary | 2.x | LGPL-3.0 | Federico Di Gregorio |
| redis | 5.x | MIT | Redis Inc |
| python-jose | 3.x | MIT | Michael Davis |
| passlib | 1.x | BSD | Eli Collins |
| pydantic-settings | 2.x | MIT | Samuel Colvin |
| boto3 | 1.x | Apache-2.0 | Amazon Web Services |
| oss2 | 2.x | Apache-2.0 | Alibaba Cloud |
| elasticsearch-py | 8.x | Apache-2.0 | Elasticsearch B.V. |
| python-ldap | 3.x | Python-style (CNRI) | python-ldap Project |
| loguru | 0.x | MIT | Delgan |

> ⚠️ `mysqlclient` 使用 GPL-2.0，但作为数据库驱动，通过 Django ORM 间接使用，不被视为"组合作品"（combined work）。若担心传染性风险，可替换为 `mysql-connector-python`（GPL-2.0 with FOSS License Exception）。

## 前端依赖（JavaScript/CSS）

| 组件 | 版本 | 许可证 | 位置 |
|------|------|--------|------|
| Vditor | 3.x | MIT | `frontend/static/vditor/` |
| LayUI | 2.x | MIT | `frontend/static/layui/` |
| PearAdminLayui | — | MIT | `frontend/static/PearAdminLayui/` |
| Luckysheet | 2.x | MIT | `frontend/static/luckysheet/` |
| iceEditor | — | MIT | 编辑器集成 |
| SortableJS | 1.15 | MIT | CDN 加载 |
| jQuery | 3.x | MIT | `node_modules/jquery/` |
| marked.js | — | MIT | `frontend/static/markdown-ext/marked/` |
| highlight.js | — | BSD-3-Clause | `frontend/static/markdown-ext/highlight/` |
| KaTeX | — | MIT | `frontend/static/markdown-ext/katex/` |
| Graphviz (hpcc-js) | — | MIT | `frontend/static/markdown-ext/graphviz/` |
| ECharts | 5.x | Apache-2.0 | `frontend/static/markdown-ext/echarts/` |
| Prism.js | 1.x | MIT | `frontend/static/markdown-ext/highlight/` |
| Cropper.js | 1.x | MIT | 头像裁剪 |
| mammoth.js | 1.x | BSD-2 | 前端 Docx 转换 |
| mind-elixir | — | MIT | 思维导图（v2.0 规划） |

## 字体

| 字体 | 许可证 | 位置 |
|------|--------|------|
| Source Han Serif CN (思源宋体) | SIL Open Font License 1.1 | `frontend/static/SourceHanSerifCN-Medium.otf` |
| LayUI Icon Font | MIT | `frontend/static/layui/font/` |
| KaTeX 数学字体 | SIL Open Font License 1.1 | `frontend/static/markdown-ext/katex/fonts/` |

## 基础设施（Docker）

| 组件 | 许可证 |
|------|--------|
| PostgreSQL 16 (Alpine) | PostgreSQL License (BSD-like) |
| Redis 7 (Alpine) | BSD-3-Clause |
| Elasticsearch 8.x | Elastic License 2.0 / SSPL |
| Python 3.11 (Alpine) | Python Software Foundation License |

> ⚠️ Elasticsearch 8.x 使用 Elastic License 2.0（非 OSI 认证开源许可证）。仅通过 Docker 使用现成镜像，不修改源码，合规。

## 协议兼容性说明

i·Space Doc 采用 **GPL-3.0** 许可证。本项目使用的所有第三方组件：

- ✅ **MIT / BSD / Apache-2.0 / SIL OFL 1.1** — 与 GPL-3.0 完全兼容
- ⚠️ **LGPL-3.0**（psycopg2-binary）— 与 GPL-3.0 兼容（LGPL 允许动态链接）
- ⚠️ **Elastic License 2.0** — 仅通过 Docker 预构建镜像使用，非源码级别集成

> 本文件作为项目 NOTICE 的一部分，随源码分发。如有遗漏或错误，请提交 Issue 反馈。
