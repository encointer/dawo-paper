#!/usr/bin/env python3
"""A2: Voting power distribution analysis."""
from common import *
from collections import Counter
import numpy as np

def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # Get all VotePlaced events with numVotes (= voting power)
    votes = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'VotePlaced'
    }))

    # Extract voting power per vote
    powers = []
    for v in votes:
        nv = v['data'].get('numVotes', v['data'].get(2))
        if nv is not None:
            powers.append(int(nv))

    power_counts = Counter(powers)
    max_power = max(powers) if powers else 4

    print(f"Total votes: {len(powers)}")
    print(f"Power distribution: {dict(sorted(power_counts.items()))}")
    print(f"Mean voting power: {np.mean(powers):.2f}")
    print(f"Median voting power: {np.median(powers):.1f}")

    # Plot
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_SINGLE, 2.5))

    levels = list(range(1, max_power + 1))
    counts = [power_counts.get(p, 0) for p in levels]
    total = sum(counts)
    fractions = [c / total * 100 for c in counts]

    bars = ax.bar(levels, fractions, color='#4878a8', edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Voting Power')
    ax.set_ylabel('Fraction of Votes (%)')
    ax.set_xticks(levels)
    ax.set_ylim(bottom=0)

    # Annotate bars with counts
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                    f'n={count}', ha='center', va='bottom', fontsize=6)

    savefig(fig, 'fig-voting-power.pdf')
    client.close()

if __name__ == '__main__':
    main()
