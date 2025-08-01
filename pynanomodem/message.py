"""Message class definitions for IoT Nano modems.
"""

from typing import Optional, Union

from .common import MessagePriorityIdp, MessageState, MessageTypeOgx, ServiceClassOgx

__all__ = ['IotNanoMessage', 'MoMessage', 'MtMessage']


class IotNanoMessage:
    """A base class for IoT Nano messages."""
    def __init__(self, name: Optional[str] = None, **kwargs) -> None:
        """Instantiates a message.
        
        Args:
            name (str): The name/handle of the message.
            **state (MessageState): The message state.
            **payload (bytes): The message payload (including SIN/MIN bytes).
            **size (int): The message size in bytes.
            **ack_bytes (int): The progress (number of bytes acknowledged).
            **priority (MessagePriority): The (IDP) message priority.
            **service_class (ServiceClass): The (OGx) service class.
            **lifetime (int): The lifetime in minutes.
        """
        self._id: Optional[str] = name
        self._state: Optional[MessageState] = None
        self._payload: Optional[bytes] = None
        self._payload_crc32: Optional[str] = None
        self._size: Optional[int] = None
        self._ack_bytes: Optional[int] = None
        self._priority: Optional[MessagePriorityIdp] = None
        self._type: Optional[MessageTypeOgx] = None
        self._service_class: Optional[ServiceClassOgx] = None
        self._lifetime: Optional[int] = None
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
    
    @property
    def id(self) -> Union[str, None]:
        return self._id
    
    @id.setter
    def id(self, value: str):
        if not isinstance(value, str) or not value:
            raise ValueError('Name must be a non-empty string')
        self._id = value
        
    @property
    def state(self) -> Union[MessageState, None]:
        return self._state
    
    @state.setter
    def state(self, value: MessageState):
        if not isinstance(value, MessageState):
            raise ValueError('Invalid message state')
        self._state = value
    
    @property
    def payload(self) -> Union[bytes, None]:
        return self._payload
    
    @payload.setter
    def payload(self, data: bytes):
        if not isinstance(data, bytes) or len(data) < 2:
            raise ValueError('Payload must be bytes with length 2 or more')
        self._payload = data
        self._size = len(data)
    
    @property
    def payload_crc32(self) -> Union[str, None]:
        return self._payload_crc32
    
    @payload_crc32.setter
    def payload_crc32(self, value: str):
        if isinstance(value, str) and len(value) == 8:
            try:
                int(value, 16)
                self._payload_crc32 = value
                return
            except ValueError:
                pass
        raise ValueError('Invalid CRC32 hex string')
    
    @property
    def codec_sin(self) -> Union[int, None]:
        return self._payload[0] if self._payload else None
    
    @property
    def codec_min(self) -> Union[int, None]:
        return self._payload[1] if self._payload else None

    @property
    def size(self) -> Union[int, None]:
        return self._size
    
    @size.setter
    def size(self, value: int):
        if not isinstance(value, int) or value < 2:
            raise ValueError('Invalid size must be 2 or more')
        if self._payload and value != len(self._payload):
            raise ValueError('Size must match payload length')
        self._size = value
    
    @property
    def ack_bytes(self) -> Union[int, None]:
        return self._ack_bytes
    
    @ack_bytes.setter
    def ack_bytes(self, value: int):
        if not isinstance(value, int) or self.size and value > self.size:
            raise ValueError('Invalid delivered must be integer up to size')
        self._ack_bytes = value
    
    @property
    def priority(self) -> Union[MessagePriorityIdp, None]:
        return self._priority
    
    @priority.setter
    def priority(self, value: MessagePriorityIdp):
        if not isinstance(value, MessagePriorityIdp):
            raise ValueError('Invalid priority')
        self._priority = value
    
    @property
    def service_class(self) -> Union[ServiceClassOgx, None]:
        return self._service_class
    
    @service_class.setter
    def service_class(self, value: ServiceClassOgx):
        if not isinstance(value, ServiceClassOgx):
            raise ValueError('Invalid service class')
        self._service_class = value
    
    @property
    def lifetime(self) -> Union[int, None]:
        """Remaining lifetime in (Tx) queue."""
        return self._lifetime
    
    @lifetime.setter
    def lifetime(self, value: int):
        if not isinstance(value, int) or value not in range(65536):
            raise ValueError('Invalid lifetime must be 0..65535 minutes')
        self._lifetime = value
    
    @property
    def type(self) -> Union[MessageTypeOgx, None]:
        return self._type
    
    @type.setter
    def type(self, value: MessageTypeOgx):
        if not isinstance(value, MessageTypeOgx):
            raise ValueError('Invalid service class')
        self._type = value


class MoMessage(IotNanoMessage):
    """A Mobile-Originated message."""


class MtMessage(IotNanoMessage):
    """A Mobile-Terminated message."""
    @property
    def lifetime(self) -> Union[int, None]:
        return self._lifetime
    
    @lifetime.setter
    def lifetime(self, value: int) -> None:
        raise ValueError('MT message does not have lifetime')
