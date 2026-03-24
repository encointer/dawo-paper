#!/usr/bin/env python3
"""A1: Ceremony participation time series per community."""
from common import *
import numpy as np

def main():
    setup_style()
    client = get_client()
    cache_db = client['encointer-kusama-accounting-backend-cache']

    # rewards_data has one doc per community with {cindex: {numParticipants, totalRewards}}
    docs = list(cache_db['rewards_data'].find())

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_DOUBLE, 2.5))

    markers = {'Nyota': 'o', 'Leu': 's', 'PayNuQ': '^', 'Green Bay': 'D'}
    colors = {'Nyota': '#1f77b4', 'Leu': '#ff7f0e', 'PayNuQ': '#2ca02c', 'Green Bay': '#d62728'}

    for doc in docs:
        cid = doc['cid']
        name = COMMUNITIES.get(cid, cid)
        data = doc['data']
        cindexes = sorted(int(k) for k in data.keys())
        participants = [data[str(c)]['numParticipants'] for c in cindexes]

        if max(participants) < 3:
            continue  # skip inactive communities

        ax.plot(cindexes, participants,
                marker=markers.get(name, '.'), markersize=3,
                color=colors.get(name, 'gray'),
                linewidth=1, label=name)

        # Print stats
        print(f"{name}: {len(cindexes)} ceremonies, "
              f"max {max(participants)}, mean {np.mean(participants):.1f}, "
              f"latest {participants[-1]}")

    ax.set_xlabel('Ceremony Index')
    ax.set_ylabel('Participants Rewarded')
    ax.legend(loc='upper left')
    ax.set_ylim(bottom=0)

    savefig(fig, 'fig-ceremony-participation.pdf')
    client.close()

if __name__ == '__main__':
    main()
