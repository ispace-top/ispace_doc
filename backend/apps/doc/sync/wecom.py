"""企业微信通讯录同步。

调用企业微信 API 拉取部门与成员数据，同步至本地 OrgNode / OrgUser / User。
"""
import logging
import time
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.contrib.auth.models import User

from backend.apps.doc.models import OrgNode, OrgUser, UserProfile
from .base import DirectorySyncBackend, SyncDepartment, SyncResult, SyncUser

logger = logging.getLogger(__name__)

WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComSyncBackend(DirectorySyncBackend):
    """企业微信通讯录同步后端。"""

    name = "wecom"

    def __init__(self, corp_id: str, corp_secret: str, agent_id: str = "",
                 root_org_node_id: int | None = None):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.root_org_node_id = root_org_node_id
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._dept_cache: dict[str, SyncDepartment] = {}

    # ---- API 层 ----

    def _get_access_token(self) -> str:
        """获取企业微信 access_token（含缓存）。"""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        url = f"{WECOM_API_BASE}/gettoken"
        resp = requests.get(url, params={
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret,
        }, timeout=15)
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"企业微信 access_token 获取失败: {data.get('errmsg')}")

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 7200)
        return self._access_token

    def _api_get(self, endpoint: str, params: dict = None) -> dict:
        """企业微信 GET 请求封装。"""
        token = self._get_access_token()
        params = params or {}
        params["access_token"] = token
        resp = requests.get(f"{WECOM_API_BASE}/{endpoint}", params=params, timeout=30)
        data = resp.json()
        if data.get("errcode") != 0:
            logger.warning("企业微信 API 错误: %s → %s", endpoint, data.get("errmsg"))
        return data

    # ---- 数据拉取 ----

    def fetch_departments(self) -> list[SyncDepartment]:
        """拉取全量部门列表。"""
        data = self._api_get("department/list")
        if data.get("errcode") != 0:
            logger.error("获取部门列表失败: %s", data.get("errmsg"))
            return []

        departments = []
        for item in data.get("department", []):
            dept = SyncDepartment(
                external_id=str(item["id"]),
                name=item.get("name", ""),
                parent_external_id=str(item.get("parentid")) if item.get("parentid") else None,
                order=item.get("order", 0),
            )
            departments.append(dept)
            self._dept_cache[dept.external_id] = dept

        return departments

    def fetch_users(self) -> list[SyncUser]:
        """拉取全量成员列表（含已关注成员详情）。"""
        # 先拉简要成员列表
        data = self._api_get("user/list", {"department_id": 1, "fetch_child": 1})
        if data.get("errcode") != 0:
            logger.error("获取成员列表失败: %s", data.get("errmsg"))
            return []

        users = []
        for item in data.get("userlist", []):
            user = SyncUser(
                external_id=item.get("userid", ""),
                name=item.get("name", ""),
                display_name=item.get("name", ""),
                email=item.get("email", ""),
                mobile=item.get("mobile", ""),
                avatar_url=item.get("avatar", ""),
                department_external_ids=[str(d) for d in item.get("department", [])],
                is_leader=bool(item.get("is_leader_in_dept", [])),
                position=item.get("position", ""),
                status="active" if item.get("status") == 1 else "inactive",
            )
            users.append(user)

        return users

    # ---- 同步逻辑 ----

    def sync(self) -> SyncResult:
        """执行完整同步。"""
        result = SyncResult(provider=self.name)
        result.started_at = datetime.now(timezone.utc).isoformat()

        try:
            self._sync_departments(result)
        except Exception:
            logger.exception("部门同步失败")
            result.errors.append("部门同步失败")
            result.success = False
            return result

        try:
            self._sync_users(result)
        except Exception:
            logger.exception("成员同步失败")
            result.errors.append("成员同步失败")
            result.success = False

        result.finished_at = datetime.now(timezone.utc).isoformat()
        return result

    def _sync_departments(self, result: SyncResult):
        """同步部门 → OrgNode。"""
        remote_depts = self.fetch_departments()
        if not remote_depts:
            return

        # 查找或创建根组织节点（企业微信根部门 id=1 对应 OrgNode 根）
        root_node = None
        if self.root_org_node_id:
            try:
                root_node = OrgNode.objects.get(pk=self.root_org_node_id)
            except OrgNode.DoesNotExist:
                pass
        if not root_node:
            root_node, _ = OrgNode.objects.get_or_create(
                parent=None,
                defaults={"name": "企业微信", "path": "/", "sort_order": 0},
            )

        # 构建外部 ID → OrgNode 映射
        existing = {n.external_id: n for n in
                    OrgNode.objects.filter(external_source='wecom').select_related('parent')}

        external_ids_seen = set()

        # 按 parent 排序以确保父节点先创建
        sorted_depts = sorted(remote_depts, key=lambda d: (d.parent_external_id or "", d.order))

        for dept in sorted_depts:
            external_ids_seen.add(dept.external_id)

            # 确定父节点
            parent = root_node
            if dept.parent_external_id and dept.parent_external_id in existing:
                parent = existing[dept.parent_external_id]

            if dept.external_id in existing:
                node = existing[dept.external_id]
                if node.name != dept.name or node.parent_id != parent.id:
                    node.name = dept.name
                    node.parent = parent
                    node.sort_order = dept.order
                    node.save(update_fields=["name", "parent", "sort_order"])
                    result.departments_updated += 1
            else:
                node = OrgNode.objects.create(
                    name=dept.name,
                    parent=parent,
                    external_source='wecom',
                    external_id=dept.external_id,
                    sort_order=dept.order,
                )
                existing[dept.external_id] = node
                result.departments_created += 1

        # 删除远端不存在的部门
        for ext_id, node in existing.items():
            if ext_id not in external_ids_seen:
                node.delete()
                result.departments_deleted += 1

    def _sync_users(self, result: SyncResult):
        """同步成员 → User + UserProfile + OrgUser。"""
        remote_users = self.fetch_users()
        if not remote_users:
            return

        # 建立外部部门 ID → OrgNode 映射
        org_nodes = {n.external_id: n for n in
                     OrgNode.objects.filter(external_source='wecom')}

        # 现有 WeCom 关联用户
        existing_profiles = {
            p.wecom_userid: p
            for p in UserProfile.objects.filter(wecom_userid__isnull=False).exclude(wecom_userid='')
        }

        external_ids_seen = set()

        for su in remote_users:
            external_ids_seen.add(su.external_id)

            if su.external_id in existing_profiles:
                # 更新用户信息
                profile = existing_profiles[su.external_id]
                user = profile.user
                if su.email and su.email != user.email:
                    user.email = su.email
                if su.name and su.name != user.last_name:
                    user.last_name = su.name
                user.save()
                if su.mobile:
                    profile.phone = su.mobile
                    profile.save(update_fields=["phone"])
                result.users_updated += 1
            else:
                # 创建新用户
                username = f"wecom_{su.external_id}"
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": su.email or "",
                        "last_name": su.name or su.display_name or "",
                        "is_active": su.status == "active",
                    },
                )
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"wecom_userid": su.external_id, "phone": su.mobile},
                )
                if not profile.wecom_userid:
                    profile.wecom_userid = su.external_id
                    profile.save(update_fields=["wecom_userid"])
                result.users_created += 1

            # 更新组织关联
            if su.department_external_ids:
                current_orgs = set(OrgUser.objects.filter(user=user).values_list('org_node_id', flat=True))
                target_orgs = set()
                for dept_ext_id in su.department_external_ids:
                    node = org_nodes.get(dept_ext_id)
                    if node:
                        target_orgs.add(node.id)

                # 添加新关联
                for org_id in target_orgs - current_orgs:
                    OrgUser.objects.get_or_create(user=user, org_node_id=org_id)

                # 移除旧的关联
                if target_orgs:
                    OrgUser.objects.filter(user=user).exclude(org_node_id__in=target_orgs).delete()

        # 停用远端不存在的用户
        for ext_id, profile in existing_profiles.items():
            if ext_id not in external_ids_seen:
                profile.user.is_active = False
                profile.user.save(update_fields=["is_active"])
                result.users_deactivated += 1
