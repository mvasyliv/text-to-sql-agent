"""File-based schema snapshot repository."""

from __future__ import annotations

import json
from pathlib import Path

from text_to_sql_agent.models import DatabaseSchema, SchemaSnapshotRef


class SchemaSnapshotRepository:
    """Persist and retrieve canonical schema snapshots on disk."""

    def __init__(self, storage_dir: str | Path) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, schema: DatabaseSchema) -> SchemaSnapshotRef:
        """Persist a schema snapshot and return its reference."""
        snapshot_ref = SchemaSnapshotRef(
            snapshot_id=schema.snapshot_id,
            database_id=schema.database_id,
            dialect=schema.dialect,
            created_at=schema.created_at,
            table_count=len(schema.tables),
            status="fresh",
        )

        payload = {
            "snapshot_ref": snapshot_ref.model_dump(mode="json"),
            "schema": schema.model_dump(mode="json"),
        }
        self._snapshot_path(schema.snapshot_id).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return snapshot_ref

    def load(self, snapshot_id: str) -> DatabaseSchema:
        """Load a schema snapshot by identifier."""
        snapshot_path = self._snapshot_path(snapshot_id)
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_id}")

        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return DatabaseSchema.model_validate(payload["schema"])

    def list(self, database_id: str | None = None) -> list[SchemaSnapshotRef]:
        """List stored snapshot references, optionally filtered by database."""
        references: list[SchemaSnapshotRef] = []

        for snapshot_path in sorted(self.storage_dir.glob("*.json")):
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            reference = SchemaSnapshotRef.model_validate(payload["snapshot_ref"])
            if database_id is not None and reference.database_id != database_id:
                continue
            references.append(reference)

        return references

    def delete(self, snapshot_id: str) -> bool:
        """Delete a stored snapshot if it exists."""
        snapshot_path = self._snapshot_path(snapshot_id)
        if not snapshot_path.exists():
            return False

        snapshot_path.unlink()
        return True

    def _snapshot_path(self, snapshot_id: str) -> Path:
        """Resolve the on-disk snapshot file path."""
        return self.storage_dir / f"{snapshot_id}.json"