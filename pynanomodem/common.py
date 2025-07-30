"""Common constants, classes and methods."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, IntEnum, IntFlag
from typing import Iterable, Optional, Union


class ModemManufacturer(IntEnum):
    """Recognized modem/module manufacturers."""
    UNKNOWN = 0
    SKYWAVE = 1
    HONEYWELL = 2
    QUECTEL = 3
    UBLOX = 4


class ModemModel(IntEnum):
    """Recognized modem/module models."""
    UNKNOWN = 0
    OGI = 1
    ST2_IDP = 2
    CC200A = 3
    ST2_OGX = 4


class NetworkProtocol(IntEnum):
    """Network protocol IDP/OGx."""
    IDP = 0
    OGX = 1


class DataFormat(IntEnum):
    """Data format used for sending or receiving messages via AT command."""
    BIN = 0
    TEXT = 1
    HEX = 2
    BASE64 = 3


class NetworkState(IntEnum):
    """The network state."""
    def is_awaiting_gnss(self) -> bool:
        return self.name in ['GNSS_WAIT']
    
    def is_searching(self) -> bool:
        return self.name.startswith('BEAM')
    
    def is_updating(self) -> bool:
        return self.name in ['BB_DOWNLOAD', 'UPDATING']
    
    def is_registering(self) -> bool:
        return self.name == 'REGISTERING'
    
    def is_connected(self) -> bool:
        return self.name in ['ACTIVE', 'CONNECTED']
    
    def is_blocked(self) -> bool:
        return self.name in ['BLOCKED']


class ControlStateIdp(NetworkState):
    """States of the IDP modem internal network acquisition process."""
    STOPPED = 0
    GNSS_WAIT = 1
    SEARCH_START = 2
    BEAM_SEARCH = 3
    BEAM_FOUND = 4
    BEAM_ACQUIRED = 5
    BEAM_SWITCH = 6
    REGISTERING = 7
    RECEIVE_ONLY = 8    
    BB_DOWNLOAD = 9
    ACTIVE = 10
    BLOCKED = 11
    CONFIRM_PREVIOUS_BEAM = 12
    CONFIRM_REQUESTED_BEAM = 13
    CONNECT_CONFIRMED_BEAM = 14


class NetworkStateOgx(NetworkState):
    """Network state used by OGx."""
    STOPPED = 0
    GNSS_WAIT = 1
    BEAM_SEARCH = 2
    UPDATING = 3
    REGISTERING = 4
    CONFIRMING = 5
    CONNECTED = 6


class BeamType(IntEnum):
    """The beam type used for signal analysis."""
    def is_global(self) -> bool:
        return self.name in ['GB', 'SAM_GB']
    
    def is_nominal(self) -> bool:
        return 'NOM' in self.name or self.name == 'RB'


class BeamTypeIdp(BeamType):
    """The beam type used for IDP."""
    GB = 0
    RB = 1


class BeamTypeOgx(BeamType):
    """The beam type used for OGx."""
    ILC_NOM_FL = 1
    ILC_NOM_RL = 2
    SAM_GB = 3
    SAM_RB = 4
    ILC_CFG = 5
    ILC_REG = 6


class BeamStateIdp(IntEnum):
    """The IDP beam search state."""
    IDLE = 0
    SEARCH_TRAFFIC_ANY = 1
    SEARCH_TRAFFIC_LAST = 2
    SEARCH_TRAFFIC_NEXT = 4
    SEARCH_BB = 5
    DELAY = 6


class MessageState(IntEnum):
    """Base class for IDP and OGx message states."""
    def is_complete(self):
        return self.name in ['RX_COMPLETE', 'TX_COMPLETE', 'TX_FAIL',
                             'TX_ABORT', 'TX_EXPIRED', 'TX_CANCELLED']
    
    def is_success(self):
        return self.name in ['RX_COMPLETE', 'TX_COMPLETE']
    
    def is_failed(self):
        return self.name in ['TX_FAIL']
    
    def is_expired(self):
        return self.name in ['TX_ABORT', 'TX_EXPIRED']
    
    def is_cancelled(self):
        return self.name in ['TX_CANCELLED']


class MessageStateIdp(MessageState):
    """The IDP message state."""
    UNAVAILABLE = 0
    RX_COMPLETE = 2
    RX_RETRIEVED = 3
    TX_READY = 4
    TX_SENDING = 5
    TX_COMPLETE = 6
    TX_FAIL = 7
    TX_ABORT = 8


class MessageStateOgx(MessageState):
    """The OGx message state."""
    TX_INITIALIZING = 1
    TX_OFFLINE = 2
    TX_READY = 3
    TX_SENDING = 4
    RX_COMPLETE = 5
    TX_COMPLETE = 6
    TX_FAIL = 7
    TX_EXPIRED = 8
    TX_CANCELLED = 14


class MessagePriorityIdp(IntEnum):
    """The IDP message priority.
    
    Weights selection of MO fragments to send. This value is not transported
    over-the-air or indicated on the Messaging API.
    """
    NONE = 0   # Used for IDP MT messages only
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


class ServiceClassOgx(IntEnum):
    """The OGx service class.
    
    Weights selection of message fragments to send. This value is indicated
    on the Messaging API.
    """
    PREMIUM = 1
    NORMAL = 2
    BACKGROUND = 3


class MessageTypeOgx(IntEnum):
    """The type of message for OGx."""
    SMALL = 1
    SINGLE_BLOCK = 2   # 1024..16000 bytes


class OperatingMode(IntEnum):
    """The operating mode as interpreted by the network API."""
    ON_OFF = 0
    WAKEUP = 1
    ROS = 2
    HYBRID = 3


class GnssMode(IntEnum):
    """The GNSS operating mode."""


class GnssModeSkywave(GnssMode):
    """GNSS mode mappings for SkyWave/Orbcomm."""
    GPS = 0   # default
    GLONASS = 1
    BEIDOU = 2
    GALILEO  = 3
    GPS_GLONASS = 10
    GPS_BEIDOU = 11
    GLONASS_BEIDOU = 12
    GPS_GALILEO = 13
    GLONASS_GALILEO = 14
    BEIDOU_GALILEO = 15


class GnssModeQuectel(GnssMode):
    """GNSS mode mappings for Quectel."""
    GPS = 0
    GPS_BEIDOU = 1
    GPS_GLONASS = 2
    GPS_GALILEO = 3
    GPS_GLONASS_GALILEO_BEIDOU = 4


class WakeupInterval(IntEnum):
    """Base class for IDP or OGx wakeup intervals."""


class WakeupIntervalIdp(WakeupInterval):
    """The modem wakeup interval for IDP."""
    NONE = 0
    SECONDS_30 = 1
    MINUTES_1 = 2
    MINUTES_3 = 3
    MINUTES_10 = 4
    MINUTES_30 = 5
    HOURS_1 = 6
    MINUTES_2 = 7
    MINUTES_5 = 8
    MINUTES_15 = 9
    MINUTES_20 = 10


class WakeupIntervalOgx(WakeupInterval):
    """The modem wakeup interval for OGx."""
    NONE = 0
    SECONDS_30 = 1
    MINUTES_1 = 2
    MINUTES_2 = 3
    MINUTES_3 = 4
    MINUTES_5 = 5
    MINUTES_10 = 6
    MINUTES_15 = 7
    MINUTES_20 = 8
    MINUTES_30 = 9
    HOURS_1 = 10
    HOURS_2 = 11
    HOURS_3 = 12
    HOURS_6 = 13
    HOURS_12 = 14
    HOURS_24 = 15


class PowerMode(IntEnum):
    """The modem power mode.
    
    Implies various internal state machine settings for balancing power
    consumption against speed of recovery from line of sight blockages.
    """
    MOBILE_POWERED = 0
    FIXED_POWERED = 1
    MOBILE_BATTERY = 2
    FIXED_BATTERY = 3
    MOBILE_MINIMAL = 4
    MOBILE_PARKED = 5


class EventNotification(IntFlag):
    """Bitmask enumerated values for modem event notifications."""
    GNSS_FIX_NEW =              0b000000000000001
    MESSAGE_MT_RECEIVED =       0b000000000000010
    MESSAGE_MO_COMPLETE =       0b000000000000100
    NETWORK_REGISTERED =        0b000000000001000
    MODEM_RESET_COMPLETE =      0b000000000010000
    JAMMING_ANTENNA_CHANGE =    0b000000000100000
    MODEM_RESET_PENDING =       0b000000001000000
    WAKEUP_INTERVAL_CHANGE =    0b000000010000000
    UTC_TIME_SYNC =             0b000000100000000
    GNSS_FIX_TIMEOUT =          0b000001000000000
    EVENT_TRACE_CACHED =        0b000010000000000
    NETWORK_PING_ACKNOWLEDGED = 0b000100000000000   # IDP-only
    MESSAGE_MO_STARTED =        0b001000000000000   # OGx-only
    SATCOM_STATE_CHANGE =       0b010000000000000   # OGx-only
    NETINFO_UPDATE =            0b100000000000000   # OGx-only
    
    @classmethod
    def get_events(cls, event_mask: int) -> 'list[EventNotification]':
        """Parses a bitmask to return a list of events."""
        return [item for item in cls if item.value & event_mask]
    
    @classmethod
    def get_bitmask(cls, events: 'list[EventNotification]') -> int:
        """Parse a list of events and return a bitmask."""
        if (not isinstance(events, list) or
            not all(isinstance(e, EventNotification) for e in events)):
            raise ValueError('Invalid list of events')
        bitmask = 0
        for event in events:
            bitmask |= event.value
        return bitmask


class SignalQuality(IntEnum):
    """A qualitative indicator of relative signal strength."""
    UNKNOWN = 0   # No Rx/Tx attempt
    NONE = 1   # No successful Rx/Tx
    WEAK = 2   # T415 Very poor
    POOR = 3
    FAIR = 4
    GOOD = 5
    STRONG = 6   # T415 Very Good
    SUPER = 7   # T415 Excellent
    
    def bars(self) -> str:
        """Qualitative indicator as number of bars 0..5"""
        if self.value == 1:
            return 'BARS_0'
        elif self.value == 2:
            return 'BARS_1'
        elif self.value == 3:
            return 'BARS_2'
        elif self.value == 4:
            return 'BARS_3'
        elif self.value == 5:
            return 'BARS_4'
        elif self.value == 6:
            return 'BARS_5'
        elif self.value == 7:
            return 'BARS_6'
        return 'UNKNOWN'


class SignalLevelIdp(Enum):
    """Qualitative mapping of SNR/CN0 values for a IDP Regional Beam.
    
    NONE, FAIR, GOOD: a scale to be used as greaterOrEqual threshold
    """
    NONE = 0.0
    WEAK = 37.0
    POOR = 39.0
    FAIR = 41.0
    GOOD = 43.0
    STRONG = 45.5
    INVALID = 55.0
    
    @classmethod
    def nearest(cls, value: Union[float, int]) -> 'SignalLevelIdp':
        if not isinstance(value, (float, int)):
            raise ValueError('Value must be float or int')
        eligible = [member for member in cls if member.value >= value]
        if eligible:
            return min(eligible, key=lambda m: m.value)
        return SignalLevelIdp.INVALID

@dataclass
class AcquisitionSummary:
    """Key information about network acquisition."""
    network: Optional[NetworkProtocol] = None
    state: Optional[NetworkState] = None
    beam_state: Optional[BeamStateIdp] = None
    registered: bool = False
    signal_quality: SignalQuality = SignalQuality.UNKNOWN
    signal_level: Optional[float] = None
    beam_type: Optional[BeamType] = None
    
    def to_str(self) -> str:
        obj = {k: v for k, v in vars(self).items()}
        for k, v in obj.items():
            if isinstance(v, Enum):
                obj[k] = v.name
            elif isinstance(v, float):
                obj[k] = round(v, 1)
        return json.dumps(obj)


class GeoBeam(IntEnum):
    """Geographic Beam identifiers mapped to readable names."""
    GLOBAL_BB = 0
    AMER_RB1 = 1
    AMER_RB2 = 2
    AMER_RB3 = 3
    AMER_RB4 = 4
    AMER_RB5 = 5
    AMER_RB6 = 6
    AMER_RB7 = 7
    AMER_RB8 = 8
    AMER_RB9 = 9
    AMER_RB10 = 10
    AMER_RB11 = 11
    AMER_RB12 = 12
    AMER_RB13 = 13
    AMER_RB14 = 14
    AMER_RB15 = 15
    AMER_RB16 = 16
    AMER_RB17 = 17
    AMER_RB18 = 18
    AMER_RB19 = 19
    AORW_SC = 61
    EMEA_RB1 = 21
    EMEA_RB2 = 22
    EMEA_RB3 = 23
    EMEA_RB4 = 24
    EMEA_RB5 = 25
    EMEA_RB6 = 26
    EMEA_RB7 = 27
    EMEA_RB8 = 28
    EMEA_RB9 = 29
    EMEA_RB10 = 30
    EMEA_RB11 = 31
    EMEA_RB12 = 32
    EMEA_RB13 = 33
    EMEA_RB14 = 34
    EMEA_RB15 = 35
    EMEA_RB16 = 36
    EMEA_RB17 = 37
    EMEA_RB18 = 38
    EMEA_RB19 = 39
    APAC_RB1 = 41
    APAC_RB2 = 42
    APAC_RB3 = 43
    APAC_RB4 = 44
    APAC_RB5 = 45
    APAC_RB6 = 46
    APAC_RB7 = 47
    APAC_RB8 = 48
    APAC_RB9 = 49
    APAC_RB10 = 50
    APAC_RB11 = 51
    APAC_RB12 = 52
    APAC_RB13 = 53
    APAC_RB14 = 54
    APAC_RB15 = 55
    APAC_RB16 = 56
    APAC_RB17 = 57
    APAC_RB18 = 58
    APAC_RB19 = 59
    IOE_RB1 = 101
    IOE_RB2 = 102
    IOE_RB3 = 103
    IOE_RB4 = 104
    IOE_RB5 = 105
    IOE_RB6 = 106
    IOE_RB7 = 107
    IOE_RB8 = 108
    IOE_RB9 = 109
    IOE_RB10 = 110
    IOE_RB11 = 111
    IOE_RB12 = 112
    IOE_RB13 = 113
    IOE_RB14 = 114
    IOE_RB15 = 115
    IOE_RB16 = 116
    IOE_RB17 = 117
    IOE_RB18 = 118
    IOE_RB19 = 119

    @property
    def satellite(self):
        return self.name.split('_')[0]

    @property
    def beam(self):
        return self.name.split('_')[1]
    
    @property
    def id(self):
        return self.value


class GeoSatellite(Enum):
    """Maps the Viasat/Inmarsat geostationary longitude supporting NIMO."""
    AMER = -98.0   # Inmarsat 4F3
    AORWSC = -54.0   # Inmarsat 3F5
    EMEA = 24.9   # Inmarsat 4AF4 aka Alphasat XL
    IOE = 63.5   # Inmarsat 6F1 previously IOR 3F1, MEAS 4F2
    APAC = 143.5   # Inmarsat 4F2 previously 4F1


def ts_to_iso(timestamp: 'float|int', ms: bool = False) -> str:
    """Converts a unix timestamp to ISO 8601 format (UTC).
    
    Args:
        timestamp: A unix timestamp.
        ms: Flag indicating whether to include milliseconds in response
    
    Returns:
        ISO 8601 UTC format e.g. `YYYY-MM-DDThh:mm:ss[.sss]Z`

    """
    iso_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    if not ms:
        return f'{iso_time[:19]}Z'
    return f'{iso_time[:23]}Z'


def iso_to_ts(iso_time: str, ms: bool = False) -> Union[int, float]:
    """Converts a ISO 8601 timestamp (UTC) to unix timestamp.
    
    Args:
        iso_time: An ISO 8601 UTC datetime `YYYY-MM-DDThh:mm:ss[.sss]Z`
        ms: Flag indicating whether to include milliseconds in response
    
    Returns:
        Unix UTC timestamp as an integer, or float if `ms` flag is set.

    """
    if '.' not in iso_time:
        iso_time = iso_time.replace('Z', '.000Z')
    utc_dt = datetime.strptime(iso_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    ts = (utc_dt - datetime(1970, 1, 1)).total_seconds()
    if not ms:
        ts = int(ts)
    return ts


def bits_in_bitmask(bitmask: int) -> Iterable[int]:
    """Get iterable integer value of each bit in a bitmask."""
    while bitmask:
        bit = bitmask & (~bitmask+1)
        yield bit
        bitmask ^= bit
