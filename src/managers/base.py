# Signature: base.py - マネージャー基底クラス定義
from abc import ABC, abstractmethod
from typing import Any, Dict
from audit_logger import AuditLogger
from config_parser import ServerConfig
from discord_client import DiscordClientWrapper


class BaseManager(ABC):
    """各リソースマネージャーの基底抽象クラス"""

    def __init__(
        self, client_wrapper: DiscordClientWrapper, audit_logger: AuditLogger
    ) -> None:
        self.client_wrapper: DiscordClientWrapper = client_wrapper
        self.audit_logger: AuditLogger = audit_logger

    @abstractmethod
    async def apply(self, desired_config: ServerConfig) -> None:
        """状態の適用を行う抽象メソッド"""
        pass
