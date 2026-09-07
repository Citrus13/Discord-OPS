# Signature: audit_logger.py - JSONL 監査ログおよびスナップショット管理モジュール
from datetime import datetime
import json
import os
from typing import Any, Dict, Optional
import yaml


class AuditLogger:
    """操作単位の前後差分を JSONL へ永続化し、事前スナップショットを出力するクラス"""

    def __init__(self, exec_id: str, log_dir: str = "logs") -> None:
        self.exec_id: str = exec_id
        self.log_dir: str = log_dir
        self.seq: int = 0
        os.makedirs(self.log_dir, exist_ok=True)
        date_str: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path: str = os.path.join(
            self.log_dir, f"audit_{date_str}.jsonl"
        )

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        resource_name: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """操作前後の状態ログを JSONL に即時書き込む"""
        self.seq += 1
        record: Dict[str, Any] = {
            "seq": self.seq,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "exec_id": self.exec_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "resource_name": resource_name,
            "before": before or {},
            "after": after or {},
            "status": status,
            "error": error,
        }

        with open(self.log_file_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def save_snapshot(
        self, snapshot_data: Dict[str, Any], snapshot_dir: str = "snapshots"
    ) -> str:
        """適用直前のサーバー状態スナップショットを YAML 形式で永続化する"""
        os.makedirs(snapshot_dir, exist_ok=True)
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path: str = os.path.join(
            snapshot_dir, f"snapshot_{timestamp}.yaml"
        )
        with open(snapshot_path, "w", encoding="utf-8") as file:
            yaml.dump(snapshot_data, file, allow_unicode=True, sort_keys=False)
        return snapshot_path
