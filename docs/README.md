# iSpaceDoc 项目文档目录

本目录包含了iSpaceDoc项目的完整分析文档，帮助开发者和用户更好地理解项目结构和功能特性。

## 📚 文档列表

### 1. [项目结构分析.md](./项目结构分析.md)
**内容概述：** iSpaceDoc项目的完整技术架构分析
- 目录结构详解
- 核心模块分析（app_admin、app_doc、app_api）
- 技术栈详细说明
- 数据模型关系图
- 配置系统说明
- 安全特性和性能优化

**适用对象：** 开发者、技术人员、架构师

### 2. [项目说明文档.md](./项目说明文档.md)
**内容概述：** iSpaceDoc项目的功能特性和应用场景
- 项目核心定位和特色
- 主要功能模块介绍
- 部署方案和环境支持
- 多端生态系统
- 安全特性和性能说明
- 社区支持和版本信息

**适用对象：** 产品经理、用户、决策者

### 3. [需求规格文档.md](./需求规格文档.md)
**内容概述：** iSpaceDoc系统的详细需求规格说明
- 功能需求详细定义（120+需求点）
- 非功能性需求（性能、安全、兼容性）
- 系统约束条件
- 验收标准定义
- 用户角色和使用场景

**适用对象：** 产品经理、测试工程师、项目经理

## 🎯 文档用途

### 开发参考
- 了解项目整体架构和模块划分
- 掌握技术栈和开发规范
- 理解数据模型和业务逻辑

### 产品规划
- 明确功能边界和产品定位
- 了解用户需求和使用场景
- 制定功能迭代和发展路线

### 项目管理
- 评估开发工作量和技术难度
- 制定测试策略和验收标准
- 规划部署和运维方案

## 📊 项目核心数据

| 指标 | 数值 |
|------|------|
| 当前版本 | v0.9.6 |
| 开发语言 | Python |
| Web框架 | Django 4.2+ |
| 前端技术 | jQuery + LayUI |
| 数据库支持 | 5种（MySQL、PostgreSQL等） |
| 功能需求数 | 120+ |
| 支持平台 | Web、桌面、移动、扩展 |
| 部署方式 | Docker、传统部署 |

## 🔧 快速上手

### 开发环境搭建
```bash
# 1. 克隆项目
git clone https://github.com/zmister2016/iSpaceDoc.git
cd iSpaceDoc

# 2. 安装依赖
pip install -r requirements.txt

# 3. 数据库配置
python manage.py migrate

# 4. 创建管理员
python manage.py createsuperuser

# 5. 启动服务
python manage.py runserver
```

### Docker部署
```bash
# 一键部署
git clone https://gitee.com/zmister/mrdoc-install.git
cd mrdoc-install
chmod +x docker-install.sh
./docker-install.sh
```

## 📖 相关链接

- **项目主页**：https://mrdoc.pro
- **在线文档**：https://doc.mrdoc.pro
- **演示站点**：http://mrdoc.zmister.com
- **Docker镜像**：https://hub.docker.com/r/zmister/mrdoc

## 🤝 贡献指南

如需补充或修改文档，请：
1. Fork项目仓库
2. 创建功能分支
3. 提交修改并推送
4. 创建Pull Request

## 📝 版本信息

- **文档版本**：v1.0
- **基于项目版本**：iSpaceDoc v0.9.6
- **最后更新**：2025年8月24日
- **维护者**：项目开发团队

---

*这些文档将帮助您全面了解iSpaceDoc项目，如有疑问请查看官方文档或联系开发团队*