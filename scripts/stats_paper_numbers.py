#!/usr/bin/env python3
"""Compute all paper-specific statistics not covered by other scripts.

Outputs:
- Table 1: per-community ceremonies, peak/latest reputables, proposals
- Unique ceremony participants (all-time, active since governance, voted)
- Swap option beneficiary stats
- Rejected proposal analysis (votes vs zero-turnout)
- Proposals per community
"""
from common import *
from collections import defaultdict, Counter
from datetime import datetime, timezone

R = 5  # reputation lifetime in ceremonies

def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    cache_db = client['encointer-kusama-accounting-backend-cache']

    GEOHASH_CID = {
        'u0qj9': 'u0qj944rhWE', 's1vrq': 's1vrqQL2SD', 'kygch': 'kygch5kVGq7'
    }

    # ── 1. Build (cid, cindex) -> set(accounts) from Issued events ──
    pipeline = [
        {'$match': {'section': 'encointerBalances', 'method': 'Issued'}},
        {'$lookup': {
            'from': 'blocks', 'localField': 'blockNumber',
            'foreignField': 'height', 'as': 'block'
        }},
        {'$unwind': '$block'},
        {'$project': {
            'cid': {'$arrayElemAt': ['$data', 0]},
            'account': {'$arrayElemAt': ['$data', 1]},
            'cindex': '$block.cindex',
            'phase': '$block.phase'
        }}
    ]
    issueds = list(pindex.events.aggregate(pipeline, allowDiskUse=True))

    cid_ci_accts = defaultdict(lambda: defaultdict(set))
    for r in issueds:
        ci = r.get('cindex')
        if ci is None:
            continue
        if r.get('phase') == 'REGISTERING':
            ci -= 1
        cid_ci_accts[r['cid']][ci].add(r['account'])

    # ── 2. Reputables per community (rolling window of R ceremonies) ──
    print("=== Table 1: Community deployment summary ===")
    rewards_docs = list(cache_db['rewards_data'].find())

    for cid, name in sorted(COMMUNITIES.items(), key=lambda x: x[1]):
        rd = next((d for d in rewards_docs if d['cid'] == cid), None)
        if not rd:
            continue
        cindexes = sorted(int(k) for k in rd['data'].keys())
        n_ceremonies = len(cindexes)

        ca = cid_ci_accts[cid]

        # Peak reputables: max over all ceremonies of unique accounts in [ci-R, ci]
        # Matches backend logic: minCindex = max(1, cindex - reputationLifetime)
        peak_rep = 0
        latest_rep = 0
        for ci in cindexes:
            window = range(max(1, ci - R), ci + 1)
            reputables = set()
            for wci in window:
                reputables |= ca.get(wci, set())
            if len(reputables) > peak_rep:
                peak_rep = len(reputables)
            latest_rep = len(reputables)

        print(f"  {name}: {n_ceremonies} ceremonies, peak reputables {peak_rep}, "
              f"latest reputables {latest_rep}")

    # ── 3. Proposals: build map with community, state, votes ──
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted'
    }))
    state_updates = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalStateUpdated'
    }))

    proposals = {}
    for s in submitted:
        pid = s['data']['proposalId']
        action = s['data'].get('proposalAction', {})
        atype = list(action.keys())[0] if isinstance(action, dict) else str(action)
        aval = list(action.values())[0] if isinstance(action, dict) else None

        cid = None
        if isinstance(aval, list) and aval and isinstance(aval[0], dict):
            gh = aval[0].get('geohash', '')
            cid = GEOHASH_CID.get(gh)

        proposals[pid] = {
            'action_type': atype, 'state': 'Ongoing',
            'cid': cid, 'timestamp': s.get('timestamp', 0)
        }

    for su in state_updates:
        pid = su['data']['proposalId']
        state = su['data']['proposalState']
        if pid in proposals:
            if isinstance(state, str):
                proposals[pid]['state'] = state
            elif isinstance(state, dict):
                proposals[pid]['state'] = list(state.keys())[0]

    # Proposals per community
    print("\n=== Proposals per community ===")
    comm_proposals = defaultdict(int)
    for p in proposals.values():
        cname = COMMUNITIES.get(p['cid'], 'Global/Unknown') if p['cid'] else 'Global/Unknown'
        comm_proposals[cname] += 1
    for cname in sorted(comm_proposals):
        print(f"  {cname}: {comm_proposals[cname]}")

    # ── 4. Vote analysis per proposal ──
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced'
    }))

    ext_ids = [v.get('extrinsicId') for v in vote_events if v.get('extrinsicId')]
    extrinsics = {e['_id']: e for e in pindex.extrinsics.find({'_id': {'$in': ext_ids}})}

    votes_per_proposal = defaultdict(list)
    all_voter_addresses = set()
    for v in vote_events:
        ext = extrinsics.get(v.get('extrinsicId'))
        if not ext:
            continue
        data = v.get('data', {})
        if isinstance(data, dict):
            pid = data.get('proposalId')
            vote_dir = data.get('vote', '')
        elif isinstance(data, list):
            pid = data[0] if data else None
            raw = data[1] if len(data) > 1 else None
            vote_dir = 'Aye' if raw == 'Aye' or (isinstance(raw, dict) and 'aye' in raw) else 'Nay'
        else:
            continue
        signer = ext.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if pid and addr:
            votes_per_proposal[pid].append({'vote': vote_dir, 'voter': addr})
            all_voter_addresses.add(addr)

    # Rejected proposal analysis
    print("\n=== Rejected proposal analysis ===")
    rejected = {pid: p for pid, p in proposals.items() if p['state'] == 'Rejected'}
    zero_turnout_rejected = 0
    voted_rejected = 0
    for pid, p in sorted(rejected.items()):
        n_votes = len(votes_per_proposal.get(pid, []))
        aye = sum(1 for v in votes_per_proposal.get(pid, []) if v['vote'] == 'Aye')
        nay = sum(1 for v in votes_per_proposal.get(pid, []) if v['vote'] == 'Nay')
        if n_votes == 0:
            zero_turnout_rejected += 1
        else:
            voted_rejected += 1
        print(f"  Proposal {pid}: {p['action_type']} ({COMMUNITIES.get(p['cid'], '?')}) "
              f"— {n_votes} votes (aye={aye}, nay={nay})")
    print(f"  Zero-turnout rejected: {zero_turnout_rejected}")
    print(f"  Rejected with votes: {voted_rejected}")

    # Proposals with at least one vote
    proposals_with_votes = sum(1 for pid in proposals if len(votes_per_proposal.get(pid, [])) > 0)
    print(f"\n=== Vote summary ===")
    print(f"  Proposals with at least one vote: {proposals_with_votes}")
    print(f"  Proposals with zero votes: {len(proposals) - proposals_with_votes}")

    # ── 5. Unique ceremony participants ──
    # Governance deployment: Dec 2024, approximate cindex
    # From fig_ceremony_participation: cindex 98 = 2024-12-02
    GOV_START_CINDEX = 98

    all_accounts_ever = set()
    active_since_gov = set()
    for cid in COMMUNITIES:
        ca = cid_ci_accts[cid]
        for ci, accts in ca.items():
            all_accounts_ever |= accts
            if ci >= GOV_START_CINDEX:
                active_since_gov |= accts

    voted_accounts = all_voter_addresses & active_since_gov
    print(f"\n=== Unique participants ===")
    print(f"  All-time ceremony participants (all communities): {len(all_accounts_ever)}")
    print(f"  Active since governance deployment (cindex>={GOV_START_CINDEX}): {len(active_since_gov)}")
    print(f"  Of those, cast at least one vote: {len(voted_accounts)} "
          f"({len(voted_accounts)/len(active_since_gov)*100:.1f}%)")

    # ── 6. Swap option beneficiary stats ──
    grant_events = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'GrantedSwapAssetOption'
    }))
    grant_block_nums = list(set(e['blockNumber'] for e in grant_events))

    block_events = list(pindex.events.find({
        'blockNumber': {'$in': grant_block_nums},
        'method': {'$in': ['GrantedSwapAssetOption', 'ProposalEnacted']}
    }).sort('_id', 1))

    proposal_beneficiary = {}
    pending_beneficiary = None
    for ev in block_events:
        if ev['method'] == 'GrantedSwapAssetOption':
            pending_beneficiary = ev['data'].get('who')
        elif ev['method'] == 'ProposalEnacted' and pending_beneficiary:
            pid = ev['data'].get('proposalId')
            if pid is not None:
                proposal_beneficiary[pid] = pending_beneficiary
            pending_beneficiary = None

    unique_beneficiaries = set(proposal_beneficiary.values())

    # Exercise transactions
    exercises = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True
    }))
    exercising_addresses = set()
    for ex in exercises:
        signer = ex.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if addr:
            exercising_addresses.add(addr)

    beneficiaries_exercised = unique_beneficiaries & exercising_addresses

    print(f"\n=== Swap option beneficiaries ===")
    print(f"  Total granted swap options: {len(grant_events)}")
    print(f"  Unique beneficiaries: {len(unique_beneficiaries)}")
    print(f"  Beneficiaries who exercised: {len(beneficiaries_exercised)} "
          f"({len(beneficiaries_exercised)/len(unique_beneficiaries)*100:.0f}%)")
    print(f"  Total exercise transactions: {len(exercises)}")

    client.close()

if __name__ == '__main__':
    main()
