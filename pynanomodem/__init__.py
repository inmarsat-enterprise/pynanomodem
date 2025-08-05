"""Module for communicating with Viasat IoT Nano modems."""

from pyatcommand import AtClient, AtTimeout

from .common import (
    AcquisitionSummary,
    BeamType,
    DataFormat,
    EventNotification,
    GnssMode,
    MessageState,
    MessageStateIdp,
    MessageStateOgx,
    ModemManufacturer,
    ModemModel,
    NetworkProtocol,
    NetworkState,
    OperatingMode,
    PowerMode,
    SignalQuality,
    WakeupInterval,
    WakeupIntervalIdp,
    WakeupIntervalOgx,
)
from .location import GnssFixQuality, GnssFixType, GnssLocation, GnssSatelliteInfo
from .message import IotNanoMessage, MoMessage, MtMessage
from .modem import SatelliteModem
from .utils import get_model, load_modem_class, clone_and_load_modem_classes

__all__ = [
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
    'AtClient',
    'AtTimeout',
    'SignalQuality',
    'AcquisitionSummary',
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
    'get_model',
    'load_modem_class',
    'clone_and_load_modem_classes',
]
