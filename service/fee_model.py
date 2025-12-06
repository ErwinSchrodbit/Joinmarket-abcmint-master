import os

from decimal import Decimal

def _f(key, default):
    try:
        return Decimal(os.environ.get(key, str(default)))
    except Exception:
        return Decimal(str(default))

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def calc_fee_percent(shards, hops):
    base = _f('FEE_BASE_P', '0.003')
    shard_p = _f('FEE_SHARD_P', '0.0008')
    hop_p = _f('FEE_HOP_P', '0.0005')
    min_p = _f('FEE_MIN_P', '0.0025')
    # 上限のクランプを解除し、下限のみを保持
    return max(base + Decimal(shards) * shard_p + Decimal(hops) * hop_p, min_p)

def estimate_tx_count(shards, hops):
    # Actual execution:
    # 1. Fanout: 'shards' transactions (serial send from mix to shards)
    # 2. Hops: 'shards * hops' transactions
    # 3. Final: 'shards' transactions (shard/hop to target)
    # Total = 2 * shards + shards * hops
    return int(shards * 2 + shards * hops)

def calc_abs_fee(amount, percent):
    amount = Decimal(str(amount))
    percent = Decimal(str(percent))
    floor_v = _f('ABS_FEE_FLOOR', '0.001')
    return max(amount * percent, floor_v)

def calc_miner_fee(tx_count):
    per_tx = _f('TX_FEE_PER_TX', '0.01')
    return (Decimal(tx_count) * per_tx).quantize(Decimal('0.00000001'))

def quote(amount, shards, hops):
    amount = Decimal(str(amount))
    percent = calc_fee_percent(shards, hops)
    tx_count = estimate_tx_count(shards, hops)
    abs_fee = calc_abs_fee(amount, percent).quantize(Decimal('0.00000001'))
    miner_fee_est = calc_miner_fee(tx_count)
    cap = _f('MINER_FEE_CAP', '1.0')
    floor_v = _f('MIN_RELAY_FEE_FLOOR', '0.001')
    miner_fee = min(max(miner_fee_est, floor_v), cap).quantize(Decimal('0.00000001'))
    extra_to_service = max(Decimal('0.0'), miner_fee_est - cap).quantize(Decimal('0.00000001'))
    abs_fee = (abs_fee + extra_to_service).quantize(Decimal('0.00000001'))
    net_amount = max(Decimal('0.0'), amount - abs_fee - miner_fee).quantize(Decimal('0.00000001'))
    return {
        'percent': percent,
        'abs_fee': abs_fee,
        'miner_fee': miner_fee,
        'tx_count': tx_count,
        'net_amount': net_amount,
        'cap': cap,
        'extra_to_service': extra_to_service,
    }

def default_tiers():
    return [
        {'name': 'SL1', 'shards': int(os.environ.get('TIER_STANDARD_SHARDS', '3')), 'hops': int(os.environ.get('TIER_STANDARD_HOPS', '1'))},
        {'name': 'SL3', 'shards': int(os.environ.get('TIER_ENHANCED_SHARDS', '5')), 'hops': int(os.environ.get('TIER_ENHANCED_HOPS', '2'))},
        {'name': 'SL5', 'shards': int(os.environ.get('TIER_STRONG_SHARDS', '8')), 'hops': int(os.environ.get('TIER_STRONG_HOPS', '3'))},
    ]
