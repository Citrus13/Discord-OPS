# Signature: onboarding_manager.py - 初期案内 Embed 配置モジュール
from typing import Any, Dict, List, Optional
import discord
from config_parser import CategoryConfig, ServerConfig
from managers.base import BaseManager


class OnboardingManager(BaseManager):
    """テキストチャンネルへの初期案内 Embed メッセージ配置クラス"""

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
                if not ch_cfg.initial_embeds:
                    continue

                text_ch: Optional[discord.TextChannel] = discord.utils.get(
                    guild.text_channels, name=ch_cfg.name, category_id=category.id
                )
                if text_ch is None:
                    continue

                # 既にメッセージが存在するかチェック
                history = [msg async for msg in text_ch.history(limit=5)]
                if len(history) > 0:
                    continue

                for embed_cfg in ch_cfg.initial_embeds:
                    color_int: int = (
                        int(embed_cfg.color.lstrip("#"), 16)
                        if embed_cfg.color
                        else 0x3498DB
                    )
                    embed = discord.Embed(
                        title=embed_cfg.title,
                        description=embed_cfg.description,
                        color=color_int,
                    )
                    sent_msg: discord.Message = (
                        await self.client_wrapper.safe_api_call(
                            text_ch.send, embed=embed
                        )
                    )
                    self.audit_logger.log_action(
                        action="EMBED_SEND",
                        resource_type="message",
                        resource_id=str(sent_msg.id),
                        resource_name=ch_cfg.name,
                        after={"title": embed_cfg.title},
                    )
