# Signature: forum_tag_manager.py - フォーラムタグ・初期リアクション同期モジュール
from typing import Any, Dict, List, Optional
import discord
from config_parser import CategoryConfig, ServerConfig
from managers.base import BaseManager


class ForumTagManager(BaseManager):
    """フォーラムチャンネルのタグおよび初期リアクション絵文字の設定クラス"""

    async def apply(self, desired_config: ServerConfig) -> None:
        guild: discord.Guild = await self.client_wrapper.get_guild()
        categories_config: List[CategoryConfig] = desired_config.categories

        for cat_cfg in categories_config:
            category: Optional[discord.CategoryChannel] = discord.utils.get(
                guild.categories, name=cat_cfg.name
            )
            if category is None:
                continue

            for ch_cfg in cat_cfg.channels:
                if ch_cfg.type != "forum" or not ch_cfg.forum_settings:
                    continue

                forum_ch: Optional[discord.ForumChannel] = discord.utils.get(
                    guild.forum_channels, name=ch_cfg.name, category_id=category.id
                )
                if forum_ch is None:
                    continue

                new_tags: List[discord.ForumTag] = []
                for tag_cfg in ch_cfg.forum_settings.tags:
                    emoji: Optional[str] = tag_cfg.emoji
                    new_tags.append(
                        discord.ForumTag(
                            name=tag_cfg.name,
                            emoji=emoji,
                            moderated=tag_cfg.moderated,
                        )
                    )

                if new_tags:
                    await self.client_wrapper.safe_api_call(
                        forum_ch.edit, available_tags=new_tags
                    )
                    self.audit_logger.log_action(
                        action="FORUM_TAGS_UPDATE",
                        resource_type="channel",
                        resource_id=str(forum_ch.id),
                        resource_name=forum_ch.name,
                        after={"tags_count": len(new_tags)},
                    )
