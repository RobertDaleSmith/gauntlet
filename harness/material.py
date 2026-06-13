"""📦 Material handling pillar — capture/normalize state, persist, replay.

Clean interface for getting game state in and results out. Every checkpoint is
persisted to SQLite so a run can be replayed from any frame forward.
"""
from __future__ import annotations

import json
import sqlite3

from .checkpoints import CheckpointResult
from .types import Action, GameState


class MaterialHandler:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id  TEXT NOT NULL,
                frame   INTEGER NOT NULL,
                action  TEXT NOT NULL,
                state   TEXT NOT NULL,
                results TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def normalize(self, raw: dict) -> GameState:
        """Raw game-state dict (from the browser) -> typed GameState."""
        return GameState(
            frame=raw.get("frame", 0),
            score=raw.get("score", 0),
            lines=raw.get("lines", 0),
            level=raw.get("level", 1),
            stack_height=raw.get("stack_height", 0),
            holes=raw.get("holes", 0),
            game_over=raw.get("game_over", False),
            raw=raw,
        )

    def persist(
        self,
        run_id: str,
        frame: int,
        action: Action,
        state: GameState,
        results: list[CheckpointResult],
    ) -> None:
        self.conn.execute(
            "INSERT INTO checkpoints (run_id, frame, action, state, results) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                frame,
                json.dumps({"buttons": list(action.buttons), "hold": action.hold_frames}),
                json.dumps(
                    {
                        "score": state.score,
                        "lines": state.lines,
                        "level": state.level,
                        "stack_height": state.stack_height,
                        "holes": state.holes,
                        "game_over": state.game_over,
                    }
                ),
                json.dumps([r.to_dict() for r in results]),
            ),
        )
        self.conn.commit()

    def replay(self, run_id: str) -> list[dict]:
        """Return every persisted checkpoint for a run, in order."""
        rows = self.conn.execute(
            "SELECT frame, action, state, results FROM checkpoints "
            "WHERE run_id = ? ORDER BY frame ASC",
            (run_id,),
        ).fetchall()
        return [
            {
                "frame": r["frame"],
                "action": json.loads(r["action"]),
                "state": json.loads(r["state"]),
                "results": json.loads(r["results"]),
            }
            for r in rows
        ]

    def load_state(self, run_id: str, frame: int) -> GameState | None:
        """Load the state snapshot at a given frame (for replay-from-checkpoint)."""
        row = self.conn.execute(
            "SELECT state FROM checkpoints WHERE run_id = ? AND frame = ?",
            (run_id, frame),
        ).fetchone()
        if row is None:
            return None
        s = json.loads(row["state"])
        return GameState(
            frame=frame,
            score=s["score"],
            lines=s["lines"],
            level=s["level"],
            stack_height=s["stack_height"],
            holes=s["holes"],
            game_over=s["game_over"],
        )
