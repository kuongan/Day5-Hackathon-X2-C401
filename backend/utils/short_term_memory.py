from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional


@dataclass
class MemoryTurn:
    user: str
    assistant: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShortTermMemoryStore:
    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns
        self._lock = threading.Lock()
        self._store: Dict[str, Deque[MemoryTurn]] = defaultdict(lambda: deque(maxlen=self.max_turns))

    def append_turn(self, conversation_id: str, user_text: str, assistant_text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not conversation_id:
            conversation_id = "default"
        turn = MemoryTurn(
            user=str(user_text or "").strip(),
            assistant=str(assistant_text or "").strip(),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._store[conversation_id].append(turn)

    def get_recent_turns(self, conversation_id: str, limit: Optional[int] = None) -> List[MemoryTurn]:
        if not conversation_id:
            conversation_id = "default"
        with self._lock:
            turns = list(self._store.get(conversation_id, []))
        if limit is not None and limit >= 0:
            return turns[-limit:]
        return turns

    def build_context(self, conversation_id: str, limit: int = 4) -> str:
        turns = self.get_recent_turns(conversation_id, limit=limit)
        if not turns:
            return ""

        lines = ["Lich su gan day:"]
        for idx, turn in enumerate(turns, start=1):
            lines.append(f"{idx}. User: {turn.user}")
            if turn.assistant:
                lines.append(f"   Assistant: {turn.assistant}")
        return "\n".join(lines)

    def clear(self, conversation_id: str) -> None:
        if not conversation_id:
            conversation_id = "default"
        with self._lock:
            self._store.pop(conversation_id, None)


_SHORT_TERM_MEMORY = ShortTermMemoryStore()


def record_turn(conversation_id: str, user_text: str, assistant_text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    _SHORT_TERM_MEMORY.append_turn(conversation_id, user_text, assistant_text, metadata=metadata)


def get_short_term_context(conversation_id: str, limit: int = 4) -> str:
    return _SHORT_TERM_MEMORY.build_context(conversation_id, limit=limit)


def clear_short_term_context(conversation_id: str) -> None:
    _SHORT_TERM_MEMORY.clear(conversation_id)
