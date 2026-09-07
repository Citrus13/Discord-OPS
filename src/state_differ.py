# Signature: state_differ.py - Diff (Plan) 検出エンジン
from typing import Any, Dict, List
from config_parser import ServerConfig


class StateDiffer:
    """現在状態と定義ファイルの差分比較・Plan 生成を行うクラス"""

    def generate_plan(
        self, current_state: Dict[str, Any], desired_config: ServerConfig
    ) -> Dict[str, List[str]]:
        """差分計画（Plan）を構築し、作成・変更・移動予定の差分リストを返す"""
        plan: Dict[str, List[str]] = {
            "roles_to_create": [],
            "roles_to_update": [],
            "categories_to_create": [],
            "channels_to_create": [],
            "channels_to_archive": [],
        }

        # 1. ロール差分
        existing_role_names: set[str] = {
            r["name"] for r in current_state.get("roles", [])
        }
        for role_cfg in desired_config.roles:
            if role_cfg.name not in existing_role_names:
                plan["roles_to_create"].append(
                    f"+ [Role] {role_cfg.name} (Color: {role_cfg.color})"
                )

        # 2. カテゴリー・チャンネル差分
        existing_cat_names: set[str] = {
            c["name"] for c in current_state.get("categories", [])
        }
        defined_channel_names: set[str] = set()

        for cat_cfg in desired_config.categories:
            if cat_cfg.name not in existing_cat_names:
                plan["categories_to_create"].append(f"+ [Category] {cat_cfg.name}")

            for ch_cfg in cat_cfg.channels:
                defined_channel_names.add(ch_cfg.name)

        existing_channel_names: set[str] = {
            ch["name"] for ch in current_state.get("channels", [])
        }
        for cat_cfg in desired_config.categories:
            for ch_cfg in cat_cfg.channels:
                if ch_cfg.name not in existing_channel_names:
                    plan["channels_to_create"].append(
                        f"+ [Channel] {ch_cfg.name} (Type: {ch_cfg.type}, Category: {cat_cfg.name})"
                    )

        # 3. アーカイブ移動対象（未定義チャンネル）
        protected_channels: set[str] = set(
            desired_config.settings.protected_channels
        )
        archive_name: str = desired_config.settings.archive_category_name

        for ch in current_state.get("channels", []):
            if ch["type"] == "category":
                continue
            if (
                ch["name"] not in defined_channel_names
                and ch["name"] not in protected_channels
            ):
                plan["channels_to_archive"].append(
                    f"~ [Archive Move] {ch['name']} -> {archive_name}"
                )

        return plan
