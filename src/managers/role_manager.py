# Signature: role_manager.py - ロール作成・属性・ヒエラルキー管理モジュール
from typing import Any, Dict, List, Optional
import discord
from config_parser import RoleConfig, ServerConfig
from managers.base import BaseManager


class RoleManager(BaseManager):
    """ロールの作成、編集、削除およびヒエラルキー制限の検証を行うクラス"""

    async def check_hierarchy_and_limits(
        self, guild: discord.Guild, roles_config: List[RoleConfig]
    ) -> None:
        """ガードレール: 制限数およびロールヒエラルキー制限の事前検証"""
        if len(guild.roles) + len(roles_config) > 250:
            raise ValueError(
                "制限エラー: サーバー内のロール総数が 250 を超えてしまいます。"
            )

        bot_member: Optional[discord.Member] = guild.me
        if bot_member is None:
            return

        top_role: discord.Role = bot_member.top_role
        for r_cfg in roles_config:
            existing_role: Optional[discord.Role] = discord.utils.get(
                guild.roles, name=r_cfg.name
            )
            if existing_role and existing_role >= top_role:
                raise PermissionError(
                    f"ヒエラルキー制限エラー: ロール ({r_cfg.name}) は Bot の最上位ロール以上の位置にあるため操作できません。"
                )

    async def apply(self, desired_config: ServerConfig) -> None:
        """定義ファイルに基づきロールの作成・更新および不要ロールの自動削除を実行する"""
        guild: discord.Guild = await self.client_wrapper.get_guild()
        roles_config: List[RoleConfig] = desired_config.roles
        protected_roles: List[str] = desired_config.settings.protected_roles

        await self.check_hierarchy_and_limits(guild, roles_config)

        defined_role_names: set[str] = {r.name for r in roles_config}

        # 1. 不要ロールの自動削除
        existing_roles = await guild.fetch_roles()
        bot_member = guild.me
        top_role = bot_member.top_role if bot_member else None

        for role in existing_roles:
            if role.is_default() or role.is_integration() or role.managed:
                continue
            if role.name in defined_role_names or role.name in protected_roles:
                continue
            if top_role and role >= top_role:
                continue

            # 不要ロールの削除
            before_state = {"name": role.name, "id": str(role.id)}
            try:
                await self.client_wrapper.safe_api_call(role.delete)
                self.audit_logger.log_action(
                    action="ROLE_DELETE",
                    resource_type="role",
                    resource_id=str(role.id),
                    resource_name=role.name,
                    before=before_state,
                )
            except discord.HTTPException as err:
                print(f"ロール削除スキップ ({role.name}): {err}")

        # 2. 定義ロールの作成・更新
        for r_cfg in roles_config:
            existing_roles = await guild.fetch_roles()
            existing_role: Optional[discord.Role] = discord.utils.get(
                existing_roles, name=r_cfg.name
            )
            color_int: int = int(r_cfg.color.lstrip("#"), 16) if r_cfg.color else 0
            color: discord.Color = discord.Color(color_int)

            if existing_role is None:
                # ロール新規作成
                new_role: discord.Role = await self.client_wrapper.safe_api_call(
                    guild.create_role,
                    name=r_cfg.name,
                    color=color,
                    hoist=r_cfg.hoist,
                    mentionable=r_cfg.mentionable,
                )
                self.audit_logger.log_action(
                    action="ROLE_CREATE",
                    resource_type="role",
                    resource_id=str(new_role.id),
                    resource_name=new_role.name,
                    after={
                        "name": new_role.name,
                        "color": str(new_role.color),
                        "hoist": new_role.hoist,
                    },
                )
            else:
                # 属性更新の検証
                needs_edit: bool = False
                before_state: Dict[str, Any] = {
                    "name": existing_role.name,
                    "color": str(existing_role.color),
                    "hoist": existing_role.hoist,
                }
                if (
                    existing_role.color != color
                    or existing_role.hoist != r_cfg.hoist
                    or existing_role.mentionable != r_cfg.mentionable
                ):
                    needs_edit = True

                if needs_edit:
                    await self.client_wrapper.safe_api_call(
                        existing_role.edit,
                        color=color,
                        hoist=r_cfg.hoist,
                        mentionable=r_cfg.mentionable,
                    )
                    self.audit_logger.log_action(
                        action="ROLE_UPDATE",
                        resource_type="role",
                        resource_id=str(existing_role.id),
                        resource_name=existing_role.name,
                        before=before_state,
                        after={
                            "name": existing_role.name,
                            "color": str(color),
                            "hoist": r_cfg.hoist,
                        },
                    )
