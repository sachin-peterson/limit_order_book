from .enums import EventType


class Event:
    """
    Represents a state change produced by the matching engine

    Attributes:
    - sequence: position of the event in the event stream
    - timestamp: time of event occurrence
    - event_type: category of event (e.g., "order filled")
    - details: event-specific information
    """
    def __init__(
        self,
        sequence: int,
        timestamp: int,
        event_type: EventType,
        details: dict[str, object]
    ) -> None:
        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("Sequence must be a positive integer")
        
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("Timestamp must be a non-negative integer")
        
        if not isinstance(event_type, EventType):
            raise ValueError("Event type must be a valid EventType")
        
        if not isinstance(details, dict):
            raise ValueError("Details must be a dictionary")

        self.sequence = sequence
        self.timestamp = timestamp
        self.event_type = event_type
        self.details = details.copy()
