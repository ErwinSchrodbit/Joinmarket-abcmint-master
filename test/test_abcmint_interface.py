import os
import sys
import importlib.util

# Add joinmarket-clientserver-master/src to sys.path
jm_root = os.path.join(os.path.dirname(__file__), '..', 'joinmarket-clientserver-master', 'src')
if jm_root not in sys.path:
    sys.path.insert(0, os.path.abspath(jm_root))

_mod_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'jmclient', 'abcmint_interface.py')
spec = importlib.util.spec_from_file_location('abcmint_interface', os.path.abspath(_mod_path))
abcmint_interface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abcmint_interface)
ABCmintBlockchainInterface = abcmint_interface.ABCmintBlockchainInterface


class DummyRpc:
    def __init__(self):
        pass

    def call(self, method, params):
        if method == 'getblockcount':
            return 123
        if method == 'getblockhash':
            return '00'*32
        if method == 'getblock':
            return {'height': params[0] if isinstance(params[0], int) else 123, 'time': 1700000000}
        if method == 'gettxout':
            return {'confirmations': 1, 'value': 0.0001, 'scriptPubKey': {'hex': '76a914' + '00'*20 + '88ac'}}
        if method == 'listunspent':
            return []
        if method == 'listtransactions':
            return []
        if method == 'gettransaction':
            return {'hex': ''}
        if method == 'sendrawtransaction':
            return 'txid'
        if method == 'validateaddress':
            return {'isvalid': True}
        if method == 'getinfo':
            return {'paytxfee': 0.00001}
        return None


def test_basic_height_hash_block():
    rpc = DummyRpc()
    iface = ABCmintBlockchainInterface(rpc, '')
    assert iface.get_current_block_height() == 123
    assert isinstance(iface.get_best_block_hash(), str)
    assert iface.get_block_time(iface.get_best_block_hash()) > 0


def test_query_utxo_set():
    rpc = DummyRpc()
    iface = ABCmintBlockchainInterface(rpc, '')
    txidbin = bytes.fromhex('00'*32)
    res = iface.query_utxo_set((txidbin, 0), includeconfs=True)
    assert isinstance(res, list)
    assert res[0]['value'] == int(0.0001 * 1e8)