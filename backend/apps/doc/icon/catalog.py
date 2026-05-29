"""图标目录 — Phosphor Icons 元数据索引。

内置常用图标子集（无需安装外部包），可选从 phosphor-icons 包加载完整数据。
"""
import json
import os

# 内置图标目录（名称 → 分类/标签）
# Phosphor Icons 常用子集，共 ~200 个高频图标
_BUILTIN_ICONS: dict[str, dict] = {
    # 箭头
    "arrow-left": {"category": "arrows", "tags": ["箭头", "左", "返回"]},
    "arrow-right": {"category": "arrows", "tags": ["箭头", "右", "前进"]},
    "arrow-up": {"category": "arrows", "tags": ["箭头", "上", "上传"]},
    "arrow-down": {"category": "arrows", "tags": ["箭头", "下", "下载"]},
    "arrow-clockwise": {"category": "arrows", "tags": ["箭头", "刷新", "重做"]},
    "arrow-counter-clockwise": {"category": "arrows", "tags": ["箭头", "撤销"]},
    "arrow-u-up-left": {"category": "arrows", "tags": ["箭头", "回复"]},
    "arrows-out": {"category": "arrows", "tags": ["箭头", "全屏", "展开"]},
    "arrows-in": {"category": "arrows", "tags": ["箭头", "缩小", "收缩"]},
    "caret-left": {"category": "arrows", "tags": ["箭头", "左", "折叠"]},
    "caret-right": {"category": "arrows", "tags": ["箭头", "右", "展开"]},
    "caret-down": {"category": "arrows", "tags": ["箭头", "下", "下拉"]},
    "caret-up": {"category": "arrows", "tags": ["箭头", "上"]},
    # 操作
    "plus": {"category": "actions", "tags": ["加", "新增", "创建", "添加"]},
    "minus": {"category": "actions", "tags": ["减", "删除", "移除"]},
    "x": {"category": "actions", "tags": ["关闭", "删除", "取消"]},
    "check": {"category": "actions", "tags": ["确认", "勾选", "完成", "√"]},
    "pencil-simple": {"category": "actions", "tags": ["编辑", "修改", "笔"]},
    "trash": {"category": "actions", "tags": ["删除", "垃圾桶", "移除"]},
    "copy-simple": {"category": "actions", "tags": ["复制", "拷贝"]},
    "clipboard": {"category": "actions", "tags": ["剪贴板", "粘贴"]},
    "scissors": {"category": "actions", "tags": ["剪切", "剪刀"]},
    "floppy-disk": {"category": "actions", "tags": ["保存", "磁盘"]},
    "share": {"category": "actions", "tags": ["分享", "转发"]},
    "export": {"category": "actions", "tags": ["导出", "下载"]},
    "upload-simple": {"category": "actions", "tags": ["上传", "导入"]},
    "download-simple": {"category": "actions", "tags": ["下载"]},
    "eye": {"category": "actions", "tags": ["查看", "预览", "可见"]},
    "eye-slash": {"category": "actions", "tags": ["隐藏", "不可见"]},
    "magnifying-glass": {"category": "actions", "tags": ["搜索", "查找"]},
    "funnel": {"category": "actions", "tags": ["筛选", "过滤"]},
    "gear": {"category": "actions", "tags": ["设置", "配置", "齿轮"]},
    "sliders": {"category": "actions", "tags": ["滑块", "调节", "参数"]},
    "wrench": {"category": "actions", "tags": ["工具", "扳手", "设置"]},
    "lock-simple": {"category": "actions", "tags": ["锁", "权限", "安全"]},
    "lock-open": {"category": "actions", "tags": ["解锁", "公开"]},
    "key": {"category": "actions", "tags": ["钥匙", "密码", "密钥"]},
    "sign-in": {"category": "actions", "tags": ["登录", "进入"]},
    "sign-out": {"category": "actions", "tags": ["注销", "退出"]},
    "bookmark-simple": {"category": "actions", "tags": ["书签", "收藏"]},
    "link-simple": {"category": "actions", "tags": ["链接", "超链接"]},
    "link-break": {"category": "actions", "tags": ["断开链接"]},
    "heart": {"category": "actions", "tags": ["喜欢", "点赞", "爱心", "收藏"]},
    "thumbs-up": {"category": "actions", "tags": ["点赞", "赞", "好评"]},
    "star": {"category": "actions", "tags": ["星", "收藏", "评分"]},
    "bell": {"category": "actions", "tags": ["通知", "铃铛", "提醒"]},
    "bell-ringing": {"category": "actions", "tags": ["通知", "新消息"]},
    "envelope": {"category": "actions", "tags": ["邮件", "消息", "信封"]},
    "paper-plane": {"category": "actions", "tags": ["发送", "发布"]},
    "chat": {"category": "actions", "tags": ["聊天", "消息", "对话"]},
    "chat-centered": {"category": "actions", "tags": ["聊天", "消息"]},
    "chats": {"category": "actions", "tags": ["聊天", "群聊", "消息"]},
    "user": {"category": "people", "tags": ["用户", "个人", "账号"]},
    "users": {"category": "people", "tags": ["用户", "群组", "多人"]},
    "user-plus": {"category": "people", "tags": ["添加用户", "邀请"]},
    "user-gear": {"category": "people", "tags": ["用户设置", "管理"]},
    "identification-badge": {"category": "people", "tags": ["身份", "角色", "徽章"]},
    "address-book": {"category": "people", "tags": ["通讯录", "联系人"]},
    # 文档/文件
    "file": {"category": "files", "tags": ["文件", "文档"]},
    "file-text": {"category": "files", "tags": ["文件", "文本", "文档"]},
    "file-pdf": {"category": "files", "tags": ["PDF", "文档"]},
    "file-image": {"category": "files", "tags": ["图片", "图像"]},
    "file-video": {"category": "files", "tags": ["视频", "媒体"]},
    "file-audio": {"category": "files", "tags": ["音频", "音乐"]},
    "file-zip": {"category": "files", "tags": ["压缩", "ZIP"]},
    "file-code": {"category": "files", "tags": ["代码", "编程"]},
    "files": {"category": "files", "tags": ["文件", "多个文件"]},
    "folder": {"category": "files", "tags": ["文件夹", "目录"]},
    "folder-open": {"category": "files", "tags": ["文件夹", "打开", "展开"]},
    "folder-plus": {"category": "files", "tags": ["新建文件夹"]},
    "note": {"category": "files", "tags": ["笔记", "记事"]},
    "notebook": {"category": "files", "tags": ["笔记本"]},
    "article": {"category": "files", "tags": ["文章", "文档"]},
    "newspaper": {"category": "files", "tags": ["新闻", "文章"]},
    "book": {"category": "files", "tags": ["书", "文档", "知识"]},
    "book-open": {"category": "files", "tags": ["书", "阅读"]},
    "books": {"category": "files", "tags": ["书", "知识库"]},
    # 编辑/排版
    "text-aa": {"category": "editor", "tags": ["字体", "字号"]},
    "text-b": {"category": "editor", "tags": ["加粗", "粗体", "B"]},
    "text-italic": {"category": "editor", "tags": ["斜体", "I"]},
    "text-underline": {"category": "editor", "tags": ["下划线", "U"]},
    "text-strikethrough": {"category": "editor", "tags": ["删除线", "S"]},
    "text-h": {"category": "editor", "tags": ["标题", "H"]},
    "text-align-left": {"category": "editor", "tags": ["左对齐"]},
    "text-align-center": {"category": "editor", "tags": ["居中"]},
    "text-align-right": {"category": "editor", "tags": ["右对齐"]},
    "text-indent": {"category": "editor", "tags": ["缩进"]},
    "list-bullets": {"category": "editor", "tags": ["无序列表", "列表"]},
    "list-numbers": {"category": "editor", "tags": ["有序列表", "编号"]},
    "list-checks": {"category": "editor", "tags": ["任务列表", "待办"]},
    "quotes": {"category": "editor", "tags": ["引用", "引号"]},
    "code": {"category": "editor", "tags": ["代码", "编程"]},
    "code-block": {"category": "editor", "tags": ["代码块"]},
    "image": {"category": "editor", "tags": ["图片", "图像", "插图"]},
    "image-square": {"category": "editor", "tags": ["图片", "正方形"]},
    "video": {"category": "editor", "tags": ["视频", "媒体"]},
    "table": {"category": "editor", "tags": ["表格"]},
    "link": {"category": "editor", "tags": ["链接", "超链接"]},
    "link-simple-horizontal": {"category": "editor", "tags": ["链接", "水平线"]},
    "highlighter-circle": {"category": "editor", "tags": ["高亮", "标记", "荧光笔"]},
    # 设计/绘图
    "pen": {"category": "design", "tags": ["笔", "绘图", "手绘"]},
    "pen-nib": {"category": "design", "tags": ["钢笔", "签名"]},
    "paint-brush": {"category": "design", "tags": ["画笔", "绘画"]},
    "pencil": {"category": "design", "tags": ["铅笔", "草图"]},
    "eraser": {"category": "design", "tags": ["橡皮", "擦除"]},
    "palette": {"category": "design", "tags": ["调色板", "颜色", "主题"]},
    "shapes": {"category": "design", "tags": ["形状", "图形"]},
    "circle": {"category": "design", "tags": ["圆", "圆形"]},
    "square": {"category": "design", "tags": ["方", "矩形"]},
    "triangle": {"category": "design", "tags": ["三角", "三角形"]},
    "polygon": {"category": "design", "tags": ["多边形"]},
    "bezier-curve": {"category": "design", "tags": ["曲线", "贝塞尔"]},
    "path": {"category": "design", "tags": ["路径", "线条"]},
    "compass": {"category": "design", "tags": ["指南针", "圆规"]},
    "ruler": {"category": "design", "tags": ["尺子", "测量", "标尺"]},
    "drop": {"category": "design", "tags": ["水滴", "颜色", "颜料"]},
    "git-branch": {"category": "dev", "tags": ["分支", "Git", "版本"]},
    "git-commit": {"category": "dev", "tags": ["提交", "Git", "节点"]},
    "git-pull-request": {"category": "dev", "tags": ["PR", "Git", "合并"]},
    "git-merge": {"category": "dev", "tags": ["合并", "Git"]},
    "terminal": {"category": "dev", "tags": ["终端", "命令行", "控制台"]},
    "terminal-window": {"category": "dev", "tags": ["终端", "窗口"]},
    "database": {"category": "dev", "tags": ["数据库", "存储"]},
    "cpu": {"category": "dev", "tags": ["处理器", "芯片"]},
    "cloud": {"category": "dev", "tags": ["云", "云端", "存储"]},
    "server": {"category": "dev", "tags": ["服务器", "主机"]},
    "hard-drive": {"category": "dev", "tags": ["硬盘", "存储"]},
    "wifi-high": {"category": "network", "tags": ["WiFi", "无线", "网络"]},
    "globe": {"category": "network", "tags": ["全球", "网络", "地球"]},
    "globe-hemisphere-east": {"category": "network", "tags": ["地球", "东半球"]},
    "rss-simple": {"category": "network", "tags": ["RSS", "订阅"]},
    "broadcast": {"category": "network", "tags": ["广播", "发布"]},
    "activity": {"category": "charts", "tags": ["活动", "统计", "心跳"]},
    "chart-bar": {"category": "charts", "tags": ["柱状图", "图表", "统计"]},
    "chart-line": {"category": "charts", "tags": ["折线图", "趋势", "统计"]},
    "chart-pie": {"category": "charts", "tags": ["饼图", "比例", "统计"]},
    "chart-scatter": {"category": "charts", "tags": ["散点图", "数据"]},
    "trend-up": {"category": "charts", "tags": ["上升", "增长", "趋势"]},
    "trend-down": {"category": "charts", "tags": ["下降", "减少", "趋势"]},
    "currency-dollar": {"category": "charts", "tags": ["美元", "金额", "财务"]},
    "calendar": {"category": "time", "tags": ["日历", "日期"]},
    "calendar-check": {"category": "time", "tags": ["日历", "确认"]},
    "clock": {"category": "time", "tags": ["时钟", "时间"]},
    "timer": {"category": "time", "tags": ["计时器", "倒计时"]},
    "hourglass": {"category": "time", "tags": ["沙漏", "等待"]},
    "alarm": {"category": "time", "tags": ["闹钟", "提醒"]},
    "sun": {"category": "weather", "tags": ["太阳", "白天", "晴"]},
    "moon": {"category": "weather", "tags": ["月亮", "夜间", "暗色"]},
    "cloud-sun": {"category": "weather", "tags": ["多云", "天气"]},
    "lightning": {"category": "weather", "tags": ["闪电", "快速"]},
    "map-pin": {"category": "map", "tags": ["定位", "位置", "标记"]},
    "map-pin-line": {"category": "map", "tags": ["定位", "位置"]},
    "navigation-arrow": {"category": "map", "tags": ["导航", "方向"]},
    "house-simple": {"category": "nav", "tags": ["首页", "主页", "首页"]},
    "sidebar-simple": {"category": "nav", "tags": ["侧边栏", "菜单"]},
    "list": {"category": "nav", "tags": ["列表", "菜单"]},
    "grid-four": {"category": "nav", "tags": ["网格", "宫格"]},
    "info": {"category": "status", "tags": ["信息", "提示", "详情"]},
    "warning": {"category": "status", "tags": ["警告", "注意", "⚠"]},
    "warning-circle": {"category": "status", "tags": ["警告", "注意"]},
    "question": {"category": "status", "tags": ["问题", "帮助", "问号"]},
    "prohibit": {"category": "status", "tags": ["禁止", "阻止"]},
    "check-circle": {"category": "status", "tags": ["成功", "正确", "完成"]},
    "x-circle": {"category": "status", "tags": ["错误", "失败", "关闭"]},
    "spinner": {"category": "status", "tags": ["加载", "等待", "旋转"]},
    "spinner-gap": {"category": "status", "tags": ["加载", "等待"]},
    "circle-notch": {"category": "status", "tags": ["加载", "旋转"]},
    # 品牌/Logo
    "github-logo": {"category": "brands", "tags": ["GitHub", "代码"]},
    "gitlab-logo-simple": {"category": "brands", "tags": ["GitLab", "代码"]},
    "google-logo": {"category": "brands", "tags": ["Google", "谷歌"]},
    "microsoft-outlook-logo": {"category": "brands", "tags": ["Outlook", "邮件"]},
    "slack-logo": {"category": "brands", "tags": ["Slack", "聊天"]},
    "discord-logo": {"category": "brands", "tags": ["Discord"]},
}

