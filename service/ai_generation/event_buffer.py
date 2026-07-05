"""SSE event buffer for client reconnection support.

When an SSE client disconnects (tab switch, page navigation), the backend task
continues executing. This module buffers SSE events so that when the client
returns, it can replay missed events instead of losing real-time progress.

Architecture:
  - Each session gets an EventBuffer that stores events with sequence numbers
  - Live asyncio.Queues are registered globally so reconnect clients can attach
  - On reconnect: replay buffered events → attach to live queue (if still running)
  - Falls back gracefully: no Redis dependency, in-memory only with TTL cleanup
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

_log = logging.getLogger("event_buffer")

# Buffer auto-cleanup after this many seconds (15 minutes)
_BUFFER_TTL_SECONDS = 900


@dataclass
class BufferedEvent:
    """A single SSE event with sequence number for replay ordering."""
    seq: int
    sse_str: str       # Full SSE string: "event: {type}\ndata: {payload}\n\n"
    event_type: str     # Event type: "stage", "custom", "messages", etc.
    timestamp: float = field(default_factory=time.monotonic)


class EventBuffer:
    """In-memory SSE event buffer for a single session.

    Thread-safe for single-writer (background task/generator) multi-reader
    (reconnect endpoints) access patterns in asyncio.
    """

    def __init__(self, session_id: int, max_size: int = 5000):
        self.session_id = session_id
        self.events: list[BufferedEvent] = []
        self._seq_counter: int = 0
        self.max_size = max_size
        self.created_at: float = time.monotonic()

    def append(self, sse_str: str, event_type: str) -> int:
        """Append an SSE event and return its sequence number."""
        seq = self._seq_counter
        self.events.append(BufferedEvent(seq=seq, sse_str=sse_str, event_type=event_type))
        self._seq_counter += 1

        # Trim oldest events if buffer exceeds max size
        if len(self.events) > self.max_size:
            self.events = self.events[-self.max_size:]

        return seq

    def replay_from(self, start_seq: int) -> list[BufferedEvent]:
        """Return all events with seq > start_seq."""
        return [e for e in self.events if e.seq > start_seq]

    @property
    def current_seq(self) -> int:
        """Return the latest sequence number (-1 if empty)."""
        return self._seq_counter - 1

    @property
    def is_expired(self) -> bool:
        """Check if the buffer has exceeded its TTL."""
        return (time.monotonic() - self.created_at) > _BUFFER_TTL_SECONDS


# ---------------------------------------------------------------------------
# Global registries
# ---------------------------------------------------------------------------

# Per-session event buffers: session_id → EventBuffer
_session_buffers: dict[int, EventBuffer] = {}

# Live queues for running tasks: session_id → asyncio.Queue
# When a reconnect client claims a queue, it is removed from this dict.
_live_queues: dict[int, "asyncio.Queue"] = {}


def get_or_create_buffer(session_id: int) -> EventBuffer:
    """Get or create an event buffer for the given session."""
    if session_id not in _session_buffers:
        _session_buffers[session_id] = EventBuffer(session_id)
    return _session_buffers[session_id]


def get_buffer(session_id: int) -> EventBuffer | None:
    """Get the event buffer for a session, or None if not found."""
    buf = _session_buffers.get(session_id)
    if buf and buf.is_expired:
        cleanup_buffer(session_id)
        return None
    return buf


def cleanup_buffer(session_id: int) -> None:
    """Remove the event buffer for a session."""
    _session_buffers.pop(session_id, None)


def register_live_queue(session_id: int, queue: "asyncio.Queue") -> None:
    """Register a live queue for a running session."""
    _live_queues[session_id] = queue


def claim_live_queue(session_id: int) -> "asyncio.Queue | None":
    """Claim the live queue for a session (removes it from registry).

    Only one reconnect client can claim the queue. Subsequent reconnect
    attempts will get None and fall back to buffer-only replay.
    """
    return _live_queues.pop(session_id, None)


def cleanup_live_queue(session_id: int) -> None:
    """Remove the live queue registration (called when task completes)."""
    _live_queues.pop(session_id, None)


def cleanup_all_expired() -> None:
    """Clean up all expired buffers. Can be called periodically."""
    expired = [sid for sid, buf in _session_buffers.items() if buf.is_expired]
    for sid in expired:
        cleanup_buffer(sid)
