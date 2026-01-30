from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PublishedEvent:
    event: object
    seq: int


class FakeNATSClient:
    def __init__(self) -> None:
        self._seq = 0
        self.published: list[PublishedEvent] = []

    async def publish_event(self, event) -> int:
        self._seq += 1
        self.published.append(PublishedEvent(event=event, seq=self._seq))
        return self._seq
