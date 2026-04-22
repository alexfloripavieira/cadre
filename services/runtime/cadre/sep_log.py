from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class SEPLogger:
    def __init__(self, log_dir: str | Path) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def log_path(self, run_id: str) -> Path:
        return self._log_dir / f"{run_id}.log.yaml"

    def write(self, run_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        enriched = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            **entry,
        }
        with self.log_path(run_id).open("a", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(enriched, f, sort_keys=False, allow_unicode=True)
        return enriched

    def read(self, run_id: str) -> list[dict[str, Any]]:
        path = self.log_path(run_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return [doc for doc in yaml.safe_load_all(f) if doc is not None]
