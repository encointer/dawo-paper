#!/usr/bin/env python3
"""Fig: Treasury governance timeline — all proposal types."""
from common import *
from datetime import datetime, timezone
from collections import defaultdict


def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # 1. Enacted treasury events (SpendNative, SpentAsset, GrantedSwapAssetOption)
    spend_native = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'SpentNative'
    }).sort('timestamp', 1))

    spend_asset = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'SpentAsset'
    }).sort('timestamp', 1))

    granted_swap = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'GrantedSwapAssetOption'
    }).sort('timestamp', 1))

    # 2. Exercised swaps
    exercised = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True
    }).sort('timestamp', 1))

    # 3. Approved proposals (before enactment)
    # Get all treasury-related proposal submissions
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted',
        '$or': [
            {'data.proposalAction.IssueSwapAssetOption': {'$exists': True}},
            {'data.proposalAction.SpendNative': {'$exists': True}},
            {'data.proposalAction.SpendAsset': {'$exists': True}},
            {'data.proposalAction.IssueSwapNativeOption': {'$exists': True}},
        ]
    }))
    treasury_pids = [s['data']['proposalId'] for s in submitted]

    approved = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalStateUpdated',
        'data.proposalId': {'$in': treasury_pids},
        'data.proposalState': 'Approved'
    }).sort('timestamp', 1))

    print(f"SpendNative enacted: {len(spend_native)}")
    print(f"SpendAsset enacted: {len(spend_asset)}")
    print(f"SwapAsset granted: {len(granted_swap)}")
    print(f"Swaps exercised: {len(exercised)}")
    print(f"Treasury proposals approved: {len(approved)}")

    # 4. Build cumulative timelines
    def to_dt(ts):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

    categories = {
        'SpendNative enacted': (spend_native, '#2ca02c', '-'),
        'SpendAsset enacted': (spend_asset, '#9467bd', '-'),
        'SwapAsset granted': (granted_swap, '#1f77b4', '-'),
        'Swap exercised': (exercised, '#ff7f0e', '--'),
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
