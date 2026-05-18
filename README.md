<h1 align="center">iSpaceDoc — Writing documents, Gathering ideas</h1>

<p align="center">
Personal and small team cloud notes, documents, and knowledge management privatization deployment solution
</p>

<p align="center">
<a href="./README-zh.md">中文介绍</a> |
<a href="./README.md">English Description</a>
</p>

<p align="center">
<img src="https://img.shields.io/badge/iSpaceDoc-v0.9.6-brightgreen.svg" title="iSpaceDoc" />
<img src="https://img.shields.io/badge/Python-3.9+-blue.svg" title="Python" />
<img src="https://img.shields.io/badge/Django-v4.2-important.svg" title="Django" />
</p>

## Introduction

`iSpaceDoc` is an online document system developed with Python. It is suitable for individuals and small to medium teams to manage documents, knowledge and notes, committed to becoming a great private online document deployment solution.

You can simply think of iSpaceDoc as a "self-hosted Yuque" or a "GitBook with online editing."

## Features

- **Site Management & User Management**
    - Support user registration, login, management, and administrator functions
    - Support site-wide registration invite codes, email password recovery, forced login, and more
    - Support configuring project permissions with four modes: public, private, visible to specified users, and visible via access code

- **Document System**
    - Document writing and reading based on Projects, with modules for projects, documents, document templates, images, and attachments
    - Markdown and rich text editing powered by Editor.md, Vditor, and iceEditor
    - Two-column document reading page with three-level table of contents, font scaling, theme switching, and social sharing
    - Token-based REST API for programmatic access to projects and documents
    - Project collaboration with creator and multiple collaborators, with flexible collaboration permissions
    - Document history versioning with diff comparison and rollback

## Docker Compose Deployment

### 1. Deploy

```bash
git clone <repository-url> && cd iSpaceDoc
docker compose -f config/docker/docker-compose.yml up -d
```

### 2. Update

Run `config/scripts/docker-update.sh` to update the running container.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Super User

```bash
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

## Dependencies

Thanks to the following open source projects:

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
- TinyMCE
- iceEditor

## License

<a href="./LICENSE">GPL-3.0</a>
