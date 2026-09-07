# Signature: server_setting_manager.py - サーバー全体設定同期モジュール
from typing import Any, Dict, Optional
import discord
from config_parser import ServerConfig, ServerSettingsConfig
from managers.base import BaseManager


class ServerSettingManager(BaseManager):
    """AFK チャンネル、システム通知チャンネル、デフォルト通知レベルの同期クラス"""

    async def apply(self, desired_config: ServerConfig) -> None:
        guild: discord.Guild = await self.client_wrapper.get_guild()
        settings_cfg: ServerSettingsConfig = desired_config.server_settings

        afk_channel: Optional[discord.VoiceChannel] = None
        if settings_cfg.afk_channel:
            found_ch = discord.utils.get(
                guild.voice_channels, name=settings_cfg.afk_channel
            )
            if isinstance(found_ch, discord.VoiceChannel):
                afk_channel = found_ch

        system_channel: Optional[discord.TextChannel] = None
        if settings_cfg.system_channel:
            found_ch = discord.utils.get(
                guild.text_channels, name=settings_cfg.system_channel
            )
            if isinstance(found_ch, discord.TextChannel):
                system_channel = found_ch

        # デフォルト通知レベルの変換
        default_notif: discord.NotificationLevel = (
            discord.NotificationLevel.only_mentions
            if settings_cfg.default_message_notifications == "only_mentions"
            else discord.NotificationLevel.all_messages
        )

        edit_kwargs: Dict[str, Any] = {}
        if (
            afk_channel is not None
            and guild.afk_channel != afk_channel
        ):
            edit_kwargs["afk_channel"] = afk_channel
        if settings_cfg.afk_timeout and guild.afk_timeout != settings_cfg.afk_timeout:
            edit_kwargs["afk_timeout"] = settings_cfg.afk_timeout
        if (
            system_channel is not None
            and guild.system_channel != system_channel
        ):
            edit_kwargs["system_channel"] = system_channel
        if guild.default_notifications != default_notif:
            edit_kwargs["default_notifications"] = default_notif

        if edit_kwargs:
            before_data: Dict[str, Any] = {
                "afk_channel_id": (
                    guild.afk_channel.id if guild.afk_channel else None
                ),
                "afk_timeout": guild.afk_timeout,
                "system_channel_id": (
                    guild.system_channel.id if guild.system_channel else None
                ),
            }
            await self.client_wrapper.safe_api_call(
                guild.edit, **edit_kwargs
            )
            self.audit_logger.log_action(
                action="GUILD_SETTINGS_UPDATE",
                resource_type="guild",
                resource_id=str(guild.id),
                resource_name=guild.name,
                before=before_data,
                after={
                    "afk_timeout": settings_cfg.afk_timeout,
                    "default_notifications": settings_cfg.default_message_notifications,
                },
            )
