# Signature: discord_client.py - Discord API 非同期通信・ガードレール管理モジュール
import asyncio
from typing import Any, Dict, List, Optional
import discord


class DiscordClientWrapper:
    """Discord API との非同期通信およびレートリミット（ガードレール）管理クラス"""

    def __init__(self, token: str, guild_id: int) -> None:
        self.token: str = token
        self.guild_id: int = guild_id
        intents: discord.Intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        self.client: discord.Client = discord.Client(intents=intents)

    async def start(self) -> None:
        """Discord API への接続を開始する"""
        await self.client.login(self.token)

    async def close(self) -> None:
        """接続を終了する"""
        await self.client.close()

    async def get_guild(self) -> discord.Guild:
        """指定した Guild オブジェクトを取得する"""
        guild: Optional[discord.Guild] = self.client.get_guild(self.guild_id)
        if guild is None:
            guild = await self.client.fetch_guild(self.guild_id)
        if guild is None:
            raise ValueError(f"Guild (ID: {self.guild_id}) が見つかりませんでした。")
        return guild

    async def rate_limit_wait(self, seconds: float = 1.2) -> None:
        """API 発行後のレートリミット回避用待機"""
        await asyncio.sleep(seconds)

    async def safe_api_call(self, coro_func: Any, *args: Any, **kwargs: Any) -> Any:
        """429 レートリミット検出時の自動再試行ラップ処理"""
        max_retries: int = 3
        for attempt in range(max_retries):
            try:
                result = await coro_func(*args, **kwargs)
                await self.rate_limit_wait(1.2)
                return result
            except discord.HTTPException as err:
                if err.status == 429:
                    retry_after: float = getattr(err, "retry_after", 2.0) + 0.5
                    print(f"HTTP 429 検出: {retry_after} 秒待機後再試行します...")
                    await asyncio.sleep(retry_after)
                else:
                    raise err
        raise RuntimeError("Discord API コールの最大再試行回数を超過しました。")

    async def fetch_current_state(self) -> Dict[str, Any]:
        """現況のサーバー構成（ロール・カテゴリー・チャンネル・設定）を取得する"""
        guild: discord.Guild = await self.get_guild()

        roles = await guild.fetch_roles()
        roles_data: List[Dict[str, Any]] = []
        for role in roles:
            roles_data.append({
                "id": role.id,
                "name": role.name,
                "color": str(role.color),
                "position": role.position,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
            })

        channels = await guild.fetch_channels()
        categories_data: List[Dict[str, Any]] = []
        channels_data: List[Dict[str, Any]] = []
        for ch in channels:
            if isinstance(ch, discord.CategoryChannel):
                categories_data.append({
                    "id": ch.id,
                    "name": ch.name,
                    "position": ch.position,
                })
            else:
                channels_data.append({
                    "id": ch.id,
                    "name": ch.name,
                    "type": str(ch.type),
                    "category_id": ch.category_id,
                    "position": ch.position,
                })

        server_settings_data: Dict[str, Any] = {
            "name": guild.name,
            "default_notifications": str(guild.default_notifications),
            "afk_channel_id": guild.afk_channel.id if guild.afk_channel else None,
            "afk_timeout": guild.afk_timeout,
            "system_channel_id": (
                guild.system_channel.id if guild.system_channel else None
            ),
        }

        return {
            "guild_id": guild.id,
            "roles": roles_data,
            "categories": categories_data,
            "channels": channels_data,
            "server_settings": server_settings_data,
        }
