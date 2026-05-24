"""
MessageBus: publish/subscribe inter-agent communication.
Every agent publishes events. Orchestrator and other agents subscribe.
"""
from collections import defaultdict
from typing import Callable
import datetime


class MessageBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._log: list[dict] = []

    def subscribe(self, topic: str, callback: Callable):
        self._subscribers[topic].append(callback)

    def publish(self, topic: str, sender: str, payload: dict):
        msg = {
            "timestamp": datetime.datetime.now().isoformat(),
            "topic":     topic,
            "sender":    sender,
            "payload":   payload,
        }
        self._log.append(msg)
        for cb in self._subscribers.get(topic, []):
            cb(msg)

    def get_log(self) -> list[dict]:
        return self._log