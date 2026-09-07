# Signature: rollback_engine.py - 監査ログ逆順ロールバックエンジン
import json
import os
from typing import Any, Dict, List, Optional
import discord
from discord_client import DiscordClientWrapper


class RollbackEngine:
    """JSONL 監査ログを逆順読み込みし原状復帰を行うクラス"""

    def __init__(self, client_wrapper: DiscordClientWrapper) -> None:
        self.client_wrapper: DiscordClientWrapper = client_wrapper

    async def execute_rollback(self, jsonl_log_path: str) -> None:
        """監査ログファイルを反転読み込みし、逆操作を発行する"""
        if not os.path.exists(jsonl_log_path):
            raise FileNotFoundError(
                f"監査ログファイル ({jsonl_log_path}) が見つかりません。"
            )

        records: List[Dict[str, Any]] = []
        with open(jsonl_log_path, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

        # LIFO (逆順) 処理
        records.reverse()
        guild: discord.Guild = await self.client_wrapper.get_guild()

        for rec in records:
            if rec.get("status") != "SUCCESS":
                continue

            action: str = rec.get("action", "")
            res_id: int = int(rec.get("resource_id", 0))

            try:
                if action in ("ROLE_CREATE", "CATEGORY_CREATE", "CHANNEL_CREATE"):
                    # 作成されたエンティティを削除
                    if action == "ROLE_CREATE":
                        role: Optional[discord.Role] = guild.get_role(res_id)
                        if role:
                            await self.client_wrapper.safe_api_call(role.delete)
                            print(f"ロールバック: ロール {role.name} を削除しました。")

                    elif action in ("CATEGORY_CREATE", "CHANNEL_CREATE"):
                        channel: Optional[discord.abc.GuildChannel] = (
                            guild.get_channel(res_id)
                        )
                        if channel:
                            await self.client_wrapper.safe_api_call(
                                channel.delete
                            )
                            print(
                                f"ロールバック: チャンネル/カテゴリー {channel.name} を削除しました。"
                            )

                elif action == "CHANNEL_MOVE":
                    channel = guild.get_channel(res_id)
                    before_cat_id_str = rec.get("before", {}).get("parent_id")
                    if channel and before_cat_id_str:
                        target_cat: Optional[discord.CategoryChannel] = None
                        if before_cat_id_str != "None":
                            target_cat = guild.get_channel(int(before_cat_id_str))  # type: ignore
                        await self.client_wrapper.safe_api_call(
                            channel.edit, category=target_cat
                        )
                        print(
                            f"ロールバック: チャンネル {channel.name} の移動を元に戻しました。"
                        )

                elif action == "MEMBER_ROLE_ASSIGN":
                    member: Optional[discord.Member] = guild.get_member(res_id)
                    role_id_str = rec.get("after", {}).get("role_id")
                    if member and role_id_str:
                        role = guild.get_role(int(role_id_str))
                        if role and role in member.roles:
                            await self.client_wrapper.safe_api_call(
                                member.remove_roles, role
                            )
                            print(
                                f"ロールバック: メンバー {member.name} からロール {role.name} を剥奪しました。"
                            )

                elif action == "MEMBER_NICKNAME_UPDATE":
                    member = guild.get_member(res_id)
                    before_nick = rec.get("before", {}).get("nickname")
                    if member:
                        await self.client_wrapper.safe_api_call(
                            member.edit, nick=before_nick
                        )
                        print(
                            f"ロールバック: メンバー {member.name} のニックネームを元に戻しました。"
                        )

            except Exception as err:
                print(
                    f"ロールバック警告: リソース (ID: {res_id}) の復元中にエラーが発生しました: {err}"
                )
