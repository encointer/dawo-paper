#!/usr/bin/env python3
"""Analyze whether swap option Aye voters are clients of the beneficiary.

For each enacted swap option proposal, categorize Aye voters into those who
previously sent CC to the beneficiary address and those who have not.
"""
from common import *
from collections import defaultdict


def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    cache_db = client['encointer-kusama-accounting-backend-cache']

    # 1. Get enacted swap option proposals from governance cache
    cached_proposals = list(cache_db['general_cache'].find({
        'cacheIdentifier': 'governance-proposal'
    }))

    swap_proposals = []
    for doc in cached_proposals:
        p = doc.get('data', doc)
        atype = p.get('actionType', '')
        state = p.get('state', '')
        if state != 'Enacted':
            continue
        if atype not in ('issueSwapAssetOption', 'issueSwapNativeOption'):
            continue
        swap_proposals.append(p)

    swap_proposals.sort(key=lambda p: p['id'])
    proposal_ids = {p['id'] for p in swap_proposals}

    # 2. Get beneficiary addresses from GrantedSwapAssetOption events.
    #    Each grant is immediately followed by its ProposalEnacted event in the
    #    same block, so we pair them by reading events in _id order per block.
    grant_block_nums = list(set(
        e['blockNumber'] for e in pindex['events'].find(
            {'section': 'encointerTreasuries', 'method': 'GrantedSwapAssetOption'},
            {'blockNumber': 1}
        )
    ))

    block_events = list(pindex['events'].find({
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

    # 3. Get all VotePlaced events and resolve voter addresses
    vote_placed = list(pindex['events'].find({
        'section': 'encointerDemocracy',
        'method': 'VotePlaced'
    }))

    ext_ids = [v.get('extrinsicId') for v in vote_placed if v.get('extrinsicId')]
    extrinsics = list(pindex['extrinsics'].find({'_id': {'$in': ext_ids}}))
    ext_map = {e['_id']: e for e in extrinsics}

    # Build per-proposal Aye voters with timestamps
    aye_voters_by_proposal = defaultdict(list)
    for v in vote_placed:
        ext = ext_map.get(v.get('extrinsicId'))
        if not ext:
            continue
        data = v.get('data', {})
        if isinstance(data, dict):
            pid = data.get('proposalId')
            vote_dir = data.get('vote', '')
        elif isinstance(data, list):
            pid = data[0] if data else None
            raw_vote = data[1] if len(data) > 1 else None
            vote_dir = 'Aye' if raw_vote == 'Aye' or (isinstance(raw_vote, dict) and 'aye' in raw_vote) else 'Nay'
        else:
            continue

        voter = (ext.get('signer', {}) or {}).get('Id')
        if not pid or not voter or vote_dir != 'Aye':
            continue
        if pid not in proposal_ids:
            continue
        aye_voters_by_proposal[pid].append({
            'voter': voter,
            'timestamp': v.get('timestamp', 0)
        })

    # 4. For each swap proposal, check which Aye voters are clients
    print(f"{'ID':>4}  {'Community':<16} {'Aye Voters':>10} "
          f"{'Clients':>8} {'Non-Clients':>11} {'Client %':>9}")
    print("-" * 65)

    community_stats = defaultdict(lambda: {'aye': 0, 'clients': 0, 'non': 0, 'proposals': 0})

    for p in swap_proposals:
        pid = p['id']
        beneficiary = proposal_beneficiary.get(pid)
        aye_voters = aye_voters_by_proposal.get(pid, [])
        community = p.get('communityName', p.get('communityId', '?'))

        if not beneficiary or not aye_voters:
            n, c, nc = len(aye_voters), 0, len(aye_voters)
        else:
            # Query all CC transfers TO beneficiary
            transfers = list(pindex['events'].find({
                'section': 'encointerBalances',
                'method': 'Transferred',
                'data.2': beneficiary
            }))

            # Build sender -> list of timestamps
            sender_timestamps = defaultdict(list)
            for t in transfers:
                sender = t['data'][1]
                sender_timestamps[sender].append(t.get('timestamp', 0))

            c = 0
            nc = 0
            for av in aye_voters:
                prior = any(ts < av['timestamp'] for ts in sender_timestamps.get(av['voter'], []))
                if prior:
                    c += 1
                else:
                    nc += 1
            n = len(aye_voters)

        pct = f"{c / n * 100:.1f}%" if n > 0 else "-"
        print(f"{pid:>4}  {community:<16} {n:>10} {c:>8} {nc:>11} {pct:>9}")
        community_stats[community]['aye'] += n
        community_stats[community]['clients'] += c
        community_stats[community]['non'] += nc
        community_stats[community]['proposals'] += 1

    # Per-community summary
    print("-" * 65)
    total_aye = 0
    total_clients = 0
    total_non = 0
    for comm in sorted(community_stats):
        s = community_stats[comm]
        pct = f"{s['clients'] / s['aye'] * 100:.1f}%" if s['aye'] > 0 else "-"
        print(f"{'':>4}  {comm:<16} {s['aye']:>10} {s['clients']:>8} "
              f"{s['non']:>11} {pct:>9}  ({s['proposals']} proposals)")
        total_aye += s['aye']
        total_clients += s['clients']
        total_non += s['non']

    print("-" * 65)
    total_pct = f"{total_clients / total_aye * 100:.1f}%" if total_aye > 0 else "-"
    print(f"{'':>4}  {'TOTAL':<16} {total_aye:>10} "
          f"{total_clients:>8} {total_non:>11} {total_pct:>9}  "
          f"({sum(s['proposals'] for s in community_stats.values())} proposals)")

    client.close()


if __name__ == '__main__':
    main()
