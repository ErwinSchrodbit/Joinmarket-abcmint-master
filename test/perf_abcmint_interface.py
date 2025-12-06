import time
import os
import importlib.util
_mod_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'jmclient', 'abcmint_interface.py')
spec = importlib.util.spec_from_file_location('abcmint_interface', os.path.abspath(_mod_path))
abcmint_interface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abcmint_interface)
ABCmintBlockchainInterface = abcmint_interface.ABCmintBlockchainInterface


class DummyRpc:
    def call(self, method, params):
        if method == 'getblockcount':
            return 100000
        if method == 'getblockhash':
            return '00'*32
        if method == 'getblock':
            return {'height': 100000, 'time': 1700000000}
        if method == 'listunspent':
            return [{'txid': '00'*32, 'vout': 0, 'amount': 0.001, 'confirmations': 6, 'scriptPubKey': {'hex': '76a9'}}]*1000
        return None


def test_perf_listunspent():
    rpc = DummyRpc()
    iface = ABCmintBlockchainInterface(rpc, '')
    t0 = time.perf_counter()
    utxos = iface.listunspent()
    t1 = time.perf_counter()
    assert isinstance(utxos, list)
    assert len(utxos) == 1000
    assert (t1 - t0) < 0.2