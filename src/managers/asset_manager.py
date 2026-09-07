# Signature: asset_manager.py - 絵文字アセット一括同期モジュール
import os
from typing import Any, Dict, Optional
import discord
from managers.base import BaseManager


class AssetManager(BaseManager):
    """assets/emojis/ ディレクトリ内の画像を検証し一括でアップロードするクラス"""

    async def upload_emojis(self, emoji_dir: str = "assets/emojis") -> None:
        """指定されたディレクトリから絵文字を一括作成する"""
        guild: discord.Guild = await self.client_wrapper.get_guild()
        if not os.path.exists(emoji_dir):
            os.makedirs(emoji_dir, exist_ok=True)
            return

        for filename in os.listdir(emoji_dir):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                continue

            emoji_name: str = os.path.splitext(filename)[0]
            existing_emoji: Optional[discord.Emoji] = discord.utils.get(
                guild.emojis, name=emoji_name
            )

            if existing_emoji is None:
                file_path: str = os.path.join(emoji_dir, filename)
                with open(file_path, "rb") as image_file:
                    image_data: bytes = image_file.read()
                    new_emoji: discord.Emoji = (
                        await self.client_wrapper.safe_api_call(
                            guild.create_custom_emoji,
                            name=emoji_name,
                            image=image_data,
                        )
                    )
                    self.audit_logger.log_action(
                        action="EMOJI_CREATE",
                        resource_type="emoji",
                        resource_id=str(new_emoji.id),
                        resource_name=new_emoji.name,
                        after={"name": new_emoji.name},
                    )

    async def apply(self, desired_state: Dict[str, Any]) -> None:
        """BaseManager 抽象メソッド実装"""
        await self.upload_emojis()
