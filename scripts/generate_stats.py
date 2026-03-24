#!/usr/bin/env python3
"""Generate summary statistics for the paper (Section 6 tables)."""
from common import *
from collections import defaultdict
import json

def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    cache_db = client['encointer-kusama-accounting-backend-cache']
    acct_db = client['encointer-kusama-accounting']

    stats = {}

    # 1. Proposal summary by type and state
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted'
    }))
    state_updates = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalStateUpdated'
    }))
    votes = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced'
    }))
    vote_failed = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VoteFailed'
    }))

    # Build proposal map
    proposals = {}
    for s in submitted:
        pid = s['data']['proposalId']
        action = s['data'].get('proposalAction', {})
        atype = list(action.keys())[0] if isinstance(action, dict) else str(action)
        proposals[pid] = {'action_type': atype, 'state': 'Ongoing',
                         'timestamp': s.get('timestamp', 0)}

    for su in state_updates:
        pid = su['data']['proposalId']
        state = su['data']['proposalState']
        if pid in proposals:
            if isinstance(state, str):
                proposals[pid]['state'] = state
            elif isinstance(state, dict):
                proposals[pid]['state'] = list(state.keys())[0]

    # Type counts
    type_counts = defaultdict(int)
    state_counts = defaultdict(int)
    for p in proposals.values():
        type_counts[p['action_type']] += 1
        state_counts[p['state']] += 1

    stats['total_proposals'] = len(proposals)
    stats['proposals_by_type'] = dict(sorted(type_counts.items(), key=lambda x: -x[1]))
    stats['proposals_by_state'] = dict(sorted(state_counts.items(), key=lambda x: -x[1]))

    # 2. Vote summary
    stats['total_votes_placed'] = len(votes)
    stats['total_votes_failed'] = len(vote_failed)

    aye_votes = sum(1 for v in votes if v['data'].get('vote') == 'Aye')
    nay_votes = sum(1 for v in votes if v['data'].get('vote') == 'Nay')
    stats['aye_votes'] = aye_votes
    stats['nay_votes'] = nay_votes

    # 3. Community summary
    communities = list(acct_db['communities'].find())
    rewards_docs = list(cache_db['rewards_data'].find())

    community_stats = []
    for comm in communities:
        cid = comm.get('cid', '')
        name = comm.get('name', cid)

        # Find rewards data
        rd = next((d for d in rewards_docs if d['cid'] == cid), None)
        if rd:
            cindexes = sorted(int(k) for k in rd['data'].keys())
            participants = [rd['data'][str(c)]['numParticipants'] for c in cindexes]
            n_ceremonies = len(cindexes)
            latest = participants[-1] if participants else 0
            peak = max(participants) if participants else 0
        else:
            n_ceremonies = 0
            latest = 0
            peak = 0

        community_stats.append({
            'name': name, 'cid': cid,
            'ceremonies': n_ceremonies,
            'latest_participants': latest,
            'peak_participants': peak
        })

    stats['communities'] = community_stats

    # 4. Ceremony participation summary
    for doc in rewards_docs:
        cid = doc['cid']
        name = COMMUNITIES.get(cid, cid)
        data = doc['data']
        all_p = [v['numParticipants'] for v in data.values()]
        if all_p:
            stats[f'ceremony_{name}_total_ceremonies'] = len(all_p)
            stats[f'ceremony_{name}_mean_participants'] = round(sum(all_p)/len(all_p), 1)

    # 5. Governance date range
    if proposals:
        first_ts = min(p['timestamp'] for p in proposals.values() if p['timestamp'])
        last_ts = max(p['timestamp'] for p in proposals.values() if p['timestamp'])
        from datetime import datetime, timezone
        stats['governance_start'] = datetime.fromtimestamp(first_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        stats['governance_end'] = datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')

    # 6. Treasury events
    granted = pindex.events.count_documents({
        'section': 'encointerTreasuries',
        'method': {'$in': ['GrantedSwapAssetOption', 'GrantedSwapNativeOption']}
    })
    spent = pindex.events.count_documents({
        'section': 'encointerTreasuries',
        'method': {'$in': ['SpentAsset', 'SpentNative']}
    })
    stats['swap_options_granted'] = granted
    stats['swap_options_exercised'] = spent

    # Print and save
    print(json.dumps(stats, indent=2))
    with open(os.path.join(FIGURES_DIR, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\nStats saved to figures/stats.json")

    client.close()

if __name__ == '__main__':
    main()
