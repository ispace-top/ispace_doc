# coding:utf-8
# iSpaceDoc template context processors
import glob
import os

from backend.apps.admin.models import SysSetting
from django.conf import settings


def _get_available_themes():
    theme_dir = os.path.join(settings.BASE_DIR, 'static', 'css', 'theme', 'themes')
    themes = []
    if not os.path.isdir(theme_dir):
        return themes
    for f in glob.glob(os.path.join(theme_dir, '*.css')):
        name = os.path.splitext(os.path.basename(f))[0]
        themes.append({'id': name, 'name': name.replace('-', ' ').title()})
    return themes


def _resolve_active_theme(setting_dict):
    """Determine theme from site setting, defaulting to 'light'."""
    return setting_dict.get('site_theme', 'light') or 'light'


# 系统设置 - 上下文变量
def sys_setting(request):
    setting_dict = dict()
    # 设置网站版本
    setting_dict['isdoc_version'] = settings.VERSIONS
    # 设置debug状态
    setting_dict['debug'] = settings.DEBUG
    # 站点地图状态
    setting_dict['sitemap'] = settings.SITEMAP
    # 获取系统设置状态（数据库未迁移时静默跳过）
    try:
        datas = SysSetting.objects.filter(types__in=["basic","doc"])
        for data in datas:
            setting_dict[data.name] = data.value
    except Exception:
        pass

    # 主题配置
    setting_dict['active_theme'] = _resolve_active_theme(setting_dict)
    setting_dict['active_theme_css'] = f'css/theme/themes/{setting_dict["active_theme"]}.css'
    setting_dict['available_themes'] = _get_available_themes()

    return setting_dict