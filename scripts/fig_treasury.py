#!/usr/bin/env python3
"""Fig: Treasury governance timeline — all proposal types."""
from common import *
from datetime import datetime, timezone
from collections import defaultdict


def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # 1. SpendNative enacted (direct KSM payouts)
    spend_native = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'SpentNative'
    }).sort('timestamp', 1))

    # 2. SwapAsset granted (swap option enacted on-chain)
    granted_swap = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'GrantedSwapAssetOption'
    }).sort('timestamp', 1))

    # 3. SwapAsset exercised (beneficiary exercises swap option)
    exercised = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True
    }).sort('timestamp', 1))

    print(f"SpendNative enacted: {len(spend_native)}")
    print(f"SwapAsset granted: {len(granted_swap)}")
    print(f"SwapAsset exercised: {len(exercised)}")

    # 4. Build cumulative timelines
    def to_dt(ts):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

    categories = {
        'SpendNative enacted': (spend_native, '#2ca02c', '-'),
        'SwapAsset granted': (granted_swap, '#1f77b4', '-'),
        'SwapAsset exercised': (exercised, '#ff7f0e', '--'),
    }

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_DOUBLE, 2.4))

    for label, (events, color, ls) in categories.items():
        if not events:
            continue
        timestamps = []
        for e in events:
            ts = e.get('timestamp', 0)
            if ts:
                timestamps.append(ts)
        timestamps.sort()
        dates = [to_dt(ts) for ts in timestamps]
        cumulative = list(range(1, len(dates) + 1))
        ax.step(dates, cumulative, where='post', linewidth=1.2,
                color=color, linestyle=ls,
                label=f'{label} (n={len(dates)})')

    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Count')
    ax.legend(fontsize=6, loc='upper left')
    ax.set_ylim(bottom=0)
    fig.autofmt_xdate()

    savefig(fig, 'fig-treasury-timeline.pdf')
    client.close()


if __name__ == '__main__':
    main()
