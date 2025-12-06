import os
import time
from decimal import Decimal

import importlib.util

svc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service', 'mixing_service.py')
spec = importlib.util.spec_from_file_location('mixing_service', svc_path)
mixing_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mixing_service)

class FakeIface:
    def __init__(self):
        self.fail_once = True
    def listunspent_for_addresses(self, addrs, minconf=0):
        if minconf == 0:
            return [{'txid': 'a'*64, 'vout': 0, 'amount': 1.0}]
        else:
            return [{'txid': 'b'*64, 'vout': 0, 'amount': 1.0}]
    def estimate_fee_coins_for_counts(self, n_in, n_out, conf_target=1):
        return Decimal('0.009')
    def create_raw_transaction(self, inputs, outputs):
        return '00'
    def sign_raw_transaction(self, raw):
        return raw
    def broadcast_raw_transaction(self, signed):
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError('mempool chain too long')
        return 'txid123'

class FakeService(mixing_service.MixingService):
    def __init__(self):
        self.iface = FakeIface()
        self.addr_pool = ['8A'*34]
    def _get_address(self):
        return '8A0'*10
def test_retry_on_unconfirmed_chain():
    os.environ['CONF_POLL_INTERVAL_SEC'] = '1'
    s = FakeService()
    txid = s._single_send_from(['8X'], Decimal('0.5'), Decimal('0.009'), '8Y', 0)
    assert txid == 'txid123'
    assert not s.iface.fail_once