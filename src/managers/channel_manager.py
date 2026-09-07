# Signature: channel_manager.py - カテゴリー・チャンネル・直接権限同期・空カテゴリー削除モジュール
from typing import Any, Dict, List, Optional
import discord
from config_parser import CategoryConfig, ChannelConfig, ServerConfig
from managers.base import BaseManager


class ChannelManager(BaseManager):
    """カテゴリー、チャンネルの作成・直接権限オーバーライト同期・空カテゴリーの削除を行うクラス"""

    async def _ensure_archive_category(
        self, guild: discord.Guild, archive_base_name: str
    ) -> discord.CategoryChannel:
        """1カテゴリー上限 50 チャンネルを考慮し、空きのあるアーカイブカテゴリーを取得または作成する"""
        all_channels = await guild.fetch_channels()
        categories = [
            c for c in all_channels if isinstance(c, discord.CategoryChannel)
        ]

        # 既存のアーカイブカテゴリーから容量 50 未満のものを探索
        for cat in categories:
            if cat.name.startswith(archive_base_name):
                cat_channels = [
                    ch for ch in all_channels if ch.category_id == cat.id
                ]
                if len(cat_channels) < 48:
                    return cat

        archive_count: int = len(
            [c for c in categories if c.name.startswith(archive_base_name)]
        )
        new_archive_name: str = (
            f"{archive_base_name} {archive_count + 1}"
            if archive_count > 0
            else archive_base_name
        )

        archive_cat = await self.client_wrapper.safe_api_call(
            guild.create_category, name=new_archive_name
        )
        self.audit_logger.log_action(
            action="CATEGORY_CREATE",
            resource_type="category",
            resource_id=str(archive_cat.id),
            resource_name=new_archive_name,
            after={"name": new_archive_name},
        )
        return archive_cat

    async def apply(self, desired_config: ServerConfig) -> None:
        """カテゴリーおよびチャンネルの同期・権限完全制限処理を実行する"""
        guild: discord.Guild = await self.client_wrapper.get_guild()
        categories_config: List[CategoryConfig] = desired_config.categories
        archive_name: str = desired_config.settings.archive_category_name
        protected_channels: List[str] = desired_config.settings.protected_channels

        defined_category_names: set[str] = set()
        defined_channel_names: set[str] = set()

        # 1-3. カテゴリー・チャンネルの作成および権限・並び順の適用
        for idx, cat_cfg in enumerate(categories_config):
            defined_category_names.add(cat_cfg.name)
            all_channels = await guild.fetch_channels()
            categories = [
                c for c in all_channels if isinstance(c, discord.CategoryChannel)
            ]
            category: Optional[discord.CategoryChannel] = discord.utils.get(
                categories, name=cat_cfg.name
            )

            # カテゴリーの取得または作成
            if category is None:
                category = await self.client_wrapper.safe_api_call(
                    guild.create_category, name=cat_cfg.name, position=idx
                )
                self.audit_logger.log_action(
                    action="CATEGORY_CREATE",
                    resource_type="category",
                    resource_id=str(category.id),
                    resource_name=category.name,
                    after={"name": category.name, "position": idx},
                )
            else:
                # 並び順（position）の同期
                if category.position != idx:
                    await self.client_wrapper.safe_api_call(
                        category.edit, position=idx
                    )

            # 各チャンネルの作成
            cat_channels: List[discord.abc.GuildChannel] = []
            for ch_cfg in cat_cfg.channels:
                defined_channel_names.add(ch_cfg.name)
                existing_ch = discord.utils.get(
                    all_channels, name=ch_cfg.name, category_id=category.id
                )

                if existing_ch is None:
                    if ch_cfg.type == "voice":
                        new_ch = await self.client_wrapper.safe_api_call(
                            guild.create_voice_channel,
                            name=ch_cfg.name,
                            category=category,
                        )
                    elif ch_cfg.type == "forum":
                        new_ch = await self.client_wrapper.safe_api_call(
                            guild.create_forum,
                            name=ch_cfg.name,
                            category=category,
                        )
                    else:
                        new_ch = await self.client_wrapper.safe_api_call(
                            guild.create_text_channel,
                            name=ch_cfg.name,
                            category=category,
                            topic=ch_cfg.topic,
                        )

                    self.audit_logger.log_action(
                        action="CHANNEL_CREATE",
                        resource_type="channel",
                        resource_id=str(new_ch.id),
                        resource_name=new_ch.name,
                        after={
                            "name": new_ch.name,
                            "type": str(new_ch.type),
                            "category_id": category.id,
                        },
                    )
                    cat_channels.append(new_ch)
                else:
                    cat_channels.append(existing_ch)

            # 権限オーバーライトの適用 (カテゴリー本体)
            roles = await guild.fetch_roles()
            defined_cat_targets = set()
            for perm_cfg in cat_cfg.permissions:
                target_obj: Optional[discord.Role | discord.Member] = None
                if perm_cfg.target == "@everyone":
                    target_obj = guild.default_role
                    defined_cat_targets.add(guild.default_role)
                else:
                    target_obj = discord.utils.get(roles, name=perm_cfg.target)
                    if target_obj is not None:
                        defined_cat_targets.add(target_obj)

                if target_obj is not None:
                    allow_kwargs = {p: True for p in perm_cfg.allow}
                    deny_kwargs = {p: False for p in perm_cfg.deny}
                    overwrite = discord.PermissionOverwrite(
                        **allow_kwargs, **deny_kwargs
                    )
                    await self.client_wrapper.safe_api_call(
                        category.set_permissions, target_obj, overwrite=overwrite
                    )

            # カテゴリーの未定義オーバーライトを完全消去
            for existing_cat_target in list(category.overwrites.keys()):
                if existing_cat_target not in defined_cat_targets:
                    await self.client_wrapper.safe_api_call(
                        category.set_permissions, existing_cat_target, overwrite=None
                    )

            # チャンネル固有の権限オーバーライトの適用またはカテゴリー完全同期
            for ch_cfg in cat_cfg.channels:
                ch_obj = discord.utils.get(cat_channels, name=ch_cfg.name)
                if not ch_obj:
                    continue

                if ch_cfg.permissions:
                    defined_ch_targets = set()
                    for ch_perm_cfg in ch_cfg.permissions:
                        ch_target_obj: Optional[discord.Role | discord.Member] = None
                        if ch_perm_cfg.target == "@everyone":
                            ch_target_obj = guild.default_role
                            defined_ch_targets.add(guild.default_role)
                        else:
                            ch_target_obj = discord.utils.get(roles, name=ch_perm_cfg.target)
                            if ch_target_obj is not None:
                                defined_ch_targets.add(ch_target_obj)

                        if ch_target_obj is not None:
                            ch_allow_kwargs = {p: True for p in ch_perm_cfg.allow}
                            ch_deny_kwargs = {p: False for p in ch_perm_cfg.deny}
                            ch_overwrite = discord.PermissionOverwrite(
                                **ch_allow_kwargs, **ch_deny_kwargs
                            )
                            await self.client_wrapper.safe_api_call(
                                ch_obj.set_permissions, ch_target_obj, overwrite=ch_overwrite
                            )

                    # チャンネルの未定義オーバーライトを完全消去（過去のゴミ権限を削除）
                    for existing_ch_target in list(ch_obj.overwrites.keys()):
                        if existing_ch_target not in defined_ch_targets:
                            await self.client_wrapper.safe_api_call(
                                ch_obj.set_permissions, existing_ch_target, overwrite=None
                            )
                else:
                    if not ch_obj.permissions_synced or ch_obj.overwrites != category.overwrites:
                        await self.client_wrapper.safe_api_call(
                            ch_obj.edit, sync_permissions=True
                        )

            # カテゴリー内の未定義チャンネルのクリーンアップ
            current_cat_channels = [
                ch for ch in all_channels if ch.category_id == category.id
            ]
            defined_in_cat = {ch_c.name for ch_c in cat_cfg.channels}
            for existing_ch in current_cat_channels:
                if (
                    existing_ch.name not in defined_in_cat
                    and existing_ch.name not in protected_channels
                ):
                    ch_del_name = existing_ch.name
                    await self.client_wrapper.safe_api_call(existing_ch.delete)
                    self.audit_logger.log_action(
                        action="CHANNEL_DELETE",
                        resource_type="channel",
                        resource_id=str(existing_ch.id),
                        resource_name=ch_del_name,
                        before={"parent_id": str(category.id)},
                    )

        # 4. 未定義カテゴリー内の旧チャンネル削除および未定義カテゴリー自体の完全クリーンアップ
        all_channels = await guild.fetch_channels()
        categories = [
            c for c in all_channels if isinstance(c, discord.CategoryChannel)
        ]
        for cat in categories:
            if cat.name in defined_category_names or cat.name.startswith(archive_name):
                continue

            children = [ch for ch in all_channels if ch.category_id == cat.id]
            for child in children:
                ch_name = child.name
                await self.client_wrapper.safe_api_call(child.delete)
                self.audit_logger.log_action(
                    action="CHANNEL_DELETE",
                    resource_type="channel",
                    resource_id=str(child.id),
                    resource_name=ch_name,
                    before={"parent_id": str(cat.id)},
                )

            await self.client_wrapper.safe_api_call(cat.delete)
            self.audit_logger.log_action(
                action="CATEGORY_DELETE",
                resource_type="category",
                resource_id=str(cat.id),
                resource_name=cat.name,
                before={"name": cat.name},
            )
