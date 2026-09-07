# Signature: member_manager.py - 名簿同期・ロール一括付与・ニックネーム適用モジュール
from typing import Any, Dict, List, Optional
import discord
from config_parser import MemberRecord
from managers.base import BaseManager


class MemberManager(BaseManager):
    """CSV 名簿と Discord メンバーのロール付与・ニックネーム同期を行うクラス"""

    async def sync_members(self, member_records: List[MemberRecord]) -> None:
        """名簿リストに基づいて各メンバーのロールおよびニックネームを適用する"""
        guild: discord.Guild = await self.client_wrapper.get_guild()

        for record in member_records:
            user_id: int = record.discord_user_id
            member: Optional[discord.Member] = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    print(
                        f"警告: ユーザー ID {user_id} ({record.display_name}) がサーバー内に見つかりません。"
                    )
                    continue

            # ニックネームの更新
            if record.nickname_format:
                new_nickname: str = record.nickname_format.format(
                    manage_number=record.manage_number,
                    display_name=record.display_name,
                )
                if member.nick != new_nickname:
                    before_nick: Optional[str] = member.nick
                    try:
                        await self.client_wrapper.safe_api_call(
                            member.edit, nick=new_nickname
                        )
                        self.audit_logger.log_action(
                            action="MEMBER_NICKNAME_UPDATE",
                            resource_type="member",
                            resource_id=str(member.id),
                            resource_name=member.name,
                            before={"nickname": before_nick},
                            after={"nickname": new_nickname},
                        )
                    except discord.Forbidden:
                        print(
                            f"権限エラー: ユーザー {member.name} のニックネーム変更権限がありません。"
                        )

            # ロールの割り当て
            for role_name in record.assign_roles:
                role: Optional[discord.Role] = discord.utils.get(
                    guild.roles, name=role_name
                )
                if role is not None and role not in member.roles:
                    await self.client_wrapper.safe_api_call(
                        member.add_roles, role
                    )
                    self.audit_logger.log_action(
                        action="MEMBER_ROLE_ASSIGN",
                        resource_type="member",
                        resource_id=str(member.id),
                        resource_name=member.name,
                        after={"role_id": str(role.id), "role_name": role.name},
                    )

    async def export_members_to_csv(self, output_path: str) -> None:
        """現在の Discord サーバーメンバー一覧を取得し CSV ファイルとして出力・保存する"""
        import csv
        guild: discord.Guild = await self.client_wrapper.get_guild()
        members = await guild.fetch_members(limit=None).flatten() if hasattr(guild.fetch_members(limit=None), "flatten") else [m async for m in guild.fetch_members(limit=None)]

        fieldnames = ["discord_user_id", "manage_number", "display_name", "assign_roles", "nickname_format"]
        
        records: List[Dict[str, Any]] = []
        for idx, member in enumerate(members, start=1):
            if member.bot:
                continue
            
            # @everyone を除く付与ロール名リスト
            assigned_roles = [r.name for r in member.roles if r.name != "@everyone"]
            roles_str = ",".join(assigned_roles)

            display_name = member.global_name or member.name
            record = {
                "discord_user_id": str(member.id),
                "manage_number": f"M{idx:04d}",
                "display_name": display_name,
                "assign_roles": roles_str,
                "nickname_format": "[{manage_number}] {display_name}",
            }
            records.append(record)

        import os
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"メンバー一覧 ({len(records)} 件) を {output_path} へエクスポートしました。")

    async def apply(self, desired_state: Dict[str, Any]) -> None:
        """BaseManager の抽象メソッド実装"""
        pass
