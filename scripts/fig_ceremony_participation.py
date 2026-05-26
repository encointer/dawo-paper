#!/usr/bin/env python3
"""A1: Ceremony participation time series per community."""
from common import *
import numpy as np
from datetime import datetime, timedelta, timezone
import matplotlib.dates as mdates

# Anchor: cindex 98 = 2024-12-02, cycle = 10 days
ANCHOR_CINDEX = 98
ANCHOR_DATE = datetime(2024, 12, 2, tzinfo=timezone.utc)
CYCLE_DAYS = 10

# Paper data freeze date (inclusive). Matches generate_stats.py.
CUTOFF_CINDEX = 151

def cindex_to_date(cindex):
    return ANCHOR_DATE + timedelta(days=(cindex - ANCHOR_CINDEX) * CYCLE_DAYS)

def main():
    setup_style()
    client = get_client()
    cache_db = client['encointer-kusama-accounting-backend-cache']

    docs = list(cache_db['rewards_data'].find())

    fig, ax1 = plt.subplots(figsize=(FIG_WIDTH_DOUBLE, 2.8))

    markers = {
        'Leu Zürich': 'o', 'Nyota': 's', 'PayNuq': 'D'
    }
    colors = {
        'Leu Zürich': '#1f77b4', 'Nyota': '#ff7f0e', 'PayNuq': '#d62728'
    }
    SKIP = {'Green Bay Dollar'}

    all_cindexes = []
    for doc in docs:
        cid = doc['cid']
        name = COMMUNITIES.get(cid, cid)
        data = doc['data']
        cindexes = sorted(int(k) for k in data.keys() if int(k) <= CUTOFF_CINDEX)
        participants = [data[str(c)]['numParticipants'] for c in cindexes]

        if max(participants) < 3 or name in SKIP:
            continue

        all_cindexes.extend(cindexes)
        ax1.plot(cindexes, participants,
                 marker=markers.get(name, '.'), markersize=3,
                 color=colors.get(name, 'gray'),
                 linewidth=1, label=name)

        print(f"{name}: {len(cindexes)} ceremonies, "
              f"max {max(participants)}, mean {np.mean(participants):.1f}, "
              f"latest {participants[-1]}")

    ax1.set_xlabel('Ceremony Index')
    ax1.set_ylabel('Participants Rewarded')
    ax1.legend(loc='upper left')
    ax1.set_ylim(bottom=0)
    ax1.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)
    # Second x-axis with dates
    ax2 = ax1.twiny()
    ci_min, ci_max = min(all_cindexes), max(all_cindexes)
    ax2.set_xlim(ax1.get_xlim())

    # Place date ticks at ~yearly intervals
    tick_cindexes = list(range(ci_min, ci_max + 1, 36))  # ~1 year = 36 cycles
    if tick_cindexes[-1] < ci_max - 10:
        tick_cindexes.append(ci_max)
    tick_labels = [cindex_to_date(c).strftime('%b %Y') for c in tick_cindexes]
    ax2.set_xticks(tick_cindexes)
    ax2.set_xticklabels(tick_labels, fontsize=7)

    savefig(fig, 'fig-ceremony-participation.pdf')
    client.close()

if __name__ == '__main__':
    main()
