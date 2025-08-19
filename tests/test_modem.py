import logging
from unittest.mock import create_autospec

import pytest
from pyatcommand import AtErrorCode, AtResponse

from pynanomodem import (
    ModemModel,
    SatelliteModem,
)

logger = logging.getLogger()


@pytest.fixture
def mock_modem():
    """Satellite Modem instance with send_command mocked."""
    
    def _make(response_map: dict[str, AtResponse],
              background_commands: list[str] = ['AT', 'ATE1', 'ATV1']):

        def send_side_effect(cmd, **kwargs):
            if cmd in response_map:
                return response_map[cmd]
            if cmd in background_commands:
                return AtResponse(AtErrorCode.OK)
            return AtResponse(AtErrorCode.ERROR)
        
        modem = SatelliteModem()
        mocked_send = create_autospec(modem.send_command)
        mocked_send.side_effect = send_side_effect
        modem.send_command = mocked_send
        return modem
    
    return _make


def test_get_model(mock_modem):
    modem: SatelliteModem = mock_modem({
        'ATI': AtResponse(AtErrorCode.OK, info='ORBCOMM'),
        'ATI4': AtResponse(AtErrorCode.OK, info='ST2'),
        'ATI5': AtResponse(AtErrorCode.OK, info='8'),
    })
    model = modem.get_model()
    assert isinstance(model, ModemModel)
    logger.info('Found model: %s', model.name)

    
def test_get_firmware_version(mock_modem):
    modem: SatelliteModem = mock_modem({
        'AT+GMR': AtResponse(AtErrorCode.OK, info='1.2.3'),
    })
    fwv = modem.firmware_version
    assert fwv != ''
    logger.info('Found firmware version: %s', fwv)


def test_get_mobile_id(mock_modem):
    modem: SatelliteModem = mock_modem({
        'AT+GSN': AtResponse(AtErrorCode.OK, info='01234567SKYFEED'),
    })
    mobile_id = modem.mobile_id
    assert len(mobile_id) >= 15
    logger.info('Found mobile ID: %s', mobile_id)
