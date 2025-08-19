"""IoT Nano modem abstract base class implementation.

Does not enforce any @abstractmethod, allowing a generic default class to
provide basic methods to query any modem.
"""

import logging
from abc import ABC
from typing import Optional, Union

from pyatcommand import AtClient, xmodem_bytes_handler

from .common import (
    ModemManufacturer,
    ModemModel,
    NetworkProtocol,
    NetworkState,
    NetInfo,
    SignalQuality,
    PowerMode,
    WakeupInterval,
    GnssMode,
    EventNotification,
)
from .location import GnssLocation
from .message import MoMessage, MtMessage

_log = logging.getLogger(__name__)


class SatelliteModem(AtClient, ABC):
    """Abstract Base Class for a IoT Nano modem."""
    
    _manufacturer: ModemManufacturer = ModemManufacturer.UNKNOWN
    _model: ModemModel = ModemModel.UNKNOWN
    _network: NetworkProtocol = NetworkProtocol.IDP
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mobile_id: str = ''
        self._firmware_version: str = ''
        self._command_timeout = 1
    
    def _post_mutate(self) -> None:
        """Run after mutating the base class to apply __init__ settings."""
    
    def connect(self, **kwargs) -> None:
        super().connect(**kwargs)
        self._autoconfig = False   # avoid potential false V0/E0 detection
    
    def disconnect(self) -> None:
        super().disconnect()
        self._mobile_id = ''
        self._firmware_version = ''
        self._autoconfig = True   # allow for new modem detection
    
    @property
    def network(self) -> NetworkProtocol:
        return self._network
    
    @property
    def manufacturer(self) -> str:
        """Get the manufacturer name."""
        return self._manufacturer.name
    
    @property
    def model(self) -> str:
        """Get the modem model."""
        return self._model.name
    
    def get_model(self) -> ModemModel:
        """Check the model of the connected modem."""
        model = self._model
        mfr_res = self.send_command('ATI')
        if mfr_res.ok and mfr_res.info:
            if 'ORBCOMM' in mfr_res.info.upper():
                model_res = self.send_command('ATI4')
                if model_res.ok and model_res.info:
                    if 'ST2' in model_res.info:
                        proto_res = self.send_command('ATI5')
                        if proto_res.ok and proto_res.info:
                            if proto_res.info == '8':
                                model = ModemModel.ST2_IDP
                            elif proto_res.info == '10':
                                model = ModemModel.ST2_OGX
                            else:
                                raise ValueError('Unsupported protocol value')
            elif 'QUECTEL' in mfr_res.info.upper():
                model = ModemModel.CC200A
        if self._model != ModemModel.UNKNOWN and model != self._model:
            _log.warning('Detected %s but expected %s', model.name, self.model)
        elif model == ModemModel.UNKNOWN:
            _log.warning('Unable to determine modem model')
        return model
        
    @property
    def firmware_version(self) -> str:
        """Get the modem firmware version."""
        if not self._firmware_version:
            resp = self.send_command('AT+GMR', prefix='+GMR:')
            if resp.ok and resp.info:
                # TODO: parse components
                self._firmware_version = resp.info
        return self._firmware_version
    
    @property
    def mobile_id(self) -> str:
        """The modem's globally unique identifier."""
        if self._mobile_id:
            return self._mobile_id
        resp = self.send_command('AT+GSN', prefix='+GSN:')
        if resp.ok and resp.info:
            return resp.info
        return ''
    
    def initialize(self, **kwargs) -> bool:
        """Initialize settings for the modem.
        
        Settings for event notifications/monitoring and URC notifications.
        """
        return True
    
    # @abstractmethod
    def get_network_state(self) -> NetworkState:
        """Get the current network state."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_netinfo(self) -> NetInfo:
        """Get details of the acquisition process."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_snr(self) -> float:
        """Get the SNR (C/N0) of the modem."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_signal_quality(self, **kwargs) -> SignalQuality:
        """Get the qualitative value of the signal."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def is_transmit_allowed(self) -> bool:
        """Check if message transmission is allowed."""
        return self.get_network_state().is_registered()
    
    def is_blocked(self) -> bool:
        """Check if line of sight is blocked."""
        return self.get_network_state().is_blocked()
    
    def is_updating_network(self) -> bool:
        """Check if the modem is updating its network configuration.
        
        The modem should not be powered down during a network update.
        """
        return self.get_network_state().is_updating()
    
    def is_muted(self) -> bool:
        """Check if modem transmission is muted."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def mo_message_send(self, data: bytes, **kwargs) -> Union[MoMessage, None]:
        """Send a mobile-originated message.
        
        Args:
            data (bytes): The binary data to send (including SIN/MIN bytes).
            **message_id (int|str): A unique message identifier in the Tx queue.
                If not provided, one will be assigned.
        
        Returns:
            `MoMessage` (including unique ID) if successful.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def mo_message_cancel(self, message_id: Union[str, int]) -> bool:
        """Cancel a previously submitted message.
        
        Args:
            message (str): The unique identifier in the Tx queue
                to attempt to cancel.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_mo_message_queue(self, message: Optional[MoMessage] = None) -> list[MoMessage]:
        """Get mobile-originated message(s) in the Tx queue.
        
        Args:
            message (MoMessage): If present, only retrieve the specified status.
        
        Returns:
            A list of `MoMessage`(s) in the Tx queue. If `message` was
                specified and is queued, it will be the only list element.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    def clear_mo_message_queue(self) -> bool:
        """Iterate the modem Tx queue to remove completed messages."""
        tx_queue = self.get_mo_message_queue()
        success = True
        for msg in tx_queue:
            if not self.mo_message_delete(msg.id):                              # type: ignore
                success = False
        return success
    
    def mo_message_delete(self, message_id: Union[str, int]) -> bool:
        """Remove a completed mobile-originated message from the Tx queue.
        
        Args:
            message_id (str): The unique identifier in the Tx queue to delete.
        
        Returns:
            True if successful.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_mt_message_queue(self, message: Optional[MtMessage] = None) -> list[MtMessage]:
        """Get mobile-terminated message(s) in the Rx queue.
        
        Args:
            message (MtMessage): If present, only get the specified status.
        
        Returns:
            A list of queued `MtMessage`(s). If `message` was specified and
                is queued, it will be the only list element.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    def clear_mt_message_queue(self) -> bool:
        """Iterate the modem Rx queue to remove completed messages."""
        rx_queue = self.get_mt_message_queue()
        success = True
        for msg in rx_queue:
            if not self.mt_message_delete(msg.id):                              # type: ignore
                success = False
        return success
    
    # @abstractmethod
    def mt_message_recv(self, message: MtMessage, **kwargs) -> Union[MtMessage, None]:
        """Retrieve the specified message (by name) from the Rx queue.
        
        Args:
            message (MtMessage): The message with `name` specified.
        
        Returns:
            The message content and meta if it was in the Rx queue, or None.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    def mt_message_delete(self, message_id: Union[str, int]) -> bool:
        """Remove a completed mobile-terminated message from the Rx queue.
        
        Args:
            message_id (str): The unique identifier in the Rx queue to delete.
        
        Returns:
            True if successful.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    def send_bytes_data_mode(self, data: bytes, **kwargs) -> Union[int, None]:
        """Send using XMODEM protocol.
        
        Args:
            data (bytes): The data to send.
            **callback (Callable): Optional callback to validate byte count.
        
        Returns:
            The number of bytes sent if no callback is specified otherwise None.
        """
        self.data_mode = True
        success = xmodem_bytes_handler(self._serial, 'send', data)              # type: ignore
        self.data_mode = False
        callback = kwargs.get('callback')
        if callable(callback):
            callback(len(data) if success else 0)
            return None
        return len(data) if success else 0
        
    def recv_bytes_data_mode(self, **kwargs) -> Union[bytes, None]:
        """Receive data using XMODEM protocol.
        
        Args:
            **callback (Callable): Callback to receive the message data.
        
        Returns:
            If `callback` is not specified returns the bytes, otherwise None. 
        """
        self.data_mode = True
        data: bytes = xmodem_bytes_handler(self._serial, 'recv', None)          # type: ignore
        self.data_mode = False
        data = data.rstrip(b'\x1a') or b''
        callback = kwargs.get('callback')
        if callable(callback):
            callback(data)
            return None
        return data
    
    def get_gnss_mode(self) -> GnssMode:
        """Get the GNSS operating mode for which systems are in use."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def set_gnss_mode(self, gnss_mode: Union[GnssMode, int], **kwargs) -> bool:
        """Set the GNSS operating mode for which systems to use."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def get_gnss_interval(self) -> int:
        """Get the GNSS refresh interval in seconds."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def set_gnss_interval(self, gnss_interval: int) -> bool:
        """Set the GNSS refresh interval in seconds.
        
        Args:
            gnss_interval (int): The number of seconds between GNSS updates.
                Must be in range 0..30. 0 disables refresh.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_location(self, **kwargs) -> Union[GnssLocation, None]:
        """Get the modem location.
        
        Args:
            **stale_secs (int): The maximum age of the fix to return.
            **wait_secs (int): The maximum time to wait for a fix.
            **nmea_sentences (str): A CSV list of valid sentence types.
                May include RMC,GGA,GSA,GSV.
                
        Returns:
            GnssLocation or None if a GNSS timeout occurs.
        """
        # stale_secs = kwargs.get('stale_secs', 1)
        # wait_secs = kwargs.get('wait_secs', 45)
        # nmea_sentences = kwargs.get('nmea_sentences')
        # if not isinstance(nmea_sentences, str):
        #     nmea_sentences = 'RMC,GGA,GSA'
        # nmea_list = nmea_sentences.replace('"', '').split(',')
        # nmea_sentences = ','.join(f'"{x.strip()}"' for x in nmea_list)
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_system_time(self) -> int:
        """Get UTC epoch seconds from the modem."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_wakeup_interval(self) -> WakeupInterval:
        """Get the modem wakeup interval."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def set_wakeup_interval(self,
                            wakeup_interval: Union[WakeupInterval, int],
                            **kwargs) -> bool:
        """Request a modem wakeup interval.
        
        The wakeup interval will not actually be changed until acknowledged
        by the network.
        
        Args:
            wakeup_interval (WakeupInterval): The desired wakeup interval.
        
        Returns:
            True if accepted. Note that the change only happens when
                acknowledged by the network.
        """
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def get_power_mode(self) -> PowerMode:
        """Get the power mode setting of the modem."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    # @abstractmethod
    def set_power_mode(self, power_mode: Union[PowerMode, int]) -> bool:
        """Set the power mode of the modem.
        
        Args:
            power_mode (PowerMode): The desired power mode.
        
        Returns:
            True if successful.
        """
        raise NotImplementedError('Implement in model-specific subclass')

    def set_event_mask(self, events_bitmask: int, **kwargs) -> bool:
        """Configure modem events that trigger notifications.
        
        Args:
            events_bitmask (int): The bitmask of events to monitor.
        """
        if not isinstance(events_bitmask, int):
            raise ValueError('Invalid bitmask')
        raise NotImplementedError('Implement in model-specific subclass')
    
    def get_event_mask(self) -> int:
        """Read the modem event notification configuration bitmask."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def get_active_events_mask(self) -> int:
        """Get the active events."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def set_monitor_network_trace(self, enable: bool = True) -> bool:
        """Enable or disable monitoring of network trace events."""
        if self.network == NetworkProtocol.IDP:
            return self.set_trace_events_monitor([(3, 1)])
        return True   # built into %NETINFO
        
    def get_trace_events_monitor(self) -> list[tuple[int, int]]:
        """Get the monitored trace events.
        
        Returns a list of (class, subclass) tuples.
        """
        events: list[tuple[int, int]] = []
        resp = self.send_command('AT%EVMON', prefix='%EVMON:')
        if resp.ok and resp.info:
            events_str = [e.strip() for e in resp.info.split(',')]
            for event in events_str:
                events.append(tuple([int(v) for v in event.split('.')]))        # type: ignore
        else:
            _log.warning('Unable to determine monitored trace events')
        return events
    
    def set_trace_events_monitor(self, event_list: list[tuple[int,int]]) -> bool:
        """Set the monitored trace events.
        
        Args:
            event_list (list): A list of (class, subclass) tuples to monitor.
        """
        if not isinstance(event_list, list):
            raise ValueError('Invalid event list')
        for e in event_list:
            if (not (isinstance(e, tuple) and
                     len(e) == 2 and
                     all(isinstance(i, int) for i in e))):
                raise ValueError('Invalid event list')
        events_str = ','.join(f'{e[0]}.{e[1]}' for e in event_list)
        return self.send_command(f'AT%EVMON={events_str}').ok
    
    # @abstractmethod
    def get_last_error_code(self) -> int:
        """Get the last numeric error code result from the modem."""
        resp = self.send_command('ATS80?')
        if resp.ok and resp.info:
            return int(resp.info)
        else:
            _log.warning('Unable to determine last error code')
            return 0
    
    def get_urc_event(self, urc: str) -> Union[EventNotification, None]:
        """Parse a URC to derive an event notification."""
        raise NotImplementedError('Implement in model-specific subclass')
    
    def report_debug(self, **kwargs):
        """Log a debug report."""
        raise NotImplementedError('Implement in model-specific subclass')
