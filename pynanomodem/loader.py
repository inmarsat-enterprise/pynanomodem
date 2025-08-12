"""Utilities for loading SatelliteModem subclasses.
"""

import logging
import importlib.util
import os
import tempfile
import shutil
import subprocess
import sys
from typing import Type, Union
from pathlib import Path
from importlib import import_module

from . import modems
from .modem import SatelliteModem
from .common import ModemModel

_log = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_ORG = 'inmarsat-enterprise'
GITHUB_REPOS = [
    'quectel-cc200a',
    'skywave-st2-ogx',
    'skywave-st2-idp',
]


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
    module = importlib.util.module_from_spec(spec)                              # type: ignore
    try:
        spec.loader.exec_module(module)                                         # type: ignore
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


def detect_modem(modem: SatelliteModem, **kwargs) -> SatelliteModem:
    """Get the subclass of the IoT Nano modem.
    
    Attempts to find the module in `modems_path` which defaults to the `modems`
    folder under `pynanomodem`.
    If not found, will attempt to clone/download from GitHub private repository
    if a GITHUB_TOKEN environment variable is present.
    
    Args:
        modem (SatelliteModem): The base/unknown modem.
        **module (module): The module containing the subclass python files.
    
    Returns:
        Subclass of SatelliteModem.
    
    Raises:
        ModuleNotFoundError if unable to load the subclass.
    """
    was_connected = modem.is_connected()
    if not was_connected:
        modem.connect()
    model = modem.get_model()
    if model != ModemModel.UNKNOWN and model != modem._model:
        modem.disconnect()
        file_tag = f'{model.name.lower()}.py'
        pymodule = kwargs.get('module', modems)
        modems_path = Path(pymodule.__path__[0])
        modem_paths = [f for f in modems_path.glob('*.py')
                       if Path(f).name != '__init__.py']
        if not any(p.name.endswith(file_tag) for p in modem_paths):
            try:
                token = kwargs.get('github_token', GITHUB_TOKEN)
                if not token:
                    _log.warning('No GITHUB_TOKEN found please contact Viasat')
                    raise ValueError('Missing GITHUB_TOKEN')
                org = kwargs.get('github_org_name', GITHUB_ORG)
                repos: list[str] = kwargs.get('github_repos', GITHUB_REPOS)
                for repo_name in repos:
                    if repo_name.replace('-', '_').endswith(model.name.lower()):
                        _log.info('Copying %s from GitHub to %s',
                                  model.name, modems_path)
                        repo_url = (f'https://{token}@github.com'
                                    f'/{org}/pynanomodem-{repo_name}')
                        clone_and_load_modem_classes([repo_url],
                                                     download_path=str(modems_path))
                # Refresh paths
                modem_paths = [f for f in modems_path.glob('*.py')
                               if Path(f).name != '__init__.py']
            except Exception as e:
                raise ModuleNotFoundError(f'No module for {model.name}') from e
        for p in modem_paths:
            if p.name.endswith(file_tag):
                modem_path = p.resolve()
                sys.path.append(str(modem_path.parents[2]))
                relative_path = modem_path.relative_to(modem_path.parents[2])
                module_name = '.'.join(relative_path.with_suffix('').parts)
                submodule = import_module(module_name)
                for attr_name in dir(submodule):
                    candidate = getattr(submodule, attr_name)
                    if (isinstance(candidate, type) and
                        issubclass(candidate, SatelliteModem) and
                        candidate._model.name == model.name):
                        modem = candidate(port=modem.port)
                        break
                break
    if model == ModemModel.UNKNOWN:
        raise ModuleNotFoundError('Unrecognized modem')
    if was_connected:
        modem.connect()
    return modem
