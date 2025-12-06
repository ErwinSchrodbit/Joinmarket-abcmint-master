import os
import sys
import importlib.util
import time
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
    fee_model_path = os.path.join(here, '..', 'service', 'fee_model.py')
    fee_model = _load_module(fee_model_path, 'fee_model')

    host = os.environ.get('ABCMINT_RPC_HOST', '127.0.0.1')
    port = int(os.environ.get('ABCMINT_RPC_PORT', '8332'))
    user = os.environ.get('ABCMINT_RPC_USER', '')
    password = os.environ.get('ABCMINT_RPC_PASSWORD', '')
    final_address = os.environ.get('FINAL_ADDRESS', '84LEUEGGvnZwnSSTpAfu7gS8b9Sey3yqTVyk69ppafLJkoqgA')
    source_addr = os.environ.get('SOURCE_ADDRESS')#本地cli测试可能需要绑定地址('8CdFhjZBNLH714wjLFipebQvBVUxio4eCh5XaLQHpheJUyG9R')

    # enforce deduction mode and primary address
    os.environ['ABCMINT_DEDUCTION_MODE'] = os.environ.get('ABCMINT_DEDUCTION_MODE', 'deduct')
    os.environ['ABCMINT_DEDUCTION_ENABLED'] = os.environ.get('ABCMINT_DEDUCTION_ENABLED', 'true')
    os.environ['ABCMINT_PRIMARY_ADDRESS'] = final_address

    if not all([host, port, user, password, final_address]):
        print('Missing RPC environment variables or FINAL_ADDRESS', file=sys.stderr)
        sys.exit(1)

    rpc = jm_jsonrpc.JsonRpc(host, port, user, password)
    iface = abcmint_iface.ABCmintBlockchainInterface(rpc, '')

    # amount to process
    amount = Decimal('40.0')
    fee = Decimal(os.environ.get('FIXED_FEE', '0.01'))
    minconf = int(os.environ.get('MINCONF', '1'))
    shards = int(os.environ.get('SHARDS', os.environ.get('TIER_STANDARD_SHARDS', '3')))
    hops = int(os.environ.get('HOPS', os.environ.get('TIER_STANDARD_HOPS', '1')))
    quote = fee_model.quote(amount, shards, hops)
    os.environ['ABCMINT_DEDUCTION_ENABLED'] = 'true'
    os.environ['ABCMINT_DEDUCTION_PERCENT'] = str(quote['percent'])
    print(f"fee quote: percent={round(quote['percent']*100,2)}% abs={quote['abs_fee']} miner={quote['miner_fee']} txs={quote['tx_count']} net={quote['net_amount']}")

    # STEP 1: send amount to dynamic mix address (274), deduct fee immediately
    mix_addr = iface.get_new_address()
    utxos1 = iface.listunspent_for_addresses([source_addr], minconf=minconf) if source_addr else iface.listunspent(minconf=minconf)
    if not utxos1:
        # diagnostics
        try:
            info = jm_jsonrpc.JsonRpc(host, port, user, password).call('getinfo', [])
            print(f"getinfo: {info}")
            allutxos = jm_jsonrpc.JsonRpc(host, port, user, password).call('listunspent', [0, 9999999])
            print(f"listunspent(0..9999999) count: {len(allutxos) if allutxos else 0}")
            if source_addr:
                addr_utxos = iface.listunspent_for_addresses([source_addr], minconf=0)
                print(f"listunspent for SOURCE_ADDRESS count: {len(addr_utxos)}")
                v = jm_jsonrpc.JsonRpc(host, port, user, password).call('validateaddress', [source_addr])
                print(f"validateaddress(SOURCE_ADDRESS): {v}")
        except Exception as e:
            print(f"diagnostics failed: {e}")
        print('No UTXOs available', file=sys.stderr)
        sys.exit(1)
    target1 = amount + fee
    selected1, total1 = [], Decimal('0')
    for u in sorted(utxos1, key=lambda x: Decimal(str(x.get('amount', 0))), reverse=True):
        a = Decimal(str(u.get('amount', 0)))
        if a <= 0:
            continue
        selected1.append({'txid': u['txid'], 'vout': int(u['vout'])})
        total1 += a
        if total1 >= target1:
            break
    if total1 < target1:
        print('Insufficient funds for step 1', file=sys.stderr)
        sys.exit(1)
    outputs1 = {mix_addr: amount}
    os.environ['ABCMINT_PRIMARY_ADDRESS'] = mix_addr
    outputs1 = iface.apply_deduction_outputs(amount, outputs1)
    change1 = total1 - (amount + fee)
    if change1 > Decimal('0'):
        change_addr1 = iface.get_new_address()
        outputs1[change_addr1] = (outputs1.get(change_addr1, Decimal('0.0')) + change1).quantize(Decimal('0.00000001'))
    raw1 = iface.create_raw_transaction(selected1, outputs1)
    signed1 = iface.sign_raw_transaction(raw1)
    txid1 = iface.broadcast_raw_transaction(signed1)
    print(txid1)

    # Monitor confirmations for txid1 until 6 confirmations
    required_conf = int(os.environ.get('REQUIRED_CONF', '6'))
    minconf2 = int(os.environ.get('MINCONF_STEP2', '6'))
    min_needed = max(required_conf, minconf2)
    while True:
        info1 = iface._rpc('gettransaction', [txid1])
        conf = 0
        if info1 and 'confirmations' in info1:
            conf = int(info1['confirmations'])
        print(f"mix-in tx {txid1} confirmations: {conf}/{min_needed}")
        if conf >= min_needed:
            break
        time.sleep(int(os.environ.get('CONF_POLL_INTERVAL_SEC', '15')))
    while True:
        utxos2_ready = iface.listunspent_for_addresses([mix_addr], minconf=minconf2)
        if utxos2_ready:
            break
        time.sleep(int(os.environ.get('CONF_POLL_INTERVAL_SEC', '15')))

    # STEP 2: from mix address to final address, send net amount (fee already taken in step 1)
    minconf2 = int(os.environ.get('MINCONF_STEP2', '6'))
    utxos2 = iface.listunspent_for_addresses([mix_addr], minconf=minconf2)
    if not utxos2:
        print('No UTXOs at mix address', file=sys.stderr)
        sys.exit(1)
    available2 = sum(Decimal(str(u.get('amount', 0))) for u in utxos2)
    net_amount = min(quote['net_amount'], max(Decimal('0.0'), available2 - fee))
    outputs2 = {final_address: net_amount}
    total_outputs2 = sum(outputs2.values())
    target2 = total_outputs2 + fee
    selected2, total2 = [], Decimal('0')
    for u in sorted(utxos2, key=lambda x: Decimal(str(x.get('amount', 0))), reverse=True):
        a = Decimal(str(u.get('amount', 0)))
        if a <= 0:
            continue
        selected2.append({'txid': u['txid'], 'vout': int(u['vout'])})
        total2 += a
        if total2 >= target2:
            break
    if total2 < target2:
        print('Insufficient funds for step 2', file=sys.stderr)
        print(f"available={available2}, net_amount={net_amount}, fee={fee}, target={total_outputs2+fee}")
        sys.exit(1)
    change2 = total2 - (total_outputs2 + fee)
    if change2 > Decimal('0'):
        change_addr2 = iface.get_new_address()
        outputs2[change_addr2] = (outputs2.get(change_addr2, Decimal('0.0')) + change2).quantize(Decimal('0.00000001'))
    raw2 = iface.create_raw_transaction(selected2, outputs2)
    signed2 = iface.sign_raw_transaction(raw2)
    txid2 = iface.broadcast_raw_transaction(signed2)
    print(txid2)
    # Print simple proof info (decode)
    decoded2 = iface._rpc('decoderawtransaction', [signed2])
    if decoded2:
        print(f"final tx outputs: {decoded2.get('vout', [])}")


if __name__ == '__main__':
    main()
