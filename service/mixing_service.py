import os
import sys
import importlib.util
import time
import uuid
import threading
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import random
import json

# Dynamically load existing modules
here = os.path.dirname(__file__)
abcmint_iface_path = os.path.join(here, '..', 'src', 'jmclient', 'abcmint_interface.py')
# Update path to reflect that joinmarket-clientserver-master is now inside joinmarket_abcmint
jm_root = os.path.join(here, '..', 'joinmarket-clientserver-master', 'src')
jsonrpc_path = os.path.join(jm_root, 'jmclient', 'jsonrpc.py')

# Ensure jmbase and other modules can be imported by abcmint_interface
if jm_root not in sys.path:
    sys.path.insert(0, os.path.abspath(jm_root))

def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

abcmint_iface = _load_module(abcmint_iface_path, 'abcmint_interface')
jm_jsonrpc = _load_module(jsonrpc_path, 'jm_jsonrpc')
fee_model = _load_module(os.path.join(here, 'fee_model.py'), 'fee_model')


@dataclass
class MixJob:
    job_id: str
    target_address: str
    amount: Decimal
    deposit_address: str
    deposit_received: Decimal = Decimal('0.0')
    deposit_required: Decimal = Decimal('0.0')
    shard_count: int = 3
    hop_count: int = 1
    fee_percent: Decimal = Decimal('0.0')
    abs_fee: Decimal = Decimal('0.0')
    miner_fee: Decimal = Decimal('0.0')
    tx_count: int = 0
    net_amount: Decimal = Decimal('0.0')
    extra_service_fee: Decimal = Decimal('0.0')
    shard_progress_total: int = 0
    shard_progress_completed: int = 0
    shard_txids_fanout: List[str] = field(default_factory=list)
    shard_txids_final: List[str] = field(default_factory=list)
    shard_txids_hops: List[List[str]] = field(default_factory=list)
    status: str = 'pending'
    created_at: datetime = field(default_factory=datetime.now)
    txid1: Optional[str] = None
    txid2: Optional[str] = None
    mix_address: Optional[str] = None
    confirmations: int = 0
    required_conf: int = 6
    error: Optional[str] = None
    last_poll_at: datetime = field(default_factory=datetime.now)
    last_update_at: datetime = field(default_factory=datetime.now)


