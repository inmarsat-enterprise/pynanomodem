"""Classes and methods for location, elevation and azimuth for satellite modems.

Parses NMEA-0183 data into a `GnssLocation` object.
"""

import inspect
import json
import logging
from dataclasses import dataclass
from enum import IntEnum

from .utils import iso_to_ts, ts_to_iso


_log = logging.getLogger(__name__)


class GnssFixType(IntEnum):
    """Enumerated fix type from NMEA-0183 standard."""
    NONE = 1
    FIX_2D = 2
    FIX_3D = 3


class GnssFixQuality(IntEnum):
    """Enumerated fix quality from NMEA-0183 standard."""
    INVALID = 0
    GPS_SPS = 1
    DGPS = 2
    PPS = 3
    RTK = 4
    FLOAT_RTK = 5
    EST_DEAD_RECKONING = 6
    MANUAL = 7
    SIMULATION = 8


@dataclass
class GnssSatelliteInfo(object):
    """Information specific to a GNSS satellite.
    
    Attributes:
        prn: The PRN code (Pseudo-Random Number sequence)
        elevation: The satellite elevation
        azimuth: The satellite azimuth
        snr: The satellite Signal-to-Noise Ratio
    """
    prn: int
    elevation: int
    azimuth: int
    snr: int


def validate_nmea(nmea_sentence: str) -> bool:
    """Validates a given NMEA-0183 sentence with CRC.
    
    Args:
        nmea_sentence (str): NMEA-0183 sentence ending in checksum.
    
    """
    if '*' not in nmea_sentence:
        return False
    data, cs_hex = nmea_sentence.split('*')
    candidate = int(cs_hex, 16)
    crc = 0   # initial
    for i in range(1, len(data)):   # ignore initial $
        crc ^= ord(data[i])
    return candidate == crc


