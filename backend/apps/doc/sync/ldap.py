"""LDAP 目录同步后端。

从 LDAP 目录拉取组织单位 (OU) 和用户，同步至本地 OrgNode / OrgUser / User。
"""
import logging

from django.contrib.auth.models import User

from backend.apps.doc.models import OrgNode, OrgUser, UserProfile
from .base import DirectorySyncBackend, SyncDepartment, SyncResult, SyncUser

logger = logging.getLogger(__name__)


class LDAPSsyncBackend(DirectorySyncBackend):
    """LDAP 目录同步后端。

    配置示例 (config.ini):

        [auth.ldap]
        server_uri = ldap://ldap.example.com:389
        bind_dn = cn=admin,dc=example,dc=com
        bind_password = admin_password
        user_base_dn = ou=users,dc=example,dc=com
        user_filter = (objectClass=person)
        username_attr = uid
        email_attr = mail
        use_tls = false
        org_base_dn = ou=groups,dc=example,dc=com
        org_filter = (objectClass=organizationalUnit)
        org_name_attr = ou
    """

    name = "ldap"

    def __init__(
        self,
        server_uri: str = "ldap://localhost:389",
        bind_dn: str = "",
        bind_password: str = "",
        user_base_dn: str = "",
        user_filter: str = "(objectClass=person)",
        username_attr: str = "uid",
        email_attr: str = "mail",
        use_tls: bool = False,
        org_base_dn: str = "",
        org_filter: str = "(objectClass=organizationalUnit)",
        org_name_attr: str = "ou",
        dept_attr: str = "department",
    ):
        self._server_uri = server_uri
        self._bind_dn = bind_dn
        self._bind_password = bind_password
        self._user_base_dn = user_base_dn
        self._user_filter = user_filter
        self._username_attr = username_attr
        self._email_attr = email_attr
        self._use_tls = use_tls
        self._org_base_dn = org_base_dn
        self._org_filter = org_filter
        self._org_name_attr = org_name_attr
        self._dept_attr = dept_attr

        self._conn = None

    def _get_conn(self):
        """获取或创建 LDAP 连接。"""
        if self._conn is not None:
            return self._conn

        try:
            import ldap
        except ImportError:
            raise ImportError("请安装 python-ldap: pip install python-ldap")

        conn = ldap.initialize(self._server_uri)
        if self._use_tls:
            conn.start_tls_s()
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 15)

        if self._bind_dn:
            conn.simple_bind_s(self._bind_dn, self._bind_password)
        self._conn = conn
        return conn

    def _close_conn(self):
        if self._conn is not None:
            try:
                self._conn.unbind_s()
            except Exception:
                pass
            self._conn = None

    def _attr_first(self, attrs, key, default=""):
        """获取 LDAP 属性的第一个值。"""
        values = attrs.get(key, [])
        if not values:
            return default
        val = values[0]
        if isinstance(val, bytes):
            return val.decode("utf-8")
        return str(val) if val else default

    # ---- 数据拉取 ----

    def fetch_departments(self) -> list[SyncDepartment]:
        """从 LDAP 拉取组织单位 (OU) 列表。"""
        departments = []

        if not self._org_base_dn:
            return departments

        try:
            import ldap
            conn = self._get_conn()
            result = conn.search_s(
                self._org_base_dn,
                ldap.SCOPE_SUBTREE,
                self._org_filter,
                [self._org_name_attr, "description", "ou"],
            )
        except Exception as e:
            logger.exception("LDAP 部门搜索失败")
            return departments

        for dn, attrs in result:
            name = self._attr_first(attrs, self._org_name_attr)
            if not name:
                name = self._attr_first(attrs, "ou")

            if not name:
                continue

            # 从 DN 解析 parent
            parent_external_id = None
            parts = dn.split(",", 1)
            if len(parts) > 1 and (self._org_base_dn in parts[1]):
                parent_external_id = parts[1].strip()

            dept = SyncDepartment(
                external_id=dn,
                name=name,
                parent_external_id=parent_external_id,
                order=0,
            )
            departments.append(dept)

        return departments

    def fetch_users(self) -> list[SyncUser]:
        """从 LDAP 拉取用户列表。"""
        users = []

        try:
            import ldap
            conn = self._get_conn()
            attrs_to_fetch = [
                self._username_attr,
                self._email_attr,
                "cn",
                "displayName",
                "sn",
                "givenName",
                "mail",
                "mobile",
                "telephoneNumber",
                self._dept_attr,
                "ou",
                "title",
            ]
            result = conn.search_s(
                self._user_base_dn,
                ldap.SCOPE_SUBTREE,
                self._user_filter,
                list(set(attrs_to_fetch)),
            )
        except Exception as e:
            logger.exception("LDAP 用户搜索失败")
            return users

        for dn, attrs in result:
            username = self._attr_first(attrs, self._username_attr)
            if not username:
                continue

            email = self._attr_first(attrs, self._email_attr) or self._attr_first(attrs, "mail")
            display_name = self._attr_first(attrs, "displayName") or self._attr_first(attrs, "cn")
            mobile = self._attr_first(attrs, "mobile") or self._attr_first(attrs, "telephoneNumber")

            # 尝试从 department / ou 属性获取组织关联
            dept_values = attrs.get(self._dept_attr, [])
            if not dept_values:
                dept_values = attrs.get("ou", [])

            department_external_ids = []
            for val in dept_values:
                if isinstance(val, bytes):
                    val = val.decode("utf-8")
                department_external_ids.append(str(val))

            user = SyncUser(
                external_id=username,
                name=display_name or username,
                display_name=display_name,
                email=email,
                mobile=mobile,
                department_external_ids=department_external_ids,
                position=self._attr_first(attrs, "title"),
                status="active",
            )
            users.append(user)

        return users

    # ---- 同步逻辑 ----

    def sync(self) -> SyncResult:
        """执行完整同步。"""
        result = SyncResult(provider=self.name)

        try:
            self._sync_departments(result)
        except Exception:
            logger.exception("LDAP 部门同步失败")
            result.errors.append("部门同步失败")
            result.success = False
            self._close_conn()
            return result

        try:
            self._sync_users(result)
        except Exception:
            logger.exception("LDAP 用户同步失败")
            result.errors.append("用户同步失败")
            result.success = False

        self._close_conn()
        return result

    def _sync_departments(self, result: SyncResult):
        """同步 LDAP OU → OrgNode。"""
        remote_depts = self.fetch_departments()
        if not remote_depts:
            return

        # 查找或创建根组织节点
        root_node, _ = OrgNode.objects.get_or_create(
            parent=None,
            defaults={"name": "LDAP", "sort_order": 0},
        )

        existing = {
            n.external_id: n
            for n in OrgNode.objects.filter(external_source="ldap").select_related("parent")
        }

        external_ids_seen = set()

        for dept in remote_depts:
            external_ids_seen.add(dept.external_id)

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
                    external_source="ldap",
                    external_id=dept.external_id,
                    sort_order=dept.order,
                )
                existing[dept.external_id] = node
                result.departments_created += 1

        for ext_id, node in existing.items():
            if ext_id not in external_ids_seen:
                node.delete()
                result.departments_deleted += 1

    def _sync_users(self, result: SyncResult):
        """同步 LDAP 用户 → User + UserProfile + OrgUser。"""
        remote_users = self.fetch_users()
        if not remote_users:
            return

        # 查找现有 LDAP org nodes（通过 ou 名称匹配）
        org_nodes_by_name = {}
        for node in OrgNode.objects.filter(external_source="ldap"):
            if node.external_id:
                org_nodes_by_name[node.name.lower()] = node

        external_ids_seen = set()

        for su in remote_users:
            external_ids_seen.add(su.external_id)

            try:
                user = User.objects.get(username=su.external_id)
                was_created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=su.external_id,
                    email=su.email or "",
                    first_name=su.display_name or su.name,
                    is_active=True,
                )
                UserProfile.objects.get_or_create(user=user)
                was_created = True

            if was_created:
                result.users_created += 1
            else:
                changed = False
                if su.email and su.email != user.email:
                    user.email = su.email
                    changed = True
                if su.display_name and su.display_name != user.first_name:
                    user.first_name = su.display_name
                    changed = True
                if changed:
                    user.save(update_fields=["email", "first_name"])
                result.users_updated += 1

            # 更新组织关联
            if su.department_external_ids:
                target_org_ids = set()
                for dept_name in su.department_external_ids:
                    node = org_nodes_by_name.get(dept_name.lower())
                    if node:
                        target_org_ids.add(node.id)

                if target_org_ids:
                    current_org_ids = set(
                        OrgUser.objects.filter(user=user).values_list("org_node_id", flat=True)
                    )
                    for org_id in target_org_ids - current_org_ids:
                        OrgUser.objects.get_or_create(user=user, org_node_id=org_id)
                    # 仅移除 LDAP 来源的组织关联
                    ldap_org_ids = set(
                        OrgNode.objects.filter(external_source="ldap").values_list("id", flat=True)
                    )
                    OrgUser.objects.filter(
                        user=user, org_node_id__in=current_org_ids & ldap_org_ids - target_org_ids
                    ).delete()
