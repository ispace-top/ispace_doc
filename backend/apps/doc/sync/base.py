"""目录同步抽象基类。

定义统一的同步接口，支持企业微信、钉钉、LDAP 等不同来源。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SyncDepartment:
    """同步用的部门数据。"""
    external_id: str
    name: str
    parent_external_id: str | None = None
    order: int = 0


@dataclass
class SyncUser:
    """同步用的用户数据。"""
    external_id: str
    name: str
    display_name: str = ""
    email: str = ""
    mobile: str = ""
    avatar_url: str = ""
    department_external_ids: list[str] = field(default_factory=list)
    is_leader: bool = False
    position: str = ""
    status: str = "active"  # active / inactive


@dataclass
class SyncResult:
    """同步结果。"""
    provider: str
    departments_created: int = 0
    departments_updated: int = 0
    departments_deleted: int = 0
    users_created: int = 0
    users_updated: int = 0
    users_deactivated: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    success: bool = True


class DirectorySyncBackend(ABC):
    """目录同步后端抽象基类。"""

    name: str = "base"

    @abstractmethod
    def fetch_departments(self) -> list[SyncDepartment]:
        """从远端获取部门列表。"""

    @abstractmethod
    def fetch_users(self) -> list[SyncUser]:
        """从远端获取用户列表。"""
