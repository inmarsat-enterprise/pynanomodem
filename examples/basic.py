"""Basic example interfacing to IoT Nano modem.

* Read network status
* Check for modem events
* Send periodic heartbeat data
* Allow remote reconfiguration of heartbeat interval

"""
import logging
import time
from datetime import date

from pynanomodem import (
    EventNotification,
    ModemModel,
    GnssLocation,
    NetworkProtocol,
    SatelliteModem,
    get_model,
)

LOG_LEVEL = logging.INFO
HEARTBEAT_INTERVAL = 0   # seconds = 1/day

formatter = logging.Formatter(
    fmt = ('%(asctime)s,[%(levelname)s],(%(threadName)s)'
           ',%(module)s.%(funcName)s:%(lineno)d,%(message)s'),
    datefmt='%Y-%m-%dT%H:%M:%S',
)
formatter.converter = time.gmtime   # !IMPORTANT for correlation with network support
file_handler = logging.FileHandler(
    f'./logs/qos-{date.today().strftime("%Y%m%d")}.log',
    mode='a',
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(LOG_LEVEL)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console)


def build_heartbeat(modem: SatelliteModem) -> bytes:
    """Builds a heartbeat payload for a Mobile-Originated message.
    
    1 byte uint_8 SIN (255)
    4 bytes uint_32 (unix) timestamp (count not required as ts is unambiguous)
    4 bytes int_32 latitude * 60000
    4 bytes int_32 longitude * 60000
    1 byte uint_8 signal_quality index
    1 byte uint_8 snr
    Does not use most efficient encoding which could be <=12 bytes instead of 15.
    """
    sin_byte = 255
    ts = modem.get_system_time()
    logger.info('Getting location for heartbeat')
    loc = modem.get_location() or GnssLocation()
    lat_enc = int(loc.latitude * 60000)
    lon_enc = int(loc.longitude * 60000)
    sq = modem.get_signal_quality().value
    snr_enc = int(round(modem.get_snr(), 0))
    payload = bytearray(sin_byte.to_bytes(1, 'big'))
    payload.extend(ts.to_bytes(4, 'big'))   # could use 31 bits
    payload.extend(lat_enc.to_bytes(4, 'big', signed=True))   # could use 25 bits or fewer with less resolution than 1.5m
    payload.extend(lon_enc.to_bytes(4, 'big', signed=True))   # could use 24 bits or fewer with less resolution than 1.5m
    payload.extend(sq.to_bytes(1, 'big'))   # could use 3 bits
    payload.extend(snr_enc.to_bytes(1, 'big'))   # could use 5 bits with offset and effective range 32-50
    return bytes(payload)


def reconfigure_hearbeat(payload: bytes, old_interval: int = HEARTBEAT_INTERVAL) -> int:
    """Parses a MT message payload to change the heartbeat interval.
    
    Expects:
    SIN 255
    4 bytes uint_32 new interval with range 0..86400
    """
    if isinstance(payload, bytes) and len(payload) > 2:
        if payload[0] == 255:
            request = int.from_bytes(payload[1:5], byteorder='big')
            if request in range(1, 86401):
                logger.info('Remote request changed heartbeat interval to %d s',
                            request)
                return request
            else:
                logger.warning('Unsupported interval %d', request)
    else:
        logger.warning('Unknown MT message structure')
    return old_interval


