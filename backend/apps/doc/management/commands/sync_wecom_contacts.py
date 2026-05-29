"""企业微信通讯录同步管理命令。

用法:
    python manage.py sync_wecom_contacts                # 使用 config.ini 配置
    python manage.py sync_wecom_contacts --corp-id=xxx --corp-secret=xxx
    python manage.py sync_wecom_contacts --dry-run       # 仅预览不写入
"""
import configparser
import os
import time

from django.core.management.base import BaseCommand

CONFIG_DIR = os.path.join(os.getcwd(), 'config', 'conf')
CONFIG_PATH = os.path.join(CONFIG_DIR, os.environ.get('ISDOC_CONFIG', 'config.ini'))


class Command(BaseCommand):
    help = "从企业微信同步部门与成员到本地 OrgNode / OrgUser"

    def add_arguments(self, parser):
        parser.add_argument("--corp-id", type=str, help="企业微信 Corp ID")
        parser.add_argument("--corp-secret", type=str, help="企业微信应用 Secret")
        parser.add_argument("--agent-id", type=str, default="", help="应用 Agent ID")
        parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入数据库")

    def handle(self, *args, **options):
        corp_id = options["corp_id"]
        corp_secret = options["corp_secret"]

        if not corp_id or not corp_secret:
            corp_id, corp_secret = self._read_config()

        if not corp_id or not corp_secret:
            self.stderr.write("缺少 corp_id / corp_secret，请在 config.ini [auth.wecom] 段配置或通过命令行传参")
            return

        from backend.apps.doc.sync.wecom import WeComSyncBackend

        backend = WeComSyncBackend(
            corp_id=corp_id,
            corp_secret=corp_secret,
            agent_id=options.get("agent_id", ""),
        )

        if options["dry_run"]:
            self._do_dry_run(backend)
            return

        self.stdout.write("正在从企业微信拉取通讯录...")
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
        """预览模式：仅打印拉取结果。"""
        self.stdout.write("--- 部门列表 ---")
        depts = backend.fetch_departments()
        for d in depts:
            self.stdout.write(f"  [{d.external_id}] {d.name} (parent={d.parent_external_id})")

        self.stdout.write(f"\n--- 成员列表 ({len(depts)} 个部门) ---")
        users = backend.fetch_users()
        for u in users:
            self.stdout.write(f"  [{u.external_id}] {u.name} <{u.email}> depts={u.department_external_ids}")

        self.stdout.write(self.style.SUCCESS(
            f"\n预览: {len(depts)} 个部门, {len(users)} 个成员"
        ))

    @staticmethod
    def _read_config():
        parser = configparser.ConfigParser()
        parser.read(CONFIG_PATH, encoding="utf-8")
        corp_id = parser.get("auth.wecom", "corp_id", fallback="")
        corp_secret = parser.get("auth.wecom", "corp_secret", fallback="")
        return corp_id, corp_secret
