import os
import sys
from decimal import Decimal
import importlib.util

# Add joinmarket-clientserver-master/src to sys.path to support imports in abcmint_interface
jm_root = os.path.join(os.path.dirname(__file__), '..', 'joinmarket-clientserver-master', 'src')
if jm_root not in sys.path:
    sys.path.insert(0, os.path.abspath(jm_root))

_mod_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'jmclient', 'abcmint_interface.py')
spec = importlib.util.spec_from_file_location('abcmint_interface', os.path.abspath(_mod_path))
abcmint_interface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abcmint_interface)
ABCmintBlockchainInterface = abcmint_interface.ABCmintBlockchainInterface


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v is not None else default


def _mk_iface():
    host = _env('ABCMINT_RPC_HOST')
    port = int(_env('ABCMINT_RPC_PORT') or 0)
    user = _env('ABCMINT_RPC_USER')
    password = _env('ABCMINT_RPC_PASSWORD')
    if not all([host, port, user, password]):
        return None
    # import JsonRpc via file path to avoid jmclient __init__ importing jmbitcoin
    jsonrpc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'joinmarket-clientserver-master', 'src', 'jmclient', 'jsonrpc.py'))
    jsonrpc_spec = importlib.util.spec_from_file_location('jm_jsonrpc', jsonrpc_path)
    jm_jsonrpc = importlib.util.module_from_spec(jsonrpc_spec)
    jsonrpc_spec.loader.exec_module(jm_jsonrpc)
    rpc = jm_jsonrpc.JsonRpc(host, port, user, password)
    return ABCmintBlockchainInterface(rpc, '')


def test_e2e_node_connect_and_transfer():
    if _env('ABCMINT_RUN_E2E') != '1':
        return
    iface = _mk_iface()
    assert iface is not None
    try:
        h = iface.get_current_block_height()
    except Exception:
        return
    assert isinstance(h, int) and h >= 0
    print(f"ABCMint height: {h}")
    tip = iface.get_best_block_hash()
    assert isinstance(tip, str) and len(tip) == 64
    print(f"ABCMint tip: {tip}")

    utxos = iface.listunspent(minconf=1)
    if not utxos:
        return
    src = next((u for u in utxos if Decimal(str(u.get('amount', 0))) > Decimal('0.0002')), None)
    if not src:
        return

    cfg = _env('ABCMINT_ADDR_CFG', '274')
    try:
        cfg_int = int(cfg)
    except Exception:
        cfg_int = 274
    newaddr = iface.get_new_address(cfg_int)
    assert isinstance(newaddr, str)
    print(f"Using address config_value: {cfg_int}\nNew address: {newaddr}")

    amount_ding = int(Decimal(str(src['amount'])) * Decimal('1e8'))
    send_ding = max(0, amount_ding - int(Decimal('0.01') * Decimal('1e8')))
    if send_ding == 0:
        return
    send_amt = Decimal(send_ding) / Decimal('1e8')

    inputs = [{
        'txid': src['txid'],
        'vout': int(src['vout']),
    }]
    outputs = {newaddr: send_amt}
    # For RPC call, we need to convert Decimal to float because json serialization might fail or RPC expects float
    # However, abcmint_interface handles this in create_raw_transaction if we were using it.
    # But here we are calling iface._rpc directly.
    # Let's fix this by using iface.create_raw_transaction instead of direct RPC call, 
    # or manually converting. Using the interface method is cleaner.
    raw = iface.create_raw_transaction(inputs, outputs)
    assert isinstance(raw, str)
    signed = iface._rpc('signrawtransaction', [raw])
    hex_tx = signed['hex'] if isinstance(signed, dict) else signed
    assert isinstance(hex_tx, str)
    txid = iface._rpc('sendrawtransaction', [hex_tx])
    assert isinstance(txid, str) and len(txid) == 64
    print(f"Broadcast txid: {txid}")
