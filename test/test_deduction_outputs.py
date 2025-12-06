import os
from decimal import Decimal

import importlib.util
import sys

base_dir = os.path.dirname(os.path.dirname(__file__))
# Add joinmarket-clientserver-master/src to sys.path
jm_root = os.path.join(base_dir, 'joinmarket-clientserver-master', 'src')
if jm_root not in sys.path:
    sys.path.insert(0, os.path.abspath(jm_root))

abcmint_iface_path = os.path.join(base_dir, 'src', 'jmclient', 'abcmint_interface.py')
spec = importlib.util.spec_from_file_location('abcmint_interface', abcmint_iface_path)
abcmint_interface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abcmint_interface)

class DummyRpc:
    def call(self, method, args):
        if method == 'validateaddress':
            return {'isvalid': True}
        return None

def test_deduction_deduct_mode():
    os.environ['ABCMINT_DEDUCTION_ENABLED'] = 'true'
    os.environ['ABCMINT_DEDUCTION_PERCENT'] = '0.1'
    os.environ['ABCMINT_DEDUCTION_ADDRESS'] = '8P3aFLXr9F6BPvzC6yR4fTiD4RzFT3wJbjhyMn5uJ1ZFARTRb'
    os.environ['ABCMINT_DEDUCTION_MODE'] = 'deduct'
    os.environ['DUST_COINS_FLOOR'] = '0.000055'
    iface = abcmint_interface.ABCmintBlockchainInterface(DummyRpc(), '')
    primary = '8A11111111111111111111111111111111111111111111111111'
    amt = Decimal('10.0')
    outs = {primary: amt}
    res = iface.apply_deduction_outputs(amt, outs)
    assert primary in res
    assert res[primary] < amt
    assert os.environ['ABCMINT_DEDUCTION_ADDRESS'] in res

def test_deduction_add_mode_dust_floor():
    os.environ['ABCMINT_DEDUCTION_ENABLED'] = 'true'
    os.environ['ABCMINT_DEDUCTION_PERCENT'] = '0.000001'
    os.environ['ABCMINT_DEDUCTION_ADDRESS'] = '8P3aFLXr9F6BPvzC6yR4fTiD4RzFT3wJbjhyMn5uJ1ZFARTRb'
    os.environ['ABCMINT_DEDUCTION_MODE'] = 'add'
    os.environ['DUST_COINS_FLOOR'] = '0.000055'
    iface = abcmint_interface.ABCmintBlockchainInterface(DummyRpc(), '')
    primary = '8A22222222222222222222222222222222222222222222222222'
    amt = Decimal('1.0')
    outs = {primary: amt}
    res = iface.apply_deduction_outputs(amt, outs)
    assert primary in res
    assert res[primary] == amt
    fee_addr = os.environ['ABCMINT_DEDUCTION_ADDRESS']
    assert fee_addr in res
    assert res[fee_addr] >= Decimal(os.environ['DUST_COINS_FLOOR'])
