#!/usr/bin/env python3
"""A3: Adaptive Quorum Biasing visualization with proposal scatter."""
from common import *
from collections import defaultdict
import numpy as np
import math

def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # Get all proposal events
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalSubmitted'
    }))
    state_updates = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalStateUpdated'
    }))
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'VotePlaced'
    }))

    # Build proposal info
    proposals = {}
    for s in submitted:
        pid = s['data']['proposalId']
        action = s['data'].get('proposalAction', {})
        action_type = list(action.keys())[0] if isinstance(action, dict) else str(action)
        proposals[pid] = {
            'id': pid,
            'action_type': action_type,
            'state': 'Ongoing',
            'turnout': 0,
            'ayes': 0,
            'block': s['blockNumber']
        }

    # Get final state for each proposal
    for su in state_updates:
        pid = su['data']['proposalId']
        state = su['data']['proposalState']
        if pid in proposals:
            if isinstance(state, str):
                proposals[pid]['state'] = state
            elif isinstance(state, dict):
                key = list(state.keys())[0]
                proposals[pid]['state'] = key

    # Aggregate votes per proposal
    for v in vote_events:
        pid = v['data'].get('proposalId', v['data'].get(0))
        nv = int(v['data'].get('numVotes', v['data'].get(2, 0)))
        vote = v['data'].get('vote', v['data'].get(1))
        if pid in proposals:
            proposals[pid]['turnout'] += nv
            is_aye = vote == 'Aye' or (isinstance(vote, dict) and 'aye' in str(vote).lower())
            if is_aye:
                proposals[pid]['ayes'] += nv

    # Estimate electorate from ceremony data (sum of reputables in voting window)
    # Use rewards_data for approximate electorate
    cache_db = client['encointer-kusama-accounting-backend-cache']
    rewards_docs = list(cache_db['rewards_data'].find())
    # Build cindex -> total participants across all communities
    cindex_participants = defaultdict(int)
    for doc in rewards_docs:
        for ci, info in doc['data'].items():
            cindex_participants[int(ci)] += info['numParticipants']

    # Get block -> cindex mapping for proposal blocks
    proposal_blocks = [p['block'] for p in proposals.values()]
    blocks = list(pindex.blocks.find(
        {'height': {'$in': proposal_blocks}},
        {'height': 1, 'cindex': 1}
    ))
    block_cindex = {b['height']: b.get('cindex', 0) for b in blocks}

    # For each proposal, estimate electorate from reputation window
    REP_LIFETIME = 5
    for pid, p in proposals.items():
        ci = block_cindex.get(p['block'], 0)
        if ci:
            # Electorate = sum of participants in [ci-R+1, ci-2]
            window = range(max(1, ci - REP_LIFETIME + 1), ci - 1)
            electorate = sum(cindex_participants.get(c, 0) for c in window)
            p['electorate'] = max(electorate, 1)
            p['turnout_pct'] = p['turnout'] / p['electorate'] * 100 if p['electorate'] > 0 else 0
            p['approval_pct'] = p['ayes'] / p['turnout'] * 100 if p['turnout'] > 0 else 0
        else:
            p['electorate'] = 1
            p['turnout_pct'] = 0
            p['approval_pct'] = 0

    # Print summary stats
    states = defaultdict(int)
    action_types = defaultdict(int)
    for p in proposals.values():
        states[p['state']] += 1
        action_types[p['action_type']] += 1

    print(f"Total proposals: {len(proposals)}")
    print(f"States: {dict(states)}")
    print(f"Action types: {dict(sorted(action_types.items(), key=lambda x: -x[1]))}")

    voted_proposals = [p for p in proposals.values() if p['turnout'] > 0]
    print(f"\nProposals with votes: {len(voted_proposals)}")
    if voted_proposals:
        turnouts = [p['turnout_pct'] for p in voted_proposals]
        approvals = [p['approval_pct'] for p in voted_proposals]
        print(f"Mean turnout%: {np.mean(turnouts):.1f}")
        print(f"Mean approval%: {np.mean(approvals):.1f}")

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_SINGLE, 3.0))

    # Theoretical AQB curve
    t_frac = np.linspace(0.001, 1.0, 200)
    threshold = 1.0 / (1.0 + np.sqrt(t_frac))  # sqrt(E)/(sqrt(E)+sqrt(T)) with T/E = t_frac
    ax.plot(t_frac * 100, threshold * 100, 'k-', linewidth=1.5, label='AQB threshold')
    ax.fill_between(t_frac * 100, threshold * 100, 100, alpha=0.1, color='green')
    ax.fill_between(t_frac * 100, 0, threshold * 100, alpha=0.1, color='red')

    # Scatter proposals with votes
    state_colors = {
        'Approved': '#2ca02c', 'Enacted': '#2ca02c',
        'Rejected': '#d62728', 'SupersededBy': '#7f7f7f',
        'Confirming': '#ff7f0e', 'Ongoing': '#1f77b4'
    }
    state_markers = {
        'Approved': 'o', 'Enacted': 'o',
        'Rejected': 'x', 'SupersededBy': 'd',
        'Confirming': 's', 'Ongoing': '^'
    }

    for state in ['Enacted', 'Approved', 'Rejected', 'SupersededBy', 'Confirming', 'Ongoing']:
        pts = [p for p in proposals.values()
               if p['state'] == state and p['turnout'] > 0]
        if pts:
            ax.scatter([p['turnout_pct'] for p in pts],
                      [p['approval_pct'] for p in pts],
                      c=state_colors.get(state, 'gray'),
                      marker=state_markers.get(state, 'o'),
                      s=25, label=f'{state} (n={len(pts)})',
                      zorder=5, edgecolors='black', linewidths=0.3)

    # Annotate zero-turnout rejected proposals
    n_zero = sum(1 for p in proposals.values() if p['turnout'] == 0 and p['state'] == 'Rejected')
    if n_zero:
        ax.annotate(f'{n_zero} proposals expired\nwith zero turnout',
                   xy=(1, 99), fontsize=6, fontstyle='italic', color='#d62728',
                   ha='left', va='top')

    ax.set_xlabel('Turnout (% of electorate)')
    ax.set_ylabel('Approval threshold / actual (%)')
    ax.set_xlim(0, 105)
    ax.set_ylim(45, 101)
    ax.legend(loc='lower right', fontsize=6)

    savefig(fig, 'fig-aqb-curve.pdf')
    client.close()

if __name__ == '__main__':
    main()
