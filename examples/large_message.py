"""Example showing sending a large message."""
import logging
import math
import time
from datetime import date
from typing import Iterable

from pynanomodem import SatelliteModem, ModemModel, EventNotification, NetworkProtocol
from pynanomodem.loader import detect_modem

LOG_LEVEL = logging.INFO
FILE_SIZE = 5000


formatter = logging.Formatter(
    fmt = ('%(asctime)s,[%(levelname)s],(%(threadName)s)'
           ',%(module)s.%(funcName)s:%(lineno)d,%(message)s'),
    datefmt='%Y-%m-%dT%H:%M:%S',
)
formatter.converter = time.gmtime   # !IMPORTANT for correlation with network support
file_handler = logging.FileHandler(
    f'./logs/large_message-{date.today().strftime("%Y%m%d")}.log',
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


def iter_chunks_with_header(data: bytearray, chunk_size: int) -> Iterable[bytes]:
    """Break up data into transmission-friendly chunks.
    
    First 2 bytes are 0xFFFF as an identifier for large message.
    3rd byte is the subsequent number of chunks to be transmitted.
    """
    header_sin_min = b'\xFF\xFF'
    chunks_left = math.ceil(len(data) / chunk_size)
    if chunks_left > 255:
        raise ValueError('Exceeded maximum chunk count')
    for i in range(0, len(data), chunk_size):
        chunks_left -= 1
        yield bytes(header_sin_min + bytes([chunks_left]) + data[i:i + chunk_size])


def main():
    modem = detect_modem(SatelliteModem())
    modem.connect()
    events_mask = int(EventNotification.MESSAGE_MO_COMPLETE)
    events_set = modem.set_event_mask(events_mask)
    if not events_set:
        logger.error('Unable to set events notifications')
    events = []
    logger.info('Starting large message test using %s on %s network',
                modem.mobile_id, modem.network.name)
    last_notification_check_time = 0
    data = bytearray()
    for i in range(FILE_SIZE):
        data.extend([255 if i % 2 == 0 else 0])
    chunk_size = 6144 if modem.network == NetworkProtocol.IDP else 15360
    chunk_count = 0
    if modem.is_transmit_allowed():
        start_time = time.time()
        for chunk in iter_chunks_with_header(data, chunk_size):
            chunk_count += 1
            logger.info('Sending %d-byte chunk #%d of %d-byte data',
                        len(chunk), chunk_count, len(data))
            msg_meta = modem.mo_message_send(chunk)
            submit_time = time.time()
            while msg_meta:
                if not events and time.time() - last_notification_check_time >= 5:
                    events_mask = modem.get_active_events_mask()
                    events = EventNotification.get_events(events_mask)
                    last_notification_check_time = time.time()
                    if EventNotification.MESSAGE_MO_COMPLETE in events:
                        tx_queue = modem.get_mo_message_queue()
                        for msg in tx_queue:
                            if msg.id == msg_meta.id:
                                latency = time.time() - submit_time
                                logger.info('Chunk %d completed in %0.1fs',
                                            chunk_count, latency)
                                modem.mo_message_delete(msg_meta.id)            # type: ignore
                                msg_meta = None
                                break
                events = []
                time.sleep(1)
        total_latency = time.time() - start_time
        logger.info('%d-bytes data transmitted in %0.1fs (%d chunks)',
                    len(data), total_latency, chunk_count)


if __name__ == '__main__':
    main()
