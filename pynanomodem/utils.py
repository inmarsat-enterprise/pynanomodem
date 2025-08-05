"""Utilities for managing modem templates.
"""
import importlib.util
import logging
import os
import tempfile
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Iterable, Type, Union

from pyatcommand import AtClient
from .common import ModemModel
from .modem import SatelliteModem

__all__ = [
    'get_model',
    'clone_and_load_modem_classes',
    'load_modem_class',
]

_log = logging.getLogger(__name__)


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


def get_model(modem: AtClient) -> ModemModel:
    """Get the model of a IoT Nano modem."""
    try:
        modem.connect()
        mfr_res = modem.send_command('ATI')
        if mfr_res.ok and isinstance(mfr_res.info, str):
            if 'ORBCOMM' in mfr_res.info.upper():
                model_res = modem.send_command('ATI4')
                if model_res.ok and isinstance(model_res.info, str):
                    if 'ST2' in model_res.info:
                        proto_res = modem.send_command('ATI5')
                        if proto_res.ok and isinstance(proto_res.info, str):
                            if proto_res.info == '8':
                                return ModemModel.ST2_IDP
                            elif proto_res.info == '10':
                                return ModemModel.ST2_OGX
                            else:
                                raise ValueError('Unsupported protocol value')
            elif 'QUECTEL' in mfr_res.info.upper():
                return ModemModel.CC200A
        return ModemModel.UNKNOWN
    finally:
        modem.disconnect()


def clone_and_load_modem_classes(repo_urls: 'list[str]',
                                 branch: str = 'main',
                                 download_path: str = '',
                                 ) -> dict[str, Type[SatelliteModem]]:
    """Clone multiple Git repositories and load subclasses of SatelliteModem.

    Args:
        repo_urls (list[str]): A list of Git repository URLs.
        branch (str): The branch to clone. Defaults to 'main'.

    Returns:
         A dictionary of modem class names and their corresponding classes.
    """
    modem_classes = {}
    # Create a temporary directory to clone repositories
    with tempfile.TemporaryDirectory() as temp_dir:
        for repo_url in repo_urls:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_path = os.path.join(temp_dir, repo_name)
            _log.debug("Cloning git repository into %s...", repo_path)
            result = subprocess.run(
                ["git", "clone", "--branch", branch, repo_url, repo_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                _log.error("Failed to clone repository %s: %s",
                           repo_url, result.stderr)
                continue
            _log.debug("Git repository %s cloned successfully.", repo_name)
            # Find Python files in the repository and load modem classes
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        class_def = load_modem_class(file_path)
                        if class_def:
                            modem_classes[file.replace('.py', '')] = class_def
                            if download_path and os.path.isdir(download_path):
                                dest_path = os.path.join(download_path, file)
                                shutil.copy(file_path, dest_path)
                                _log.debug('Copied %s to %s', file, dest_path)
    return modem_classes


def load_modem_class(file_path: str) -> Union[Type[SatelliteModem], None]:
    """Load a Python file and return the SatelliteModem subclass.

    Args:
        file_path (str): Path to the Python file.

    Returns:
        SatelliteModem subclass or None.
    """
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)                              # pyright: ignore
    try:
        spec.loader.exec_module(module)                                         # pyright: ignore
    except Exception as exc:
        print(f"Error loading {file_path}: {exc}")
        return None
    # Look for subclasses of SatelliteModem
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (isinstance(attr, type) and issubclass(attr, SatelliteModem) and
            attr is not SatelliteModem):
            return attr
    return None
