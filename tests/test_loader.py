import os

from pynanomodem import SatelliteModem, clone_and_load_modem_classes, load_modem_class


PRIVATE_ACCESS_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_BASE_URL = 'inmarsat-enterprise'
REPOS = [
    'pynanomodem-quectel-cc200a',
    # 'pynanomodem-skywave-st2-ogx',
    # 'pynanomodem-skywave-st2-idp',
]


def test_clone_and_load():
    if not PRIVATE_ACCESS_TOKEN:
        raise ValueError('Requires GitHub PAT for private repo access')
    repo_urls = [f'https://{PRIVATE_ACCESS_TOKEN}@github.com/{REPO_BASE_URL}/{x}'
                 for x in REPOS]
    modems = clone_and_load_modem_classes(repo_urls)
    assert len(modems.keys()) > 0
    for name, subcls in modems.items():
        assert issubclass(subcls, SatelliteModem)
        assert name.replace('_', '') == subcls.__name__.lower()
