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
        'method': {'$in': ['GrantedSwapAssetOption', 'GrantedSwapNativeOption']}
    }).sort('timestamp', 1))

    # Spent events (exercises)
    spent = list(pindex.events.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['SpentAsset', 'SpentNative']}
    }).sort('timestamp', 1))

    print(f"Granted swap options: {len(granted)}")
    print(f"Swap exercises (spent): {len(spent)}")

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

    for s in spent:
        cid_data = s['data'].get('cid', '')
        ts = s.get('timestamp', 0)
        by_cid[cid_data].append({
            'type': 'spent',
            'timestamp': ts,
            'method': s['method']
        })

    for cid, events in by_cid.items():
        name = COMMUNITIES.get(cid, cid)
        n_granted = sum(1 for e in events if e['type'] == 'granted')
        n_spent = sum(1 for e in events if e['type'] == 'spent')
        print(f"  {name}: {n_granted} granted, {n_spent} exercises")

    # Plot timeline of all swap events
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_DOUBLE, 2.0))

    all_events = []
    for g in granted:
        ts = g.get('timestamp', 0)
        if ts:
            all_events.append((ts, 'Granted', g['data'].get('cid', '')))
    for s in spent:
        ts = s.get('timestamp', 0)
        if ts:
            all_events.append((ts, 'Exercised', s['data'].get('cid', '')))

    all_events.sort()

    if all_events:
        dates = [datetime.fromtimestamp(e[0]/1000, tz=timezone.utc) for e in all_events]
        types = [e[1] for e in all_events]
        cids = [COMMUNITIES.get(e[2], e[2][:8]) for e in all_events]

        # Cumulative granted and exercised over time
        cum_granted = []
        cum_exercised = []
        g_count = 0
        e_count = 0
        g_dates = []
        e_dates = []
        for d, t, c in zip(dates, types, cids):
            if t == 'Granted':
                g_count += 1
                g_dates.append(d)
                cum_granted.append(g_count)
            else:
                e_count += 1
                e_dates.append(d)
                cum_exercised.append(e_count)

        ax.step(g_dates, cum_granted, where='post', linewidth=1.2,
                color='#1f77b4', label=f'Cumulative granted (n={g_count})')
        if e_dates:
            ax.step(e_dates, cum_exercised, where='post', linewidth=1.2,
                    color='#2ca02c', label=f'Cumulative exercised (n={e_count})')

    ax.set_xlabel('Date')
    ax.set_ylabel('Swap Options')
    ax.legend(fontsize=7)
    ax.set_ylim(bottom=0)
    fig.autofmt_xdate()

    savefig(fig, 'fig-treasury-timeline.pdf')
    client.close()

if __name__ == '__main__':
    main()
