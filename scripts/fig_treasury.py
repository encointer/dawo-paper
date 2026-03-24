#!/usr/bin/env python3
"""A6: Treasury swap option activity timeline."""
from common import *
from datetime import datetime, timezone

def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # Granted swap options
    granted = list(pindex.events.find({
        'section': 'encointerTreasuries',
        'method': 'GrantedSwapAssetOption'
    }).sort('timestamp', 1))

    # Swap exercises are extrinsics (swapAsset / swapNative), not events
    exercises = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True
    }).sort('timestamp', 1))

    # Approved swap option proposals (submitted but not yet enacted)
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalSubmitted',
        'data.proposalAction.IssueSwapAssetOption': {'$exists': True}
    }))
    swap_pids = [s['data']['proposalId'] for s in submitted]

    approved = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalStateUpdated',
        'data.proposalId': {'$in': swap_pids},
        'data.proposalState': 'Approved'
    }).sort('timestamp', 1))

    print(f"Swap option proposals submitted: {len(submitted)}")
    print(f"Swap option proposals approved: {len(approved)}")
    print(f"Swap options granted (enacted): {len(granted)}")
    print(f"Swap options exercised (successful): {len(exercises)}")

    # Group by community
    from collections import defaultdict
    by_cid = defaultdict(list)
    for g in granted:
        cid_data = g['data'].get('cid', '')
        ts = g.get('timestamp', 0)
        by_cid[cid_data].append({
            'type': 'granted',
            'timestamp': ts,
            'method': g['method']
        })

    for ex in exercises:
        # Extrinsics use args.cid, not data.cid
        cid_data = ex.get('args', {}).get('cid', '')
        ts = ex.get('timestamp', 0)
        by_cid[cid_data].append({
            'type': 'exercised',
            'timestamp': ts,
            'method': ex['method']
        })

    for cid, events in by_cid.items():
        name = COMMUNITIES.get(cid, cid)
        n_granted = sum(1 for e in events if e['type'] == 'granted')
        n_exercised = sum(1 for e in events if e['type'] == 'exercised')
        print(f"  {name}: {n_granted} granted, {n_exercised} exercised")

    # Plot timeline of all swap events
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_DOUBLE, 2.0))

    # Build event list with three types
    all_events = []
    for a in approved:
        ts = a.get('timestamp', 0)
        if ts:
            all_events.append((ts, 'Approved'))
    for g in granted:
        ts = g.get('timestamp', 0)
        if ts:
            all_events.append((ts, 'Granted'))
    for ex in exercises:
        ts = ex.get('timestamp', 0)
        if ts:
            all_events.append((ts, 'Exercised'))

    all_events.sort()

    if all_events:
        a_dates, a_cum = [], []
        g_dates, g_cum = [], []
        e_dates, e_cum = [], []
        a_count = g_count = e_count = 0

        for ts, typ in all_events:
            d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            if typ == 'Approved':
                a_count += 1
                a_dates.append(d)
                a_cum.append(a_count)
            elif typ == 'Granted':
                g_count += 1
                g_dates.append(d)
                g_cum.append(g_count)
            else:
                e_count += 1
                e_dates.append(d)
                e_cum.append(e_count)

        ax.step(a_dates, a_cum, where='post', linewidth=1.2,
                color='#aaaaaa', linestyle='--',
                label=f'Approved (n={a_count})')
        ax.step(g_dates, g_cum, where='post', linewidth=1.2,
                color='#1f77b4',
                label=f'Granted / enacted (n={g_count})')
        if e_dates:
            ax.step(e_dates, e_cum, where='post', linewidth=1.2,
                    color='#2ca02c',
                    label=f'Exercised (n={e_count})')

    ax.set_xlabel('Date')
    ax.set_ylabel('Swap Options')
    ax.legend(fontsize=7)
    ax.set_ylim(bottom=0)
    fig.autofmt_xdate()

    savefig(fig, 'fig-treasury-timeline.pdf')
    client.close()

if __name__ == '__main__':
    main()