class GnssLocation:
    """A set of location-based information derived from the modem's NMEA data.
    
    Uses 90.0/180.0 if latitude/longitude are unknown

    Attributes:
        latitude (float): decimal degrees
        longitude (float): decimal degrees
        altitude (float): in metres
        speed (float): in knots
        heading (float): in degrees
        timestamp (int): in seconds since 1970-01-01T00:00:00Z
        satellites (int): in view at time of fix
        fix_type (GnssFixType): 1=None, 2=2D or 3=3D
        fix_quality (GnssFixQuality): Enumerated lookup value
        pdop (float): Probability Dilution of Precision
        hdop (float): Horizontal Dilution of Precision
        vdop (float): Vertical Dilution of Precision
        time_iso (str): ISO 8601 formatted timestamp

    """
    __slots__ = ('latitude', 'longitude', 'altitude', 'speed', 'heading',
                 'timestamp', 'satellites', 'fix_type', 'fix_quality',
                 'pdop', 'hdop', 'vdop',)
    
    def __init__(self, **kwargs):
        """Initializes a Location with default latitude/longitude 90/180."""
        self.latitude = float(kwargs.get('latitude', 90.0))
        self.longitude = float(kwargs.get('longitude', 180.0))
        self.altitude = float(kwargs.get('altitude', 0.0))   # metres
        self.speed = float(kwargs.get('speed', 0.0))  # knots
        self.heading = float(kwargs.get('heading', 0.0))   # degrees
        self.timestamp = int(kwargs.get('timestamp', 0))   # seconds (unix)
        self.satellites = int(kwargs.get('satellites', 0))
        self.fix_type = GnssFixType(int(kwargs.get('fix_type', 1)))
        self.fix_quality = GnssFixQuality(int(kwargs.get('fix_quality', 0)))
        self.pdop = float(kwargs.get('pdop', 99))
        self.hdop = float(kwargs.get('hdop', 99))
        self.vdop = float(kwargs.get('vdop', 99))

    @property
    def time_iso(self) -> str:
        return f'{ts_to_iso(self.timestamp)}'

    def __repr__(self) -> str:
        obj = {k: v for k, v in vars(self).items()
               if not k.startswith('_') and not callable(v)}
        for name, _ in inspect.getmembers(self.__class__,
                                          lambda o: isinstance(o, property)):
            if not name.startswith('_'):
                try:
                    v = getattr(self, name)
                    if not callable(v):
                        obj[name] = v
                except Exception:
                    pass
        for k, v in obj.items():
            if k in ['latitude', 'longitude']:
                obj[k] = round(v, 5)
            elif isinstance(v, float):
                obj[k] = round(v, 1)
            elif isinstance(v, IntEnum):
                obj[k] = v.name
        return json.dumps(obj, skipkeys=True)
    
    def is_valid(self) -> bool:
        """Check validity."""
        return self.latitude is not None and self.longitude is not None
    
    def parse_nmea(self, nmea_sentence: str):
        """Update the location with information derived from an NMEA sentence.
        
        Args:
            nmea_sentence (str): The NMEA-0183 sentence to parse.
        """
        if not validate_nmea(nmea_sentence):
            raise ValueError('Invalid NMEA-0183 sentence')
        data = nmea_sentence.split('*')[0]
        nmea_type = ''
        cache = {}
        for i, field_data in enumerate(data.split(',')):
            if i == 0:
                nmea_type = field_data[-3:]
                if nmea_type == 'GSV':
                    _log.warning('No processing required for GSV sentence')
                    return
                if nmea_type == 'GSA' and self.vdop != 99:
                    # _log.debug('Skipping redundant GSA data')
                    return
                # _log.debug('Processing NMEA type: %s', nmea_type)
            elif i == 1:
                if nmea_type == 'RMC':
                    cache['fix_hour'] = field_data[0:2]
                    cache['fix_min'] = field_data[2:4]
                    cache['fix_sec'] = field_data[4:6]
            elif i == 2:
                if nmea_type == 'RMC':
                    if (field_data == 'V'):
                        _log.warn('Fix Void')
                elif nmea_type == 'GSA':
                    self.fix_type = GnssFixType(int(field_data))
            elif i == 3:
                if nmea_type == 'RMC':
                    self.latitude = (float(field_data[0:2]) +
                                     float(field_data[2:]) / 60.0)
            elif i == 4:
                if nmea_type == 'RMC':
                    if field_data == 'S':
                        self.latitude *= -1
            elif i == 5:
                if nmea_type == 'RMC':
                    self.longitude = (float(field_data[0:3]) +
                                      float(field_data[3:]) / 60.0)
            elif i == 6:
                if nmea_type == 'RMC':
                    if field_data == 'W':
                        self.longitude *= -1
                elif nmea_type == 'GGA':
                    self.fix_quality = GnssFixQuality(int(field_data))
            elif i == 7:
                if nmea_type == 'RMC':
                    self.speed = float(field_data)
                elif nmea_type == 'GGA':
                    self.satellites = int(field_data)
            elif i == 8:
                if nmea_type == 'RMC':
                    self.heading = float(field_data)
                elif nmea_type == 'GGA':
                    self.hdop = round(float(field_data), 1)
            elif i == 9:
                if nmea_type == 'RMC':
                    fix_day = field_data[0:2]
                    fix_month = field_data[2:4]
                    fix_yy = int(field_data[4:])
                    fix_yy += 1900 if fix_yy >= 73 else 2000
                    iso_time = (f'{fix_yy}-{fix_month}-{fix_day}T'
                                f'{cache["fix_hour"]}:{cache["fix_min"]}'
                                f':{cache["fix_sec"]}Z')
                    self.timestamp = int(iso_to_ts(iso_time))
                elif nmea_type == 'GGA':
                    self.altitude = float(field_data)
            elif i == 10:
                # RMC magnetic variation - ignore
                if nmea_type == 'GGA' and field_data != 'M':
                    _log.warning('Unexpected altitude units: %s', field_data)
            # elif i == 11:   # RMC magnetic variation direction, GGA height of geoid - ignore
            # elif i == 12:   # GGA units height of geoid - ignore
            # elif i == 13:   # GGA seconds since last DGPS update - ignore
            # elif i == 14:   # GGA DGPS station ID - ignore
            elif i == 15:   # GSA PDOP - ignore (unused)
                if nmea_type == 'GSA':
                    self.pdop = round(float(field_data), 1)
            # elif i == 16:   # GSA HDOP - ignore (use GGA)
            elif i == 17:
                if nmea_type == 'GSA':
                    self.vdop = round(float(field_data), 1)
    
    @classmethod
    def from_nmea_list(cls, nmea_list: list[str]) -> 'GnssLocation':
        """Create a GnssLocation from a list of NMEA-0183 sentences."""
        if (not isinstance(nmea_list, list) or
            not all(isinstance(s, str) for s in nmea_list)):
            raise ValueError('Invalid list or sentences in list')
        loc = GnssLocation()
        for sentence in nmea_list:
            loc.parse_nmea(sentence)
        return loc
