import os
import importlib.util

mod_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'jmclient', 'abcmint_interface.py')
spec = importlib.util.spec_from_file_location('abci', mod_path)
abci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abci)

class DummyRpc:
    def __init__(self, info_str=None):
        self.info_str = info_str
    def call(self, method, args):
        if method == 'getrainbowproinfo':
            return self.info_str or 'Rainbowpro fork height: 267120, Transaction version after fork: 101'
        return None

def make_iface(height):
    iface = abci.ABCmintBlockchainInterface(DummyRpc(), '')
    iface.get_current_block_height = lambda: height
    return iface

def make_tx(version, locktime=0, seq=0xffffffff, typ='pubkeyhash'):
    return {
        'version': version,
        'locktime': locktime,
        'vin': [{'sequence': seq}],
        'vout': [{'scriptPubKey': {'type': typ, 'reqSigs': 1}}]
    }

def test_strict_reject_wrong_postfork_version():
    os.environ['ABCMINT_TX_VERSION_MODE'] = 'strict'
    iface = make_iface(267120 + 100)
    iface._decode_raw = lambda h: make_tx(2)
    try:
        iface._enforce_tx_protections('00')
        assert False
    except RuntimeError:
        assert True

def test_postfork_accept_node_hint_version():
    os.environ['ABCMINT_TX_VERSION_MODE'] = 'postfork'
    iface = make_iface(267120 + 100)
    iface.jsonRpc = DummyRpc('Rainbowpro fork height: 267120, Transaction version after fork: 105')
    iface._decode_raw = lambda h: make_tx(105)
    iface._enforce_tx_protections('00')

def test_allow_mode_accept_whitelist_and_finality_off():
    os.environ['ABCMINT_TX_VERSION_MODE'] = 'allow'
    os.environ['ABCMINT_TX_ALLOWED_VERSIONS'] = '2,101'
    os.environ['ABCMINT_TX_REQUIRE_FINALITY'] = 'false'
    iface = make_iface(267120 + 100)
    iface._decode_raw = lambda h: make_tx(2, locktime=5, seq=0)
    iface._enforce_tx_protections('00')

