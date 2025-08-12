"""Module for communicating with Viasat IoT Nano modems."""

from pyatcommand import AtClient, AtTimeout

from .common import (
    BeamType,
    DataFormat,
    EventNotification,
    GnssMode,
    LastErrorCode,
    MessageState,
    MessageStateIdp,
    MessageStateOgx,
    ModemManufacturer,
    ModemModel,
    NetInfo,
    NetworkProtocol,
    NetworkState,
    OperatingMode,
    PowerMode,
    SignalQuality,
    WakeupInterval,
    WakeupIntervalIdp,
    WakeupIntervalOgx,
)
from .loader import clone_and_load_modem_classes, detect_modem, load_modem_class
from .location import GnssFixQuality, GnssFixType, GnssLocation, GnssSatelliteInfo
from .message import IotNanoMessage, MoMessage, MtMessage
from .modem import SatelliteModem

__all__ = [
    'AtClient',
    'AtTimeout',
    'LastErrorCode',
    'SatelliteModem',
    'ModemManufacturer',
    'ModemModel',
    'BeamType',
    'IotNanoMessage',
    'MessageState',
    'MessageStateIdp',
    'MessageStateOgx',
    'MoMessage',
    'MtMessage',
    'NetworkProtocol',
    'NetworkState',
    'SignalQuality',
    'NetInfo',
    'DataFormat',
    'EventNotification',
    'WakeupInterval',
    'WakeupIntervalIdp',
    'WakeupIntervalOgx',
    'PowerMode',
    'GnssMode',
    'GnssLocation',
    'GnssFixType',
    'GnssFixQuality',
    'GnssSatelliteInfo',
    'OperatingMode',
    'load_modem_class',
    'clone_and_load_modem_classes',
    'detect_modem',
]
