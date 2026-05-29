"""LDAP 用户 & 组织架构同步管理命令。

用法:
    python manage.py sync_ldap [--dry-run] [--full]

从 LDAP 目录同步用户和组织单位 (OU) 到本地数据库。
"""
import configparser
import logging
import os
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.getcwd(), 'config', 'conf')
CONFIG_PATH = os.path.join(CONFIG_DIR, os.environ.get('ISDOC_CONFIG', 'config.ini'))


class Command(BaseCommand):
    help = "从 LDAP 目录同步用户和组织架构到本地数据库"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入数据库")
        parser.add_argument("--full", action="store_true", help="全量同步（默认增量）")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        full_sync = options["full"]

        cfg = self._read_config()

        if not cfg["server_uri"]:
            self.stdout.write(self.style.WARNING("LDAP 未配置（config.ini 中无 [auth.ldap] 段或 server_uri 为空），跳过同步"))
            return

        if not cfg["bind_dn"] or not cfg["user_base_dn"]:
            self.stdout.write(self.style.ERROR("LDAP 配置不完整（缺少 bind_dn 或 user_base_dn）"))
            return

        try:
            import ldap  # noqa: F401
        except ImportError:
            self.stdout.write(self.style.ERROR("python-ldap 未安装，请执行: pip install python-ldap"))
            return

        from backend.apps.doc.sync.ldap import LDAPSsyncBackend

        backend = LDAPSsyncBackend(
            server_uri=cfg["server_uri"],
            bind_dn=cfg["bind_dn"],
            bind_password=cfg["bind_password"],
            user_base_dn=cfg["user_base_dn"],
            user_filter=cfg["user_filter"],
            username_attr=cfg["username_attr"],
            email_attr=cfg["email_attr"],
            use_tls=cfg["use_tls"],
            org_base_dn=cfg["org_base_dn"],
            org_filter=cfg["org_filter"],
            org_name_attr=cfg["org_name_attr"],
        )

        if dry_run:
            self._do_dry_run(backend)
            return

        self.stdout.write("正在从 LDAP 拉取数据...")
        t0 = time.time()

        result = backend.sync()

        elapsed = time.time() - t0
        self.stdout.write(self.style.SUCCESS(
            f"同步完成 (耗时 {elapsed:.1f}s): "
            f"部门 新建{result.departments_created} 更新{result.departments_updated} 删除{result.departments_deleted}, "
            f"用户 新建{result.users_created} 更新{result.users_updated} 停用{result.users_deactivated}"
        ))
        if result.errors:
            for err in result.errors:
                self.stderr.write(f"错误: {err}")

    def _do_dry_run(self, backend):
        """预览模式：仅打印拉取结果，不写入数据库。"""
        depts = backend.fetch_departments()
        self.stdout.write(f"--- 组织单位 ({len(depts)} 个) ---")
        for d in depts:
            self.stdout.write(f"  [{d.external_id}] {d.name} (parent={d.parent_external_id})")

        users = backend.fetch_users()
        self.stdout.write(f"\n--- 用户 ({len(users)} 个) ---")
        for u in users:
            self.stdout.write(f"  [{u.external_id}] {u.name} <{u.email}> depts={u.department_external_ids}")

        self.stdout.write(self.style.SUCCESS(
            f"\n预览: {len(depts)} 个部门, {len(users)} 个用户"
        ))

    @staticmethod
    def _read_config():
        parser = configparser.ConfigParser()
        parser.read(CONFIG_PATH, encoding="utf-8")

        if not parser.has_section("auth.ldap"):
            return {"server_uri": ""}

        return {
            "server_uri": parser.get("auth.ldap", "server_uri", fallback=""),
            "bind_dn": parser.get("auth.ldap", "bind_dn", fallback=""),
            "bind_password": parser.get("auth.ldap", "bind_password", fallback=""),
            "user_base_dn": parser.get("auth.ldap", "user_base_dn", fallback=""),
            "user_filter": parser.get("auth.ldap", "user_filter", fallback="(objectClass=person)"),
            "username_attr": parser.get("auth.ldap", "username_attr", fallback="uid"),
            "email_attr": parser.get("auth.ldap", "email_attr", fallback="mail"),
            "use_tls": parser.getboolean("auth.ldap", "use_tls", fallback=False),
            "org_base_dn": parser.get("auth.ldap", "org_base_dn", fallback=""),
            "org_filter": parser.get("auth.ldap", "org_filter", fallback="(objectClass=organizationalUnit)"),
            "org_name_attr": parser.get("auth.ldap", "org_name_attr", fallback="ou"),
        }
