import logging
import threading
import time
from typing import Any, Callable, Union, Optional
from unittest.mock import create_autospec

import pytest
from pyatcommand import AtErrorCode, AtResponse
from pyatcommand.common import dprint

from pynanomodem import (
    ModemModel,
    SatelliteModem,
)

logger = logging.getLogger()

@pytest.fixture
def modem():
    modem = SatelliteModem()
    try:
        modem.connect()
    except (ConnectionError,):
        pass
    if modem.is_connected():
        # any preconfiguration
        pass
    else:
        modem = None
    yield modem
    if modem is not None:
        modem.disconnect()


# Simulation / mock support

ResponseType = Union[AtResponse, Callable[[str, dict], AtResponse]]
SubValue = str|Callable[[str, SatelliteModem], str]
cmd_placeholders: dict[str, Union[str, Callable[[str, SatelliteModem], str]]] = {}

def mock_res(info: Optional[str] = None, ok: bool = True):
    """Returns an AT command response data structure for mocks."""
    return AtResponse(AtErrorCode.OK if ok else AtErrorCode.ERROR, info)


@pytest.fixture
def mock_modem():
    """Satellite Modem instance with send_command mocked."""
    
    def _make(response_map: dict[str, ResponseType],
              background_commands: Optional[list[str]] = None,
              delay_map: Optional[dict[str, float]] = None,
              urc_map: Optional[dict[str, tuple[str, float]]] = None):
        # Configure defaults
        background_commands = background_commands or ['AT', 'ATE1', 'ATV1']
        delay_map = delay_map or {}
        urc_map = urc_map or {}
        
        modem = SatelliteModem(apn='viasat.poc')
        modem._is_initialized = True
        
        def substitute(cmd: str,
                       modem: SatelliteModem,
                       placeholder_map: dict[str, SubValue],
                       ) -> str:
            """Substitutes placeholders in commands for modem attributes."""
            for k, v in placeholder_map.items():
                if k in cmd:
                    if callable(v):
                        cmd = v(cmd, modem)
                    else:
                        cmd = cmd.replace(k, v)
            return cmd
        
        def find_in_map(incoming_cmd: str, command_map: dict[str, Any]) -> Any|None:
            """Looks up an AT command factoring placeholder substitutions"""
            if incoming_cmd in command_map:
                return command_map[incoming_cmd]
            for template, response in command_map.items():
                if substitute(template, modem, cmd_placeholders) == incoming_cmd:
                    return response
            return None
        
        def emit_urc(urc: str, delay: float):
            """Simulates a command-triggered unsolicited result after a delay."""
            def _worker():
                time.sleep(delay)
                logger.info('Injecting URC %s', dprint(urc))
                modem._unsolicited_queue.put(urc)
            threading.Thread(target=_worker, daemon=True).start()
        
        def send_side_effect(cmd, **kwargs):
            """Emulates a response to an AT command."""
            delay_response = find_in_map(cmd, delay_map)
            if delay_response is not None:
                time.sleep(delay_response)
            response = find_in_map(cmd, response_map)
            if response is not None:
                if callable(response):
                    return response(cmd, kwargs)
                trigger_urc = find_in_map(cmd, urc_map)
                if trigger_urc is not None:
                    emit_urc(*trigger_urc)
                return response
            elif cmd in background_commands:
                return AtResponse(AtErrorCode.OK)
            return AtResponse(AtErrorCode.ERROR)
        
        mocked_send = create_autospec(modem.send_command,
                                      side_effect=send_side_effect)
        modem.send_command = mocked_send
        return modem
    
    return _make


# ------ TEST CASES ------

def test_get_model(mock_modem, modem: SatelliteModem):   # type: ignore
    if modem is None:
        modem: SatelliteModem = mock_modem({
            'ATI': mock_res('ORBCOMM'),
            'ATI4': mock_res('ST2'),
            'ATI5': mock_res('8'),
        })
    model = modem.get_model()
    assert isinstance(model, ModemModel)
    logger.info('Found model: %s', model.name)

    
def test_get_firmware_version(mock_modem, modem: SatelliteModem):   # type: ignore
    if modem is None:
        modem: SatelliteModem = mock_modem({
            'AT+GMR': mock_res('1.2.3'),
        })
    fwv = modem.firmware_version
    assert fwv != ''
    logger.info('Found firmware version: %s', fwv)


def test_get_mobile_id(mock_modem, modem: SatelliteModem):   # type: ignore
    if modem is None:
        modem: SatelliteModem = mock_modem({
            'AT+GSN': mock_res('01234567SKYFEED'),
        })
    mobile_id = modem.mobile_id
    assert len(mobile_id) >= 15
    logger.info('Found mobile ID: %s', mobile_id)
