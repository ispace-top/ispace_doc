# coding:utf-8

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from backend.apps.doc.models import Doc


class HomeSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['pro_list']

    def location(self, item):
        return reverse(item)


class DocSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Doc.objects.filter(status=1, is_public=True, is_deleted=False)

    def lastmod(self, obj):
        return obj.modify_time


class SitemapAll:
    def __init__(self):
        self.sitemaps = {}

    def __iter__(self):
        self._generate_sitemaps_dict()
        return self.sitemaps.__iter__()

    def __getitem__(self, key):
        self._generate_sitemaps_dict()
        return self.sitemaps[key]

    def items(self):
        self._generate_sitemaps_dict()
        return self.sitemaps.items()

    def _generate_sitemaps_dict(self):
        if self.sitemaps:
            return
        self.sitemaps['docs'] = DocSitemap()
        self.sitemaps['home'] = HomeSitemap()
