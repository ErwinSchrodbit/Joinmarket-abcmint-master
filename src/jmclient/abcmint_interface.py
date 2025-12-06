from decimal import Decimal
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple, Union
import os

import binascii
import re

from jmbase import bintohex, hextobin
from jmbase.support import get_log
try:
    from jmclient.blockchaininterface import BlockchainInterface
except Exception:
    class BlockchainInterface(object):
        pass

log = get_log()
DEFAULT_ADDR_CFG = 274
RAINBOWFORKHEIGHT = 267120

class ABCmintBlockchainInterface(BlockchainInterface):
    def __init__(self, jsonRpc, wallet_name: str) -> None:
        super().__init__()
        self.jsonRpc = jsonRpc

    def _rpc(self, method: str, args: Union[dict, list] = []) -> Any:
        ret = self.jsonRpc.call(method, args)
        return ret

    def is_address_imported(self, addr: str) -> bool:
        try:
            res = self._rpc('validateaddress', [addr])
            if not res:
                return False
            return bool(res.get('isvalid', False))
        except Exception:
            return False

    def is_address_labeled(self, utxo: dict, walletname: str) -> bool:
        return False

    def pushtx(self, txbin: bytes) -> bool:
        txhex = bintohex(txbin)
        _ = self._rpc('sendrawtransaction', [txhex])
        return _ is not None

    def query_utxo_set(self,
                       txouts: Union[Tuple[bytes, int], List[Tuple[bytes, int]]],
                       includeconfs: bool = False,
                       include_mempool: bool = True) -> List[Optional[dict]]:
        if not isinstance(txouts, list):
            txouts = [txouts]
        result: List[Optional[dict]] = []
        for txo in txouts:
            txo_hex = bintohex(txo[0])
            try:
                txo_idx = int(txo[1])
            except Exception:
                result.append(None)
                continue
            ret = self._rpc('gettxout', [txo_hex, txo_idx, include_mempool])
            if not ret:
                result.append(None)
                continue
            try:
                val = ret['value']
                if not isinstance(val, Decimal):
                    val = Decimal(str(val))
                value_ding = int(val * Decimal('1e8'))
                script_hex = ret['scriptPubKey']['hex']
                item: Dict[str, Any] = {'value': value_ding, 'script': hextobin(script_hex)}
                if includeconfs:
                    item['confirms'] = int(ret.get('confirmations', 0))
                result.append(item)
            except Exception:
                result.append(None)
        return result

    def get_wallet_rescan_status(self) -> Tuple[bool, Optional[Decimal]]:
        return False, None

    def rescanblockchain(self, start_height: int, end_height: Optional[int] = None) -> None:
        return None

    def import_addresses_if_needed(self, addresses: Set[str], wallet_name: str) -> bool:
        return False

    def import_addresses(self, addr_list: Iterable[str], wallet_name: str,
                         restart_cb: Optional[Callable[[str], None]] = None) -> None:
        return None

    def list_transactions(self, num: int, skip: int = 0) -> List[dict]:
        res = self._rpc('listtransactions', ["*", num, skip])
        return res if res else []

    def get_deser_from_gettransaction(self, rpcretval: dict) -> Optional[object]:
        if not rpcretval or 'hex' not in rpcretval:
            return None
        try:
            decoded = self._rpc('decoderawtransaction', [rpcretval['hex']])
            return decoded if isinstance(decoded, dict) else None
        except Exception:
            return None

    def get_transaction(self, txid: bytes) -> Optional[dict]:
        htxid = bintohex(txid)
        try:
            res = self._rpc('gettransaction', [htxid])
            return res if res else None
        except Exception:
            return None

    def get_block(self, blockheight: int) -> str:
        block_hash = self.get_block_hash(blockheight)
        ret = self._rpc('getblock', [block_hash])
        if ret is None:
            raise RuntimeError('RPC getblock failed')
        return ret

    def get_current_block_height(self) -> int:
        ret = self._rpc('getblockcount', [])
        if ret is None:
            raise RuntimeError('RPC getblockcount failed')
        return int(ret)

    def get_best_block_hash(self) -> str:
        bh = self._rpc('getblockhash', [self.get_current_block_height()])
        if bh is None:
            raise RuntimeError('RPC getblockhash failed')
        return bh

    def get_best_block_median_time(self) -> int:
        bh = self.get_current_block_height()
        h = self.get_block_hash(bh)
        b = self._rpc('getblock', [h])
        if b is None:
            raise RuntimeError('RPC getblock failed')
        return int(b.get('time', 0))

    def get_block_height(self, blockhash: str) -> int:
        b = self._rpc('getblock', [blockhash])
        if b is None:
            raise RuntimeError('RPC getblock failed')
        return int(b.get('height', 0))

    def get_block_time(self, blockhash: str) -> int:
        b = self._rpc('getblock', [blockhash])
        if b is None:
            raise RuntimeError('RPC getblock failed')
        return int(b.get('time', 0))

    def get_block_hash(self, height: int) -> str:
        ret = self._rpc('getblockhash', [height])
        if ret is None:
            raise RuntimeError('RPC getblockhash failed')
        return ret

    def get_new_address(self, config_value: int = DEFAULT_ADDR_CFG, account: Optional[str] = None) -> str:
        args: List[Any] = [int(config_value)]
        if account is not None:
            args.append(account)
        ret = self._rpc('getnewaddress', args)
        if not isinstance(ret, str):
            raise RuntimeError('RPC getnewaddress failed')
        return ret

    def create_raw_transaction(self, inputs: List[dict], outputs: Dict[str, Decimal]) -> str:
        # RPC usually supports string amounts to avoid precision loss.
        # Converting Decimal to string for RPC compatibility.
        outs_rpc = {k: str(v) for k, v in outputs.items()}
        ret = self._rpc('createrawtransaction', [inputs, outs_rpc])
        if not isinstance(ret, str):
            raise RuntimeError('RPC createrawtransaction failed')
        return ret

    def sign_raw_transaction(self, raw_hex: str) -> str:
        ret = self._rpc('signrawtransaction', [raw_hex])
        if isinstance(ret, dict):
            hex_tx = ret.get('hex')
        else:
            hex_tx = ret
        if not isinstance(hex_tx, str):
            raise RuntimeError('RPC signrawtransaction failed')
        return hex_tx

    def broadcast_raw_transaction(self, hex_tx: str) -> str:
        self._enforce_tx_protections(hex_tx)
        ret = self._rpc('sendrawtransaction', [hex_tx])
        if isinstance(ret, str):
            return ret
        try:
            decoded = self._rpc('decoderawtransaction', [hex_tx])
        except Exception:
            decoded = None
        dust_floor = Decimal(os.environ.get('DUST_COINS_FLOOR', '0.000055'))
        hint = None
        try:
            if isinstance(decoded, dict):
                outs = decoded.get('vout') or []
                mins = []
                for o in outs:
                    v = o.get('value')
                    if v is not None:
                        mins.append(Decimal(str(v)))
                if mins:
                    mv = min(mins)
                    if mv < dust_floor:
                        hint = 'possible dust output'
        except Exception:
            pass
        msg = 'RPC sendrawtransaction failed'
        if hint:
            msg = msg + ' (' + hint + ')'
        raise RuntimeError(msg)

    def send_to_address(self, address: str, amount_coins: Decimal) -> str:
        ret = self._rpc('sendtoaddress', [address, str(amount_coins)])
        if not isinstance(ret, str):
            raise RuntimeError('RPC sendtoaddress failed')
        return ret

    def _load_deduction_config(self) -> Tuple[bool, Decimal, Optional[str]]:
        import configparser
        cfg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'conf', 'joinmarket_abcmint.cfg')
        cfg = configparser.ConfigParser()
        enabled, percent, address = False, Decimal('0.0'), None
        try:
            if os.path.exists(cfg_path):
                cfg.read(cfg_path)
                enabled = cfg.getboolean('DEDUCTION', 'enabled', fallback=False)
                percent = Decimal(cfg.get('DEDUCTION', 'percent', fallback='0.0'))
                address = cfg.get('DEDUCTION', 'address', fallback=None)
        except Exception:
            pass
        # env overrides
        env_enabled = os.environ.get('ABCMINT_DEDUCTION_ENABLED')
        if env_enabled is not None:
            enabled = env_enabled.lower() in ('1', 'true', 'yes')
        env_percent = os.environ.get('ABCMINT_DEDUCTION_PERCENT')
        if env_percent is not None:
            try:
                percent = Decimal(env_percent)
            except Exception:
                pass
        env_address = os.environ.get('ABCMINT_DEDUCTION_ADDRESS')
        if env_address:
            address = env_address
        return enabled, percent, address

    def apply_deduction_outputs(self, send_amount_coins: Decimal, outputs: Dict[str, Decimal]) -> Dict[str, Decimal]:
        enabled, percent, address = self._load_deduction_config()
        if not enabled:
            return outputs
        if not address or percent <= Decimal('0') or percent >= Decimal('1'):
            return outputs
        v = self._rpc('validateaddress', [address])
        if not v or not v.get('isvalid', False):
            return outputs
        mode = os.environ.get('ABCMINT_DEDUCTION_MODE', '').lower()
        if not mode:
            # try config file mode
            try:
                import configparser
                cfg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'conf', 'joinmarket_abcmint.cfg')
                cfg = configparser.ConfigParser()
                if os.path.exists(cfg_path):
                    cfg.read(cfg_path)
                    mode = cfg.get('DEDUCTION', 'mode', fallback='deduct').lower()
            except Exception:
                mode = 'deduct'
        if mode not in ('deduct', 'add'):
            mode = 'deduct'

        dust_floor = Decimal(os.environ.get('DUST_COINS_FLOOR', '0.000055'))
        amt_dec = send_amount_coins
        ded_dec = (amt_dec * percent).quantize(Decimal('0.00000001'))
        if ded_dec <= Decimal('0'):
            return outputs

        new_outputs = {k: v for k, v in outputs.items()}
        primary_addr = os.environ.get('ABCMINT_PRIMARY_ADDRESS')
        target_addr = None
        if primary_addr and primary_addr in new_outputs:
            target_addr = primary_addr
        else:
            try:
                target_addr = next(iter(new_outputs.keys()))
            except StopIteration:
                target_addr = None

        if mode == 'deduct' and target_addr:
            new_val = new_outputs[target_addr] - ded_dec
            if new_val <= dust_floor:
                mode = 'add'
            else:
                new_outputs[target_addr] = new_val.quantize(Decimal('0.00000001'))

        fee_out_val = new_outputs.get(address, Decimal('0.0')) + ded_dec
        if fee_out_val < dust_floor:
            fee_out_val = dust_floor
        new_outputs[address] = fee_out_val.quantize(Decimal('0.00000001'))
        return new_outputs

    def get_tx_merkle_branch(self, txid: str, blockhash: Optional[str] = None) -> bytes:
        raise NotImplementedError

    def verify_tx_merkle_branch(self, txid: str, block_height: int, merkle_branch: bytes) -> bool:
        return False

    def listaddressgroupings(self) -> list:
        return self._rpc('listaddressgroupings', []) or []

    def listunspent(self, minconf: Optional[int] = None) -> List[dict]:
        args: List[Any] = []
        if minconf is not None:
            args = [minconf]
        res = self._rpc('listunspent', args)
        return res if res else []

    def listunspent_for_addresses(self, addresses: List[str], minconf: int = 1, maxconf: int = 9999999) -> List[dict]:
        res = self._rpc('listunspent', [minconf, maxconf, addresses])
        return res if res else []

    def testmempoolaccept(self, rawtx: str) -> bool:
        return True

    def mempoolfullrbf(self) -> bool:
        return False

    def _get_mempool_min_fee(self) -> Optional[int]:
        return None

    def _estimate_fee_basic(self, conf_target: int) -> Optional[Tuple[int, int]]:
        try:
            info = self._rpc('getinfo', [])
            if not info:
                return None
            fee_ding_kvb = int(Decimal(str(info.get('paytxfee', 0))) * Decimal('1e8'))
            if fee_ding_kvb <= 0:
                return None
            return fee_ding_kvb, conf_target
        except Exception:
            return None

    def _get_relay_fee_floor(self) -> Optional[Decimal]:
        try:
            info = self._rpc('getinfo', [])
            if not info:
                return None
            v = info.get('paytxfee')
            if v is None:
                return None
            return Decimal(str(v))
        except Exception:
            return None

    def _decode_raw(self, hex_tx: str) -> Optional[dict]:
        try:
            decoded = self._rpc('decoderawtransaction', [hex_tx])
            return decoded if isinstance(decoded, dict) else None
        except Exception:
            return None

    def _enforce_tx_protections(self, hex_tx: str) -> None:
        decoded = self._decode_raw(hex_tx)
        if not decoded:
            raise RuntimeError('TX decode failed')
        try:
            cur_h = self.get_current_block_height()
        except Exception:
            cur_h = RAINBOWFORKHEIGHT + 100000
        ver = int(decoded.get('version', 0))
        mode = (os.environ.get('ABCMINT_TX_VERSION_MODE') or 'postfork').lower()
        allowed_env = os.environ.get('ABCMINT_TX_ALLOWED_VERSIONS') or ''
        allowed: Set[int] = set()
        for p in allowed_env.split(','):
            try:
                v = int(p.strip())
                if v:
                    allowed.add(v)
            except Exception:
                pass
        hint_ver, hint_fork = self._get_node_tx_version_hint()
        fork_h = hint_fork if isinstance(hint_fork, int) and hint_fork > 0 else RAINBOWFORKHEIGHT
        postfork = cur_h > fork_h + 20
        if mode == 'strict':
            if postfork:
                if ver != 101:
                    raise RuntimeError('version enforcement failed')
            else:
                if ver not in (1, 101):
                    raise RuntimeError('version enforcement failed')
        elif mode == 'allow':
            if postfork:
                if allowed and ver in allowed:
                    pass
                elif hint_ver is not None and ver == int(hint_ver):
                    pass
                else:
                    raise RuntimeError('version enforcement failed')
            else:
                if ver not in (1, 101) and (not allowed or ver not in allowed):
                    raise RuntimeError('version enforcement failed')
        else:
            if postfork:
                target = int(hint_ver) if hint_ver is not None else 101
                if ver != target and ver not in allowed:
                    raise RuntimeError('version enforcement failed')
            else:
                if ver not in (1, 101):
                    raise RuntimeError('version enforcement failed')
        lt = int(decoded.get('locktime', 0))
        req_final = (os.environ.get('ABCMINT_TX_REQUIRE_FINALITY') or 'true').lower() in ('1', 'true', 'yes')
        if req_final:
            if lt != 0:
                raise RuntimeError('finality enforcement failed')
        vin = decoded.get('vin') or []
        for i in vin:
            seq = int(i.get('sequence', 0))
            if req_final and seq != 0xffffffff:
                raise RuntimeError('finality enforcement failed')
        vout = decoded.get('vout') or []
        for o in vout:
            spk = o.get('scriptPubKey') or {}
            typ = (spk.get('type') or '').lower()
            if typ in ('nonstandard', 'witness_v0_keyhash', 'witness_v0_scripthash'):
                raise RuntimeError('nonstandard script rejected')
            if typ == 'multisig':
                rs = int(spk.get('reqSigs', 0))
                if rs < 1 or rs > 3:
                    raise RuntimeError('multisig reqSigs out of range')

    def _get_node_tx_version_hint(self) -> Tuple[Optional[int], Optional[int]]:
        try:
            s = self._rpc('getrainbowproinfo', [])
            if not isinstance(s, str) or not s:
                return None, None
            mv = None
            mh = None
            m1 = re.search(r'fork\s+height\s*:\s*(\d+)', s, re.IGNORECASE)
            if m1:
                try:
                    mh = int(m1.group(1))
                except Exception:
                    mh = None
            m2 = re.search(r'Transaction\s+version\s+after\s+fork\s*:\s*(\d+)', s, re.IGNORECASE)
            if m2:
                try:
                    mv = int(m2.group(1))
                except Exception:
                    mv = None
            return mv, mh
        except Exception:
            return None, None

    def _estimate_tx_size_nonsegwit(self, num_inputs: int, num_outputs: int) -> int:
        ni = max(0, int(num_inputs))
        no = max(0, int(num_outputs))
        return 10 + ni * 148 + no * 34

    def estimate_fee_coins_for_counts(self, num_inputs: int, num_outputs: int, conf_target: int = 1) -> Decimal:
        size = self._estimate_tx_size_nonsegwit(num_inputs, num_outputs)
        est = self._estimate_fee_basic(conf_target)
        if not est:
            fallback = Decimal(os.environ.get('TX_FEE_PER_TX', '0.01'))
            return fallback
        ding_per_kb, _ = est
        kb = (size + 999) // 1000
        ding = ding_per_kb * kb
        coins = Decimal(ding) / Decimal('1e8')
        floor = self._get_relay_fee_floor()
        if floor is not None:
            coins = max(coins, floor)
        return coins

    def get_fee_source_hint(self) -> str:
        try:
            est = self._estimate_fee_basic(1)
            if est:
                return 'node'
        except Exception:
            pass
        return 'constant'