class MixingService:
    def __init__(self):
        self._ensure_env()
        # Initialize RPC with retry logic wrapper
        self._init_rpc()
        
        self.jobs: Dict[str, MixJob] = {}
        self.lock = threading.Lock()
        self._load_state()
        self.monitors: Dict[str, str] = {}
        self.addr_pool: List[str] = []
        try:
            self._ensure_wallet_unlocked()
        except Exception:
            pass
        threading.Thread(target=self._guardian, daemon=True).start()

    def _init_rpc(self):
        self.rpc = jm_jsonrpc.JsonRpc(
            os.environ.get('ABCMINT_RPC_HOST', '127.0.0.1'),
            int(os.environ.get('ABCMINT_RPC_PORT', '8332')),
            os.environ.get('ABCMINT_RPC_USER', ''),
            os.environ.get('ABCMINT_RPC_PASSWORD', '')
        )
        
        # Monkey patch the call method to add retry logic
        original_call = self.rpc.call
        
        def safe_call(method, params=None):
            retries = 3
            delay = 1
            last_err = None
            for i in range(retries):
                try:
                    return original_call(method, params)
                except Exception as e:
                    last_err = e
                    # If it's a connection error, wait and retry
                    if 'CannotSendRequest' in str(e) or 'Connection refused' in str(e) or 'Remote end closed connection' in str(e):
                        time.sleep(delay)
                        delay *= 2
                        # Re-initialize connection if possible (JsonRpc implementation usually handles this, 
                        # but creating a new instance forces a fresh http.client connection)
                        try:
                             self.rpc = jm_jsonrpc.JsonRpc(
                                os.environ.get('ABCMINT_RPC_HOST', '127.0.0.1'),
                                int(os.environ.get('ABCMINT_RPC_PORT', '8332')),
                                os.environ.get('ABCMINT_RPC_USER', ''),
                                os.environ.get('ABCMINT_RPC_PASSWORD', '')
                            )
                             # Update the interface to use the new rpc instance
                             self.iface.jsonRpc = self.rpc
                        except:
                            pass
                        continue
                    raise e
            raise last_err

        self.rpc.call = safe_call
        self.iface = abcmint_iface.ABCmintBlockchainInterface(self.rpc, '')

    def _ensure_env(self):
        defaults = {
            'ABCMINT_RPC_HOST': '127.0.0.1',
            'ABCMINT_RPC_PORT': '8332',
            'ABCMINT_RPC_USER': '',
            'ABCMINT_RPC_PASSWORD': '',
            'FIXED_FEE': '0.01',
            'DEPOSIT_EXTRA': '0.1',
            'MINCONF': '1',
            'MINCONF_STEP2': '6',
            'REQUIRED_CONF': '6',
            'CONF_POLL_INTERVAL_SEC': '15',
            'ABCMINT_DEDUCTION_MODE': 'deduct',
            'ABCMINT_FEE_ADDRESS': '8P3aFLXr9F6BPvzC6yR4fTiD4RzFT3wJbjhyMn5uJ1ZFARTRb'
        }
        tier_defaults = {
            'FEE_BASE_P': '0.003',
            'FEE_SHARD_P': '0.0008',
            'FEE_HOP_P': '0.0005',
            'FEE_MIN_P': '0.0025',
            'FEE_MAX_P': '0.012',
            'ABS_FEE_FLOOR': '0.001',
            'TX_FEE_PER_TX': '0.01',
            'MINER_FEE_CAP': '1',
            'MINCONF_SHARD': '0',  # Validated: 0 is safe and recommended for ABCMint to avoid lag
            'TIER_STANDARD_SHARDS': '3',
            'TIER_STANDARD_HOPS': '1',
            'TIER_ENHANCED_SHARDS': '5',
            'TIER_ENHANCED_HOPS': '2',
            'TIER_STRONG_SHARDS': '8',
            'TIER_STRONG_HOPS': '3'
        }
        for k, v in defaults.items():
            if k not in os.environ:
                os.environ[k] = v
        for k, v in tier_defaults.items():
            if k not in os.environ:
                os.environ[k] = v
        # clamp to recommended network levels
        try:
            rec = Decimal('0.01')
            fx = Decimal(os.environ.get('FIXED_FEE', '0.01'))
            if fx < rec:
                os.environ['FIXED_FEE'] = str(rec)
            txp = Decimal(os.environ.get('TX_FEE_PER_TX', '0.01'))
            if txp < rec:
                os.environ['TX_FEE_PER_TX'] = str(rec)
            os.environ['MINER_FEE_CAP'] = os.environ.get('MINER_FEE_CAP', '1')
        except Exception:
            os.environ['FIXED_FEE'] = '0.01'
            os.environ['TX_FEE_PER_TX'] = '0.01'
            os.environ['MINER_FEE_CAP'] = '1'

    def _prefetch_addresses(self, count: int) -> None:
        n = max(0, int(count))
        for _ in range(n):
            try:
                a = self.iface.get_new_address()
                if a:
                    self._label_address(a, 'NEIN')
                    self.addr_pool.append(a)
            except Exception:
                break

    def _get_address(self) -> str:
        if not self.addr_pool:
            self._prefetch_addresses(16)
        if not self.addr_pool:
            a = self.iface.get_new_address()
            self._label_address(a, 'NEIN')
            return a
        return self.addr_pool.pop(0)

    def _label_address(self, address: str, label: str) -> None:
        try:
            self.iface._rpc('setaccount', [address, label])
        except Exception:
            pass

    def _ensure_wallet_unlocked(self) -> None:
        info = self.iface._rpc('getinfo', [])
        if not info:
            return
        u = info.get('unlocked_until')
        if isinstance(u, int) and u == 0:
            pwd = os.environ.get('ABCMINT_WALLET_PASSPHRASE')
            tout = int(os.environ.get('ABCMINT_WALLET_PASSPHRASE_TIMEOUT', '120'))
            if pwd:
                try:
                    self.iface._rpc('walletpassphrase', [pwd, tout])
                except Exception:
                    pass

    def _state_path(self) -> str:
        # Use AppData for state persistence
        app_data = os.getenv('LOCALAPPDATA')
        if not app_data:
            app_data = os.path.expanduser('~')
        
        data_dir = os.path.join(app_data, 'JoinMarket-ABCMint')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return os.path.join(data_dir, 'jobs_state.json')

    def _load_state(self):
        try:
            path = self._state_path()
            if not os.path.exists(path):
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for jid, jd in data.items():
                try:
                    jd['amount'] = Decimal(str(jd.get('amount', 0)))
                    jd['deposit_received'] = Decimal(str(jd.get('deposit_received', 0)))
                    jd['deposit_required'] = Decimal(str(jd.get('deposit_required', 0)))
                    jd['fee_percent'] = Decimal(str(jd.get('fee_percent', 0)))
                    jd['abs_fee'] = Decimal(str(jd.get('abs_fee', 0)))
                    jd['miner_fee'] = Decimal(str(jd.get('miner_fee', 0)))
                    jd['net_amount'] = Decimal(str(jd.get('net_amount', 0)))
                    jd['extra_service_fee'] = Decimal(str(jd.get('extra_service_fee', 0)))

                    jd['created_at'] = datetime.fromisoformat(jd.get('created_at')) if isinstance(jd.get('created_at'), str) else datetime.now()
                    jd['last_poll_at'] = datetime.fromisoformat(jd.get('last_poll_at')) if isinstance(jd.get('last_poll_at'), str) else datetime.now()
                    jd['last_update_at'] = datetime.fromisoformat(jd.get('last_update_at')) if isinstance(jd.get('last_update_at'), str) else datetime.now()
                except Exception:
                    jd['created_at'] = datetime.now()
                    jd['last_poll_at'] = datetime.now()
                    jd['last_update_at'] = datetime.now()
                job = MixJob(**jd)
                self.jobs[jid] = job
        except Exception:
            pass

    def _save_state(self):
        try:
            with self.lock:
                data = {}
                for jid, j in self.jobs.items():
                    d = asdict(j)
                    d['amount'] = str(j.amount)
                    d['deposit_received'] = str(j.deposit_received)
                    d['deposit_required'] = str(j.deposit_required)
                    d['fee_percent'] = str(j.fee_percent)
                    d['abs_fee'] = str(j.abs_fee)
                    d['miner_fee'] = str(j.miner_fee)
                    d['net_amount'] = str(j.net_amount)
                    d['extra_service_fee'] = str(j.extra_service_fee)

                    d['created_at'] = j.created_at.isoformat()
                    d['last_poll_at'] = j.last_poll_at.isoformat()
                    d['last_update_at'] = j.last_update_at.isoformat()
                    data[jid] = d
            tmp_path = self._state_path() + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, self._state_path())
        except Exception:
            pass

    def _guardian(self):
        while True:
            try:
                with self.lock:
                    ids = list(self.jobs.keys())
                for jid in ids:
                    job = self.get_job(jid)
                    if not job:
                        continue
                    job.last_poll_at = datetime.now()
                    # Normal states
                    if job.status == 'waiting_deposit' and self.monitors.get(jid) != 'deposit':
                        threading.Thread(target=self._monitor_deposit, args=(jid,), daemon=True).start()
                        self.monitors[jid] = 'deposit'
                    if job.status == 'deposit_received' and self.monitors.get(jid) != 'deposit':
                        threading.Thread(target=self._monitor_deposit, args=(jid,), daemon=True).start()
                        self.monitors[jid] = 'deposit'
                    if job.status == 'waiting_confirmations' and self.monitors.get(jid) != 'confirm' and job.txid1:
                        threading.Thread(target=self._resume_confirmations, args=(jid,), daemon=True).start()
                        self.monitors[jid] = 'confirm'
                    
                    # Error recovery
                    has_shards = bool(job.shard_txids_fanout or [])
                    if job.status in ('mixing_step2', 'error') and has_shards and self.monitors.get(jid) != 'shard':
                        threading.Thread(target=self._resume_sharded_hops, args=(jid,), daemon=True).start()
                        self.monitors[jid] = 'shard'
                    
                    # Recover from error/stuck state where txid1 exists but no shards yet (Step 1 done/confirming)
                    if job.status in ('error', 'waiting_deposit') and job.txid1 and not has_shards and self.monitors.get(jid) != 'confirm':
                        threading.Thread(target=self._resume_confirmations, args=(jid,), daemon=True).start()
                        self.monitors[jid] = 'confirm'

                self._save_state()
            except Exception:
                pass
            time.sleep(10)

    def _resume_confirmations(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job or not job.txid1:
            return
        try:
            required_conf = int(os.environ['REQUIRED_CONF'])
            minconf2 = int(os.environ['MINCONF_STEP2'])
            min_needed = max(required_conf, minconf2)
            while True:
                info = self.iface._rpc('gettransaction', [job.txid1])
                conf = int(info.get('confirmations', 0)) if info else 0
                job.confirmations = conf
                job.last_update_at = datetime.now()
                self._save_state()
                if conf >= min_needed:
                    break
                time.sleep(int(os.environ['CONF_POLL_INTERVAL_SEC']))
            src_addr = job.mix_address or os.environ.get('ABCMINT_PRIMARY_ADDRESS', '')
            while True:
                utxos_ready = self.iface.listunspent_for_addresses([src_addr], minconf=minconf2)
                if utxos_ready:
                    break
                time.sleep(int(os.environ['CONF_POLL_INTERVAL_SEC']))
                self._save_state()
            job.status = 'mixing_step2'
            self._execute_sharded_hops(job, src_addr)
            job.status = 'completed'
            self.monitors.pop(job_id, None)
            self._save_state()
        except Exception as e:
            job.status = 'error'
            job.error = str(e)
            self.monitors.pop(job_id, None)
            self._save_state()

    def _resume_sharded_hops(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job or not job.mix_address:
            return
        try:
            job.status = 'mixing_step2'
            self._execute_sharded_hops(job, job.mix_address)
            job.status = 'completed'
            self.monitors.pop(job_id, None)
            self._save_state()
        except Exception as e:
            job.status = 'error'
            job.error = str(e)
            self.monitors.pop(job_id, None)
            self._save_state()

    def _derive_shard_sources(self, job: MixJob) -> List[Dict[str, Any]]:
        minconf_shard = int(os.environ.get('MINCONF_SHARD', '0'))
        utxos = self.iface.listunspent(minconf=minconf_shard) or []
        txid_set = set(job.shard_txids_fanout or [])
        for hop_list in (job.shard_txids_hops or []):
            txid_set.update(hop_list)
        entries: List[Dict[str, Any]] = []
        for u in utxos:
            t = u.get('txid')
            if t and t in txid_set:
                try:
                    entries.append({'address': u.get('address'), 'amount': Decimal(str(u.get('amount', 0))), 'txid': t, 'vout': int(u.get('vout', 0))})
                except Exception:
                    continue
        return [e for e in entries if e.get('address') and e.get('amount', Decimal(0)) > 0]

    def create_job(self, target_address: str, amount: Decimal, shard_count: int = None, hop_count: int = None) -> MixJob:
        job_id = str(uuid.uuid4())
        deposit_address = self.iface.get_new_address()
        try:
            self._label_address(deposit_address, 'DEP')
        except Exception:
            pass
        sc = shard_count if shard_count is not None else int(os.environ.get('TIER_STANDARD_SHARDS', '3'))
        hc = hop_count if hop_count is not None else int(os.environ.get('TIER_STANDARD_HOPS', '1'))
        q = fee_model.quote(amount, sc, hc)
        step1_fee = Decimal(os.environ.get('DEPOSIT_EXTRA', '0.1'))
        miner_est = q['miner_fee']
        cap = q['cap']
        extra_service = q['extra_to_service']
        job = MixJob(
            job_id=job_id,
            target_address=target_address,
            amount=amount,
            deposit_address=deposit_address,
            deposit_required=(amount + step1_fee + extra_service).quantize(Decimal('0.00000001')),
            shard_count=sc,
            hop_count=hc,
            fee_percent=q['percent'],
            abs_fee=q['abs_fee'],
            miner_fee=q['miner_fee'],
            tx_count=q['tx_count'],
            net_amount=q['net_amount'],
            extra_service_fee=extra_service
        )
        with self.lock:
            self.jobs[job_id] = job
        self._save_state()
        threading.Thread(target=self._monitor_deposit, args=(job_id,), daemon=True).start()
        self.monitors[job_id] = 'deposit'
        return job

    def get_job(self, job_id: str) -> Optional[MixJob]:
        return self.jobs.get(job_id)

    def _monitor_deposit(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        try:
            job.status = 'waiting_deposit'
            job.error = None
            while True:
                utxos = self.iface.listunspent_for_addresses([job.deposit_address], minconf=0)
                total = sum(Decimal(str(u.get('amount', 0))) for u in utxos)
                
                # Check if funds were received but already spent (recovery from crash post-broadcast)
                if total == 0:
                    try:
                        received = Decimal(str(self.iface._rpc('getreceivedbyaddress', [job.deposit_address, 0])))
                        if received >= job.deposit_required:
                            # Funds arrived and moved. Transition to next step to trigger error or recovery.
                            # Calling _execute_mixing will fail with "No UTXOs" -> Error state.
                            # This prevents infinite "recovering" loop.
                            job.status = 'deposit_received'
                            job.last_update_at = datetime.now()
                            self._execute_mixing(job_id)
                            break
                    except Exception:
                        pass

                if total == 0:
                    all_utxos = self.iface.listunspent(minconf=0)
                    total = sum(
                        Decimal(str(u.get('amount', 0)))
                        for u in (all_utxos or [])
                        if u.get('address') == job.deposit_address
                    )
                job.deposit_received = total
                if total >= job.deposit_required:
                    job.status = 'deposit_received'
                    job.last_update_at = datetime.now()
                    minconf_step1 = int(os.environ.get('MINCONF', '1'))
                    utxos_ready = self.iface.listunspent_for_addresses([job.deposit_address], minconf=minconf_step1)
                    if utxos_ready:
                        self._execute_mixing(job_id)
                        break
                    # Not enough confirmations for step 1, continue waiting
                self._save_state()
                time.sleep(15)
        except Exception as e:
            job.status = 'error'
            job.error = str(e)
            self.monitors.pop(job_id, None)
            self._save_state()

    def _execute_mixing(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        try:
            try:
                self._ensure_wallet_unlocked()
            except Exception:
                pass
            job.status = 'mixing_step1'
            os.environ['ABCMINT_DEDUCTION_MODE'] = os.environ.get('ABCMINT_DEDUCTION_MODE', 'deduct')
            os.environ['ABCMINT_DEDUCTION_ENABLED'] = 'true'
            os.environ['ABCMINT_DEDUCTION_PERCENT'] = str(job.fee_percent)
            # STEP 1: Deduct fee from deposit_address and return change to internal address
            minconf_step1 = int(os.environ.get('MINCONF', '1'))
            utxos = self.iface.listunspent_for_addresses([job.deposit_address], minconf=minconf_step1)
            if not utxos:
                raise RuntimeError('No UTXOs at deposit address')
            
            fee_guess = Decimal(os.environ.get('TX_FEE_PER_TX', os.environ.get('FIXED_FEE', '0.01')))
            ded_percent = job.fee_percent
            ded_amt = (job.amount * ded_percent).quantize(Decimal('0.00000001'))
            selected, total = [], Decimal('0')
            
            # Generate internal mixing address
            mix_addr = self._get_address()
            try:
                self._label_address(mix_addr, 'MIX')
            except Exception:
                pass
            outputs1 = {mix_addr: job.amount}
            job.mix_address = mix_addr
            os.environ['ABCMINT_PRIMARY_ADDRESS'] = mix_addr
            outputs1 = self.iface.apply_deduction_outputs(job.amount, outputs1)
            fee_addr = os.environ.get('ABCMINT_FEE_ADDRESS')
            if fee_addr and job.extra_service_fee > Decimal('0'):
                v = self.iface._rpc('validateaddress', [fee_addr])
                if v and v.get('isvalid', False):
                    outputs1[fee_addr] = (outputs1.get(fee_addr, Decimal('0.0')) + job.extra_service_fee).quantize(Decimal('0.00000001'))
            
            num_outputs_est = len(outputs1)
            for u in sorted(utxos, key=lambda x: Decimal(str(x.get('amount', 0))), reverse=True):
                a = Decimal(str(u.get('amount', 0)))
                if a <= 0:
                    continue
                ident = {'txid': u['txid'], 'vout': int(u['vout'])}
                selected.append(ident)
                total += a
                mf = self.iface.estimate_fee_coins_for_counts(len(selected), num_outputs_est + 1)
                miner_fee = mf
                need = sum(outputs1.values()) + miner_fee
                if total >= need:
                    break
            if total < (sum(outputs1.values()) + miner_fee):
                raise RuntimeError('Insufficient funds for step 1')
            dust_floor = Decimal(os.environ.get('DUST_COINS_FLOOR', '0.000055'))
            change1 = (total - (sum(outputs1.values()) + miner_fee)).quantize(Decimal('0.00000001'))
            if change1 > Decimal('0'):
                if change1 <= dust_floor:
                    outputs1[mix_addr] = (outputs1[mix_addr] + change1).quantize(Decimal('0.00000001'))
                else:
                    change_addr1 = self._get_address()
                    try:
                        self._label_address(change_addr1, 'CH')
                    except Exception:
                        pass
                    outputs1[change_addr1] = (outputs1.get(change_addr1, Decimal('0.0')) + change1).quantize(Decimal('0.00000001'))
            
            raw1 = self.iface.create_raw_transaction(selected, outputs1)
            signed1 = self.iface.sign_raw_transaction(raw1)
            job.txid1 = self.iface.broadcast_raw_transaction(signed1)
            self._save_state()
            
            # Wait for confirmations
            job.status = 'waiting_confirmations'
            job.error = ''
            self.monitors[job_id] = 'confirm'
            required_conf = int(os.environ['REQUIRED_CONF'])
            minconf2 = int(os.environ['MINCONF_STEP2'])
            min_needed = max(required_conf, minconf2)
            while True:
                info = self.iface._rpc('gettransaction', [job.txid1])
                conf = int(info.get('confirmations', 0)) if info else 0
                job.confirmations = conf
                job.last_update_at = datetime.now()
                if conf >= min_needed:
                    break
                time.sleep(int(os.environ['CONF_POLL_INTERVAL_SEC']))
                self._save_state()
            while True:
                utxos_ready = self.iface.listunspent_for_addresses([mix_addr], minconf=minconf2)
                if utxos_ready:
                    break
                time.sleep(int(os.environ['CONF_POLL_INTERVAL_SEC']))
                self._save_state()
            
            job.status = 'mixing_step2'
            job.error = ''
            self._execute_sharded_hops(job, mix_addr)
            job.status = 'completed'
            job.error = ''
            self._save_state()
            self.monitors.pop(job_id, None)
            self._save_state()
            
        except Exception as e:
            job.status = 'error'
            job.error = str(e)
            self.monitors.pop(job_id, None)
            self._save_state()

    def _compute_shard_amounts(self, total: Decimal, shards: int) -> List[Decimal]:
        shards = max(1, int(shards))
        base = (total / Decimal(shards)).quantize(Decimal('0.00000001'))
        amounts = [base] * (shards - 1)
        last = total - base * Decimal(shards - 1)
        amounts.append(max(Decimal('0.0'), last))
        return [a for a in amounts if a > 0]

    def _single_send_from(self, from_addrs: List[str], amount: Decimal, fee: Decimal, to_addr: str, minconf: int) -> str:
        utxos = self.iface.listunspent_for_addresses(from_addrs, minconf=minconf)
        if not utxos:
            raise RuntimeError('No UTXOs available')
        target = amount + fee
        selected, total = [], Decimal('0')
        for u in sorted(utxos, key=lambda x: Decimal(str(x.get('amount', 0))), reverse=True):
            a = Decimal(str(u.get('amount', 0)))
            if a <= 0:
                continue
            selected.append({'txid': u['txid'], 'vout': int(u['vout'])})
            total += a
            if total >= target:
                break
        if total < target:
            amount = max(Decimal('0.0'), total - fee)
            target = amount + fee
        outputs = {to_addr: amount}
        miner_fee = self.iface.estimate_fee_coins_for_counts(len(selected), 2)
        need = amount + miner_fee
        if total < need:
            for u in sorted(utxos, key=lambda x: Decimal(str(x.get('amount', 0))), reverse=True):
                ident = {'txid': u['txid'], 'vout': int(u['vout'])}
                if ident in selected:
                    continue
                a = Decimal(str(u.get('amount', 0)))
                if a <= 0:
                    continue
                selected.append(ident)
                total += a
                miner_fee = self.iface.estimate_fee_coins_for_counts(len(selected), 2)
                need = amount + miner_fee
                if total >= need:
                    break
        change_dec = (total - need).quantize(Decimal('0.00000001'))
        dust_floor = Decimal(os.environ.get('DUST_COINS_FLOOR', '0.000055'))
        if change_dec > Decimal('0'):
            if change_dec <= dust_floor:
                outputs[to_addr] = (outputs.get(to_addr, Decimal('0.0')) + change_dec).quantize(Decimal('0.00000001'))
            else:
                change_addr = self._get_address()
                outputs[change_addr] = (outputs.get(change_addr, Decimal('0.0')) + change_dec).quantize(Decimal('0.00000001'))
        raw = self.iface.create_raw_transaction(selected, outputs)
        signed = self.iface.sign_raw_transaction(raw)
        try:
            txid = self.iface.broadcast_raw_transaction(signed)
            return txid
        except Exception:
            if minconf == 0:
                wait_s = int(os.environ.get('CONF_POLL_INTERVAL_SEC', '15'))
                for _ in range(6):
                    time.sleep(wait_s)
                    ready = self.iface.listunspent_for_addresses(from_addrs, minconf=1)
                    if ready:
                        return self._single_send_from(from_addrs, amount, fee, to_addr, 1)
            raise RuntimeError('broadcast failed minconf=' + str(minconf) + ' inputs=' + str(len(selected)) + ' outputs=' + str(len(outputs)))

    def _process_shard_sequence(self, job: MixJob, entry: Dict[str, Any], fee_guess: Decimal, minconf_shard: int):
        src_addr = entry['address']
        current_amt = entry['amount']
        src_txid = entry['txid']
        
        # Find or create hop list
        current_hops_list = []
        found_list = False
        
        # 1. Try to find in existing hop lists (Resume from Hop)
        for h_list in job.shard_txids_hops:
            if src_txid in h_list:
                current_hops_list = h_list
                found_list = True
                break
        
        # 2. If not found, check if it's a fanout TXID (Resume from Fanout)
        if not found_list:
            try:
                fan_idx = job.shard_txids_fanout.index(src_txid)
                # Robustness: Ensure hops list is long enough to avoid index error
                while len(job.shard_txids_hops) <= fan_idx:
                    job.shard_txids_hops.append([])
                
                if fan_idx < len(job.shard_txids_hops):
                    current_hops_list = job.shard_txids_hops[fan_idx]
                    found_list = True
            except ValueError:
                pass

        # 3. If still not found, create new list
        if not found_list:
            current_hops_list = []
            job.shard_txids_hops.append(current_hops_list)

        # Calculate remaining hops needed
        hops_done = len(current_hops_list)
        hops_needed = max(0, int(job.hop_count) - hops_done)

        for _ in range(hops_needed):
            # Safety check: If funds are exhausted by fees, stop to avoid dust errors or infinite loops
            if current_amt <= fee_guess:
                # Mark as completed (failed path) to allow job to finish
                job.shard_progress_completed += 1
                return

            next_addr = self._get_address()
            try:
                self._label_address(next_addr, 'H')
            except Exception:
                pass
            txid_hop = self._single_send_from([src_addr], max(Decimal('0.0'), current_amt).quantize(Decimal('0.00000001')), fee_guess, next_addr, minconf=minconf_shard)
            current_hops_list.append(txid_hop)
            self._save_state()
            src_addr = next_addr
            current_amt = max(Decimal('0.0'), current_amt - fee_guess).quantize(Decimal('0.00000001'))

        txid_fin = self._single_send_from([src_addr], max(Decimal('0.0'), current_amt).quantize(Decimal('0.00000001')), fee_guess, job.target_address, minconf=minconf_shard)
        job.shard_txids_final.append(txid_fin)
        job.shard_progress_completed += 1
        self._save_state()

    def _execute_sharded_hops(self, job: MixJob, mix_addr: str):
        fee_guess = Decimal(os.environ.get('TX_FEE_PER_TX', os.environ.get('FIXED_FEE', '0.01')))
        minconf2 = int(os.environ['MINCONF_STEP2'])
        minconf_shard = int(os.environ.get('MINCONF_SHARD', '0'))

        # Initialize lists if needed (first run)
        if job.shard_txids_fanout is None: job.shard_txids_fanout = []
        if job.shard_txids_final is None: job.shard_txids_final = []
        if job.shard_txids_hops is None: job.shard_txids_hops = []

        # 1. Process existing shards (Resume/Continue)
        src_entries = self._derive_shard_sources(job)
        for entry in src_entries:
            try:
                self._process_shard_sequence(job, entry, fee_guess, minconf_shard)
            except Exception:
                pass # Log error but allow other shards to proceed

        # 2. Process remaining funds in mix address (New Fanouts)
        utxos2 = self.iface.listunspent_for_addresses([mix_addr], minconf=minconf2)
        if utxos2:
            available2 = sum(Decimal(str(u.get('amount', 0))) for u in utxos2)
            done_count = len(job.shard_txids_fanout)
            rem_count = max(1, int(job.shard_count) - done_count)
            
            # Calculate net amount for remaining part
            # Note: job.net_amount is the target total. We should try to match it proportionally?
            # Or just split available funds. Splitting available funds is safer for consistency.
            amounts = self._compute_shard_amounts(available2, rem_count)
            
            # Prefetch addresses
            # Need: 1 (Shard) + Hops + 1 (Target, no new addr) per shard path.
            # Plus potential change addresses for each transaction.
            # Safe buffer: Shards * (Hops + 4)
            need_addrs = len(amounts) * (int(job.hop_count) + 4)
            self._prefetch_addresses(need_addrs)
            
            for idx, amt in enumerate(amounts):
                shard_addr = self._get_address()
                try:
                    self._label_address(shard_addr, 'S' + str(done_count + idx + 1))
                except Exception:
                    pass
                
                txid_fan = self._single_send_from([mix_addr], amt, fee_guess, shard_addr, minconf=minconf_shard)
                job.shard_txids_fanout.append(txid_fan)
                self._save_state()
                
                # Create entry for sequence processing
                entry = {
                    'address': shard_addr, 
                    'amount': amt, 
                    'txid': txid_fan
                }
                try:
                    self._process_shard_sequence(job, entry, fee_guess, minconf_shard)
                except Exception:
                    pass # Continue to next shard even if this one fails
        self._save_state()

    def resume_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
            
        if self.monitors.get(job_id):
            return True

        has_shards = bool(job.shard_txids_fanout or [])
        
        # 1. Recover based on progress (txid1 exists)
        if job.txid1:
            if has_shards:
                threading.Thread(target=self._resume_sharded_hops, args=(job_id,), daemon=True).start()
                self.monitors[job_id] = 'shard'
                return True
            else:
                # Step 1 done, but no shards -> waiting confirmations
                threading.Thread(target=self._resume_confirmations, args=(job_id,), daemon=True).start()
                self.monitors[job_id] = 'confirm'
                return True

        # 2. Recover based on status (no txid1 yet)
        if job.status in ('waiting_deposit', 'deposit_received', 'error'):
            threading.Thread(target=self._monitor_deposit, args=(job_id,), daemon=True).start()
            self.monitors[job_id] = 'deposit'
            return True
            
        return True
