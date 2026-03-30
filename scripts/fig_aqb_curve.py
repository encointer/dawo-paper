#!/usr/bin/env python3
"""Fig 5: AQB threshold curve with empirical proposal outcomes.

Uses on-chain electorate sizes from cached governance proposals
rather than recomputing them, ensuring consistency with the chain.
"""
from common import *
from collections import defaultdict
import numpy as np


MIN_TURNOUT_PERMILLE = 50  # 5% = 50 per mille


def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    cache_db = client['encointer-kusama-accounting-backend-cache']

    # 1. Get cached proposals with on-chain electorate, turnout, ayes, state
    cached = list(cache_db.general_cache.find({'cacheIdentifier': 'governance-proposal'}))
    proposals_cached = {}
    for c in cached:
        d = c.get('data', {})
        pid = d.get('id')
        if pid is not None:
            proposals_cached[pid] = d

    # 2. For proposals not in cache (still Ongoing), get from vote events
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted'
    }))
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced'
    }))

    # Aggregate votes for non-cached proposals
    vote_agg = defaultdict(lambda: {'turnout': 0, 'ayes': 0})
    for v in vote_events:
        pid = v['data'].get('proposalId', v['data'].get(0))
        nv = int(v['data'].get('numVotes', v['data'].get(2, 0)))
        vote = v['data'].get('vote', v['data'].get(1))
        vote_agg[pid]['turnout'] += nv
        if vote == 'Aye' or (isinstance(vote, dict) and 'aye' in str(vote).lower()):
            vote_agg[pid]['ayes'] += nv

    # Build final proposal list
    proposals = []
    for s in submitted:
        pid = s['data']['proposalId']
        action = s['data'].get('proposalAction', {})
        atype = list(action.keys())[0] if isinstance(action, dict) else str(action)

        if pid in proposals_cached:
            d = proposals_cached[pid]
            electorate = d.get('electorateSize', 0)
            turnout = d.get('turnout', 0)
            ayes = d.get('ayes', 0)
            state = d.get('state', 'Ongoing')
        else:
            electorate = 0
            turnout = vote_agg[pid]['turnout']
            ayes = vote_agg[pid]['ayes']
            state = 'Ongoing'

        proposals.append({
            'id': pid,
            'action_type': atype,
            'state': state,
            'electorate': electorate,
            'turnout': turnout,
            'ayes': ayes,
            'turnout_pct': turnout / electorate * 100 if electorate > 0 else 0,
            'approval_pct': ayes / turnout * 100 if turnout > 0 else 0,
        })

    # Stats
    states = defaultdict(int)
    action_types = defaultdict(int)
    for p in proposals:
        states[p['state']] += 1
        action_types[p['action_type']] += 1

    print(f"Total proposals: {len(proposals)}")
    print(f"States: {dict(states)}")
    print(f"Action types: {dict(sorted(action_types.items(), key=lambda x: -x[1]))}")

    voted = [p for p in proposals if p['turnout'] > 0]
    print(f"\nProposals with votes: {len(voted)}")
    if voted:
        print(f"Mean turnout%: {np.mean([p['turnout_pct'] for p in voted]):.1f}")
        print(f"Mean approval%: {np.mean([p['approval_pct'] for p in voted]):.1f}")

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_SINGLE, 3.0))

    # Theoretical AQB curve
    t_frac = np.linspace(0.001, 1.0, 200)
    threshold = 1.0 / (1.0 + np.sqrt(t_frac))
    ax.plot(t_frac * 100, threshold * 100, 'k-', linewidth=1.5, label='AQB threshold')
    ax.fill_between(t_frac * 100, threshold * 100, 100, alpha=0.1, color='green')
    ax.fill_between(t_frac * 100, 0, threshold * 100, alpha=0.1, color='red')

    # MinTurnout vertical line at 5%
    min_turnout_pct = MIN_TURNOUT_PERMILLE / 10
    ax.axvline(x=min_turnout_pct, color='black', linestyle=':', linewidth=1.0,
               label=f'MinTurnout ({min_turnout_pct:.0f}%)')

    # Scatter proposals
    state_colors = {
        'Approved': '#2ca02c', 'Enacted': '#2ca02c',
        'Rejected': '#d62728', 'SupersededBy': '#7f7f7f',
        'Confirming': '#ff7f0e', 'Ongoing': '#1f77b4'
    }
    state_markers = {
        'Approved': '.', 'Enacted': '.',
        'Rejected': 'x', 'SupersededBy': 'd',
        'Confirming': 's', 'Ongoing': '^'
    }

    for state in ['Enacted', 'Approved', 'Rejected', 'SupersededBy', 'Confirming', 'Ongoing']:
        pts = [p for p in proposals if p['state'] == state and p['turnout'] > 0]
        if pts:
            ax.scatter([p['turnout_pct'] for p in pts],
                       [p['approval_pct'] for p in pts],
                       c=state_colors.get(state, 'gray'),
                       marker=state_markers.get(state, 'o'),
                       s=25, label=f'{state} (n={len(pts)})',
                       zorder=5, edgecolors='black', linewidths=0.3)

    # Annotate zero-turnout rejected proposals
    n_zero = sum(1 for p in proposals if p['turnout'] == 0 and p['state'] == 'Rejected')
    if n_zero:
        ax.annotate(f'{n_zero} proposals expired\nwith zero turnout',
                    xy=(6, 50), fontsize=6, fontstyle='italic', color='#d62728',
                    ha='left', va='top')

    ax.set_xlabel('Turnout (% of electorate)')
    ax.set_ylabel('Approval threshold / actual (%)')
    ax.set_xlim(-1, 50)
    ax.set_ylim(45, 101)
    ax.legend(loc='right outside', fontsize=6)
    ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)

    savefig(fig, 'fig-aqb-curve.pdf')
    client.close()


if __name__ == '__main__':
    main()