CATEGORY_LABELS = {
    "arrows": "箭头",
    "actions": "操作",
    "people": "用户",
    "files": "文件",
    "editor": "编辑",
    "design": "设计",
    "dev": "开发",
    "network": "网络",
    "charts": "图表",
    "time": "时间",
    "weather": "天气",
    "map": "地图",
    "nav": "导航",
    "status": "状态",
    "brands": "品牌",
}


def search_icons(query: str = "", category: str = "", page: int = 1, page_size: int = 50) -> dict:
    """搜索图标。

    Returns:
        {"icons": [...], "total": int, "page": int, "categories": [...]}
    """
    results = []
    q = query.lower().strip() if query else ""

    for name, meta in _BUILTIN_ICONS.items():
        if category and meta["category"] != category:
            continue
        if q:
            # 匹配名称或标签
            if q in name.lower() or any(q in t.lower() or q == t for t in meta["tags"]):
                results.append({"name": name, "category": meta["category"], "tags": meta["tags"]})
        else:
            results.append({"name": name, "category": meta["category"], "tags": meta["tags"]})

    total = len(results)
    start = (page - 1) * page_size
    icons = results[start : start + page_size]

    categories = [{"name": k, "label": v} for k, v in CATEGORY_LABELS.items()]

    return {"icons": icons, "total": total, "page": page, "page_size": page_size, "categories": categories}
