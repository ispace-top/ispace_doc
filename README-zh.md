<h1 align="center">爱思文档开源版</h1>

<p align="center">个人和小型团队的云笔记、云文档、知识管理私有化部署方案</p>

<p align="center">
<a href="./README-zh.md">中文介绍</a> |
<a href="./README.md">English Description</a>
</p>

<p align="center">
<img src="https://img.shields.io/badge/iSpaceDoc-v0.9.6-brightgreen.svg" title="iSpaceDoc" />
<img src="https://img.shields.io/badge/Python-3.9+-blue.svg" title="Python" />
<img src="https://img.shields.io/badge/Django-v4.2-important.svg" title="Django" />
</p>

## 简介

`iSpaceDoc` 是基于 Python 开发的在线文档系统。

iSpaceDoc 适合作为个人和中小型团队的私有云文档、云笔记和知识管理工具，致力于成为优秀的私有化在线文档部署方案。

你可以简单粗暴地将 iSpaceDoc 视为「可私有部署的语雀」和「可在线编辑文档的 GitBook」。

## 适用场景

个人云笔记、在线产品手册、团队内部知识库、在线电子教程等私有化部署场景。

## 功能特性

- **站点管理**
    - 用户管理
    - 图片管理
    - 附件管理
    - 文档管理
    - 文集管理
    - 注册邀请码配置
    - 登录验证码配置
    - 全站禁止注册配置
    - 全站强制登录配置
    - 广告代码配置
    - 统计代码配置
    - 站点信息配置
    - 备案号配置
    - 附件配置

- **个人管理**
    - 文集管理
    - 文档管理：新建、删除、回收站、历史版本
    - 文档模板管理：新建、删除
    - 图片管理：上传、分组、删除
    - 附件管理：上传、删除
    - Token 管理：借助 Token API 接口高效新建和获取文档
    - 个人信息管理：修改昵称、修改电子邮箱、切换文档编辑器

- **文集控制**
    - 文集图标配置
    - 文字水印配置
    - 文集权限配置：公开、私密、指定用户可见、访问码可见
    - 下载配置：PDF、EPUB 文件生成和下载
    - 文集协作成员配置
    - 文集文档拖拽排序
    - 文集导出
    - 文集转让

- **文档书写**
    - 文本文档、表格文档两种文档类型，Markdown、富文本两种编辑模式，Editor.md、Vditor、iceEditor 三种编辑器加持
    - 图片、附件、科学公式、音视频、思维导图、流程图、Echarts 图表
    - 文档排序、文档上级设置、文档模板插入
    - 文档标签设置

- **文档阅读**
    - 两栏式布局，三级目录层级显示，左侧文集大纲，右侧文档正文
    - 文档阅读字体缩放、字体类型切换、日间夜间模式切换、页面社交分享、移动端阅读优化
    - 文档 Markdown 文件下载
    - 标签关系网络图
    - 文档全文搜索
    - 文档分享码分享
    - 文档收藏

- **其他特性**
    - 搜索引擎收录支持
    - Sitemap 站点地图
    - 无限用户限制
    - 无限空间限制

## 基于 Docker Compose 的一键部署和更新

### 1、部署

```bash
git clone <仓库地址> && cd iSpaceDoc
docker compose -f config/docker/docker-compose.yml up -d
```

### 2、更新

如果有版本更新，直接在爱思文档项目目录下运行 `config/scripts/docker-update.sh` 脚本即可完成更新。

## 简明运行教程

### 1、安装依赖库

```bash
pip install -r requirements.txt
```

### 2、初始化数据库

在安装完所需的第三方库并配置好数据库信息之后，我们需要对数据库进行初始化。

在项目路径下打开命令行界面，运行如下命令生成数据库迁移：

```bash
python manage.py makemigrations
```

运行如下命令执行数据库迁移：

```bash
python manage.py migrate
```

执行完毕之后，数据库就初始化完成了。

### 3、创建管理员账户

在初始化完数据库之后，需要创建一个管理员账户来管理整个 iSpaceDoc，在项目路径下打开命令行终端，运行如下命令：

```bash
python manage.py createsuperuser
```

按照提示输入用户名、电子邮箱地址和密码即可。

### 4、测试运行

在完成上述步骤之后，即可运行使用 iSpaceDoc。

在测试环境中，可以使用 Django 自带的服务器运行 iSpaceDoc，其命令为：

```bash
python manage.py runserver
```

## 依赖

爱思文档基于以下开源项目进行开发，在此表示感谢：

- Python
- Django
- jQuery
- LayUI
- PearAdminLayui
- Editor.md
- Marked
- CodeMirror
- ECharts
- Viewer.js
- Sortable.js
- Vditor
- iceEditor

## 协议

<a href="./LICENSE">GPL-3.0</a>

开源版的使用者必须保留 iSpaceDoc 和爱思文档相关版权标识，禁止对 iSpaceDoc 和爱思文档相关版权标识进行修改和删除。

如果违反，开发者保留对侵权者追究责任的权利。

其他相关协议亦可参考《[免责声明](https://github.com/kerwin618/iSpaceDoc/blob/main/DISCLAIMER.md)》。
