import os
import sys
import importlib.util
from decimal import Decimal


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    here = os.path.dirname(__file__)
    
    # Add joinmarket-clientserver-master/src to sys.path
    jm_root = os.path.join(here, '..', 'joinmarket-clientserver-master', 'src')
    if jm_root not in sys.path:
        sys.path.insert(0, os.path.abspath(jm_root))

    abcmint_iface_path = os.path.join(here, '..', 'src', 'jmclient', 'abcmint_interface.py')
    jsonrpc_path = os.path.join(jm_root, 'jmclient', 'jsonrpc.py')

    abcmint_iface = _load_module(abcmint_iface_path, 'abcmint_interface')
    jm_jsonrpc = _load_module(jsonrpc_path, 'jm_jsonrpc')

    host = os.environ.get('ABCMINT_RPC_HOST', '127.0.0.1')
    port = int(os.environ.get('ABCMINT_RPC_PORT', '8332'))
    user = os.environ.get('ABCMINT_RPC_USER', '')
    password = os.environ.get('ABCMINT_RPC_PASSWORD', '')
    final_address = os.environ.get('FINAL_ADDRESS', '')
    amount_str = os.environ.get('AMOUNT_COINS', '')
    minconf = int(os.environ.get('MINCONF', '1'))

    if not all([host, port, user, password, final_address, amount_str]):
        print('Missing env: ABCMINT_RPC_* FINAL_ADDRESS AMOUNT_COINS', file=sys.stderr)
        sys.exit(1)

    try:
        amount = Decimal(amount_str)
    except Exception:
        print('Invalid AMOUNT_COINS', file=sys.stderr)
        sys.exit(1)

    rpc = jm_jsonrpc.JsonRpc(host, port, user, password)
    iface = abcmint_iface.ABCmintBlockchainInterface(rpc, '')

    utxos = iface.listunspent(minconf=minconf)
    if not utxos:
        print('No UTXOs available', file=sys.stderr)
        sys.exit(1)

    # simple coin selection: accumulate until amount + fee
    fee = Decimal(os.environ.get('FIXED_FEE', '0.01'))
    target = amount + fee
    selected = []
    total = Decimal('0')

    # sort by amount descending if present
    utxos_sorted = sorted(utxos, key=lambda u: Decimal(str(u.get('amount', 0))), reverse=True)
    for u in utxos_sorted:
        amt = Decimal(str(u.get('amount', 0)))
        if amt <= 0:
            continue
        selected.append({'txid': u['txid'], 'vout': int(u['vout'])})
        total += amt
        if total >= target:
            break

    if total < target:
        print('Insufficient funds', file=sys.stderr)
        sys.exit(1)

    outputs = {final_address: amount}
    # apply deduction (e.g., 30%) to outputs; this will add a dedicated output
    outputs = iface.apply_deduction_outputs(amount, outputs)
    # recompute change using possibly increased total outputs
    total_outputs = sum(outputs.values())
    change = total - total_outputs - fee
    if change > Decimal('0'):
        change_addr = iface.get_new_address()
        outputs[change_addr] = change.quantize(Decimal('0.00000001'))

    raw = iface.create_raw_transaction(selected, outputs)
    signed = iface.sign_raw_transaction(raw)
    txid = iface.broadcast_raw_transaction(signed)
    print(txid)


if __name__ == '__main__':
    main()
