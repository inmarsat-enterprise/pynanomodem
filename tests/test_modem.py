import logging

import pytest

from pynanomodem import (
    SatelliteModem,
    get_model,
    ModemModel,
    NetworkState,
    NetInfo,
    SignalQuality,
)

logger = logging.getLogger()


@pytest.fixture
def modem():
    modem = SatelliteModem()
    model = get_model(modem)
    if model == ModemModel.CC200A:
        from pynanomodem.modems.quectel_cc200a import QuectelCc200a
        modem = QuectelCc200a()
    modem.connect()
    yield modem
    modem.disconnect()


def test_get_model(modem: SatelliteModem):
    model = get_model(modem)
    assert isinstance(model, ModemModel)
    logger.info('Found model: %s', model.name)

    
def test_get_mobile_id(modem: SatelliteModem):
    mobile_id = modem.get_mobile_id()
    assert mobile_id != ''
    logger.info('Found mobile ID: %s', mobile_id)


def test_get_firmware_version(modem: SatelliteModem):
    fwv = modem.get_firmware_version()
    assert fwv != ''
    logger.info('Found firmware version: %s', fwv)


def test_get_network_state(modem: SatelliteModem):
    ns = modem.get_network_state()
    assert isinstance(ns, NetworkState)
    logger.info('Found network state: %s', ns.name)


def test_get_acquisition_summary(modem: SatelliteModem):
    summary = modem.get_netinfo()
    assert isinstance(summary, NetInfo)
    logger.info('Acquisition summary: %s', summary)


def test_get_snr(modem: SatelliteModem):
    snr = modem.get_snr()
    assert isinstance(snr, float)
    logger.info('SNR: %0.1f', snr)


def test_get_signal_quality(modem: SatelliteModem):
    sq = modem.get_signal_quality()
    assert isinstance(sq, SignalQuality)
    logger.info('Signal Quality: %s (%s)', sq.name, sq.bars())


def test_get_location(modem: SatelliteModem):
    loc = modem.get_location()
    assert hasattr(loc, 'latitude')
    logger.info('Location: %s', loc)
