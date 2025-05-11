from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Message:
    """
    Represents a message to be published to RabbitMQ
    """
    payload: Any
    routing_key: str
    headers: Dict[str, Any] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