def main():
    heartbeat_interval = HEARTBEAT_INTERVAL
    modem = SatelliteModem()
    model = get_model(modem)
    if model == ModemModel.CC200A:
        from pynanomodem.modems.quectel_cc200a import QuectelCc200a
        modem = QuectelCc200a()
    elif model == ModemModel.ST2_OGX:
        from pynanomodem.modems.skywave_st2_ogx import SkywaveSt2Ogx
        modem = SkywaveSt2Ogx()
    modem.connect()
    events_mask = (EventNotification.NETWORK_REGISTERED |
                   EventNotification.MESSAGE_MO_COMPLETE |
                   EventNotification.MESSAGE_MT_RECEIVED |
                   EventNotification.WAKEUP_INTERVAL_CHANGE)
    if modem.network == NetworkProtocol.IDP:
        modem.set_monitor_network_trace()
        events_mask |= EventNotification.EVENT_TRACE_CACHED
    else:
        events_mask |= EventNotification.NETINFO_UPDATE
    events_set = modem.set_event_mask(events_mask)
    if not events_set:
        logger.error('Unable to set events notifications')
    device_id = modem.get_mobile_id()
    firmware = modem.get_firmware_version()
    # loc = modem.get_location()
    logger.info('>>> Starting QoS log for %s (%s)', device_id, firmware)
    log_interval = 30
    last_log_time = 0
    last_notification_check_time = 0
    last_heartbeat_time = 0
    heartbeat_count = 0
    # set initial event flags to clear Tx/Rx queues on first run
    events: list[EventNotification] = [EventNotification.MESSAGE_MO_COMPLETE,
                                       EventNotification.MESSAGE_MT_RECEIVED]
    try:
        while True:
            urc = modem.get_urc()
            if urc:
                try:
                    event: EventNotification = modem.parse_urc_event(urc)       # pyright: ignore
                    events.append(event)
                    logger.info('URC signalled event: %s', event.name)
                except AttributeError:
                    pass
            
            if not events and time.time() - last_notification_check_time >= 5:
                events_mask = modem.get_active_events_mask()
                events = EventNotification.get_events(events_mask)
                last_notification_check_time = time.time()
            
            if time.time() - last_log_time >= log_interval:
                logger.info('%s', modem.get_acquisition_summary())
                last_log_time = time.time()
            
            if (heartbeat_interval and
                time.time() - last_heartbeat_time >= heartbeat_interval):
                # send heartbeat
                heartbeat_count += 1
                logger.info('Heartbeat # %d triggered', heartbeat_count)
                if modem.is_transmit_allowed():
                    payload = build_heartbeat(modem)
                    mo_msg = modem.mo_message_send(payload)
                    if mo_msg:
                        logger.info('Queued MO message: %s', mo_msg.id)
                else:
                    logger.warning('Cannot transmit - skipping heartbeat %d',
                                   heartbeat_count)
                last_heartbeat_time = time.time()
                logger.info('Next heartbeat in %0.1f hours',
                            heartbeat_interval / 3600)
                
            for event in events:
                
                if event == EventNotification.MESSAGE_MT_RECEIVED:
                    rx_queue = modem.get_mt_message_queue()
                    for i, _ in enumerate(rx_queue):
                        mt_message = rx_queue[i]
                        mt_message = modem.mt_message_recv(mt_message)
                        if (mt_message and
                            mt_message.size and
                            mt_message.id and
                            mt_message.payload):
                            logger.info('Received %d-bytes MT message (%r...)',
                                        mt_message.size, mt_message.payload[:2])
                            if mt_message.payload[0] == 255:
                                heartbeat_interval = reconfigure_hearbeat(
                                    mt_message.payload,
                                    heartbeat_interval
                                )
                            modem.mt_message_delete(mt_message.id)
                
                elif event == EventNotification.MESSAGE_MO_COMPLETE:
                    tx_queue = modem.get_mo_message_queue()
                    for i, mo_message in enumerate(tx_queue):
                        if (mo_message.state and
                            mo_message.state.is_complete() and
                            mo_message.id):
                            logger.info('MO message %s complete: %s',
                                        mo_message.id, mo_message.state.name)
                            modem.mo_message_delete(mo_message.id)
                
                else:
                    logger.debug('Ignoring %s', event.name)
            
            if events:
                logger.debug('Clearing events')
                events = []
            
    except KeyboardInterrupt:
        logger.info('<<< Stopped by keyboard interrupt')
    modem.disconnect()


if __name__ == '__main__':
    main()
