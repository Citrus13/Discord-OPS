# Signature: config_parser.py - Pydantic v2 スキーマおよび設定ファイル解析モジュール
import csv
from typing import Any, List, Optional
from pydantic import BaseModel, Field
import yaml


from pydantic import BaseModel, Field, field_validator


class PermissionOverwriteConfig(BaseModel):
    """チャンネル/カテゴリーの権限オーバーライト定義"""

    target: str
    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)

    @classmethod
    def from_dict_format(cls, data: Any) -> List["PermissionOverwriteConfig"]:
        """辞書形式の permissions データを List[PermissionOverwriteConfig] に変換する"""
        if isinstance(data, list):
            res = []
            for item in data:
                if isinstance(item, dict):
                    res.append(cls.model_validate(item))
            return res
        elif isinstance(data, dict):
            res = []
            for target_name, perms in data.items():
                allow_list = []
                deny_list = []
                if isinstance(perms, dict):
                    for perm_name, val in perms.items():
                        if val == "allow" or val is True:
                            allow_list.append(perm_name)
                        elif val == "deny" or val is False:
                            deny_list.append(perm_name)
                res.append(cls(target=str(target_name), allow=allow_list, deny=deny_list))
            return res
        return []


class ForumTagConfig(BaseModel):
    """フォーラムタグの定義"""

    name: str
    emoji: Optional[str] = None
    moderated: bool = False


class ForumSettingsConfig(BaseModel):
    """フォーラムチャンネルの固有設定"""

    default_reaction_emoji: Optional[str] = None
    tags: List[ForumTagConfig] = Field(default_factory=list)


class EmbedConfig(BaseModel):
    """初期配置 Embed の定義"""

    title: str
    description: str
    color: Optional[str] = "#3498DB"


class ChannelConfig(BaseModel):
    """チャンネルの定義"""

    name: str
    type: str = "text"
    topic: Optional[str] = None
    sync_permissions: bool = True
    permissions: List[PermissionOverwriteConfig] = Field(default_factory=list)
    forum_settings: Optional[ForumSettingsConfig] = None
    initial_embeds: List[EmbedConfig] = Field(default_factory=list)

    @field_validator("permissions", mode="before")
    @classmethod
    def parse_permissions(cls, v: Any) -> Any:
        return PermissionOverwriteConfig.from_dict_format(v)


class CategoryConfig(BaseModel):
    """カテゴリーの定義"""

    name: str
    permissions: List[PermissionOverwriteConfig] = Field(default_factory=list)
    channels: List[ChannelConfig] = Field(default_factory=list)

    @field_validator("permissions", mode="before")
    @classmethod
    def parse_permissions(cls, v: Any) -> Any:
        return PermissionOverwriteConfig.from_dict_format(v)


class RoleConfig(BaseModel):
    """ロールの定義"""

    name: str
    color: Optional[str] = "#000000"
    hoist: bool = False
    mentionable: bool = False


class ServerSettingsConfig(BaseModel):
    """サーバー設定の同期項目"""

    default_message_notifications: str = "only_mentions"
    afk_channel: Optional[str] = None
    afk_timeout: int = 900
    system_channel: Optional[str] = None


class GlobalSettingsConfig(BaseModel):
    """ツールの運用動作設定"""

    archive_category_name: str = "[Archive] 削除予定"
    protected_roles: List[str] = Field(default_factory=lambda: ["@everyone"])
    protected_channels: List[str] = Field(default_factory=list)


class ServerConfig(BaseModel):
    """メイン構成定義モデル"""

    version: str = "1.0"
    guild_id: int
    settings: GlobalSettingsConfig = Field(default_factory=GlobalSettingsConfig)
    server_settings: ServerSettingsConfig = Field(
        default_factory=ServerSettingsConfig
    )
    roles: List[RoleConfig] = Field(default_factory=list)
    categories: List[CategoryConfig] = Field(default_factory=list)


class MemberRecord(BaseModel):
    """CSV 名簿の 1 行に対応するデータモデル"""

    discord_user_id: int
    manage_number: str
    display_name: str
    assign_roles: List[str] = Field(default_factory=list)
    nickname_format: Optional[str] = "[{manage_number}] {display_name}"


def load_server_config(file_path: str) -> ServerConfig:
    """YAML 定義ファイルを読み込み Pydantic モデルへ変換する"""
    with open(file_path, "r", encoding="utf-8") as file:
        data: Any = yaml.safe_load(file)
    return ServerConfig.model_validate(data)


def load_members_csv(file_path: str) -> List[MemberRecord]:
    """CSV メンバー名簿を読み込み MemberRecord のリストへ変換する"""
    members: List[MemberRecord] = []
    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            roles_str: str = row.get("assign_roles", "")
            roles_list: List[str] = (
                [r.strip() for r in roles_str.split(",") if r.strip()]
                if roles_str
                else []
            )
            record = MemberRecord(
                discord_user_id=int(row["discord_user_id"]),
                manage_number=row.get("manage_number", ""),
                display_name=row.get("display_name", ""),
                assign_roles=roles_list,
                nickname_format=row.get("nickname_format"),
            )
            members.append(record)
    return members
