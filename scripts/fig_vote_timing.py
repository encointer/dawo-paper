#!/usr/bin/env python3
"""A4: Vote timing relative to ceremony attesting phases."""
from common import *
from collections import defaultdict
import numpy as np

def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # Get VotePlaced timestamps
    votes = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'VotePlaced'
    }, {'timestamp': 1, 'blockNumber': 1}))

    # Get attesting phase windows per cindex
    attesting = list(pindex.blocks.aggregate([
        {'$match': {'phase': 'ATTESTING'}},
        {'$group': {
            '_id': '$cindex',
            'start': {'$min': '$timestamp'},
            'end': {'$max': '$timestamp'}
        }},
        {'$sort': {'_id': 1}}
    ]))

    # For each vote, check if it falls within an attesting window
    att_windows = [(a['start'], a['end']) for a in attesting]
    in_attesting = 0
    total = 0
    vote_offsets = []  # offset from nearest attesting start, in hours

    for v in votes:
        ts = v.get('timestamp')
        if ts is None:
            continue
        total += 1
        in_att = False
        min_offset = float('inf')
        for start, end in att_windows:
            if start <= ts <= end:
                in_att = True
                offset_h = (ts - start) / 3600000
                min_offset = min(min_offset, abs(offset_h))
                break
            offset_h = (ts - start) / 3600000
            if abs(offset_h) < abs(min_offset):
                min_offset = offset_h

        if in_att:
            in_attesting += 1
            vote_offsets.append(min_offset)

    print(f"Total votes with timestamps: {total}")
    print(f"Votes during attesting phase: {in_attesting} ({in_attesting/total*100:.1f}%)")
    print(f"Votes outside attesting phase: {total - in_attesting}")

    # Plot: histogram of vote timestamps bucketed by day-of-week and hour
    from datetime import datetime, timezone
    vote_hours = []
    for v in votes:
        ts = v.get('timestamp')
        if ts:
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            vote_hours.append(dt.hour)

    fig, ax = plt.subplots(figsize=(FIG_WIDTH_SINGLE, 2.2))
    ax.hist(vote_hours, bins=24, range=(0, 24), color='#4878a8',
            edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Hour of Day (UTC)')
    ax.set_ylabel('Number of Votes')
    ax.set_xticks(range(0, 25, 4))
    ax.set_xlim(0, 24)

    # Note: attesting phase data in blocks collection is from 2022;
    # governance votes are 2024-2026, so overlay is not possible

    savefig(fig, 'fig-vote-timing.pdf')
    client.close()

if __name__ == '__main__':
    main()
