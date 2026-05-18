#!/usr/bin/env python3
"""Analyze whether swap option Aye voters are clients of the beneficiary.

For each swap option proposal that reached Approved or Confirming state by
the paper data cutoff, categorise Aye voters into those who previously sent
community currency to the beneficiary address (clients) and those who did
not. Cutoff matches generate_stats.py.
"""
from common import *
from collections import defaultdict
from datetime import datetime, timezone

CUTOFF_DATE = '2026-03-27'
CUTOFF_TS_MS = int(datetime(2026, 3, 27, 23, 59, 59,
                            tzinfo=timezone.utc).timestamp() * 1000)

GEOHASH_CID = {
    'u0qj9': 'u0qj944rhWE', 's1vrq': 's1vrqQL2SD',
    'kygch': 'kygch5kVGq7', 'dpcmj': 'dpcmj33LUs9',
}
CID_NAME = {v: k for k, v in COMMUNITIES.items()} if False else COMMUNITIES


def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # 1. Identify swap proposals that reached approved/confirming by cutoff.
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    state_updates = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalStateUpdated',
        'timestamp': {'$lte': CUTOFF_TS_MS}
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
        proposals[pid] = {'action_type': atype, 'state': 'Ongoing', 'cid': cid}

    transitions_by_pid = defaultdict(list)
    for su in state_updates:
        pid = su['data']['proposalId']
        state = su['data']['proposalState']
        stname = state if isinstance(state, str) else list(state.keys())[0]
        transitions_by_pid[pid].append((su.get('timestamp', 0), stname))
    for pid, ts_list in transitions_by_pid.items():
        if pid in proposals:
            ts_list.sort()
            proposals[pid]['state'] = ts_list[-1][1]

    swap_pids = {
        pid for pid, p in proposals.items()
        if p['action_type'] == 'IssueSwapAssetOption'
        and p['state'] in ('Approved', 'Confirming')
    }

    # 2. Resolve beneficiary per proposal: GrantedSwapAssetOption events for
    #    Approved proposals; ProposalAction.swapAssetOption[1] for the rest.
    proposal_beneficiary = {}

    grant_block_nums = list(set(
        e['blockNumber'] for e in pindex.events.find(
            {'section': 'encointerTreasuries',
             'method': 'GrantedSwapAssetOption',
             'timestamp': {'$lte': CUTOFF_TS_MS}},
            {'blockNumber': 1}
        )
    ))
    block_events = list(pindex.events.find({
        'blockNumber': {'$in': grant_block_nums},
        'method': {'$in': ['GrantedSwapAssetOption', 'ProposalEnacted']}
    }).sort('_id', 1))
    pending = None
    for ev in block_events:
        if ev['method'] == 'GrantedSwapAssetOption':
            pending = ev['data'].get('who')
        elif ev['method'] == 'ProposalEnacted' and pending is not None:
            pid = ev['data'].get('proposalId')
            if pid is not None:
                proposal_beneficiary[pid] = pending
            pending = None

    # For Confirming proposals not yet enacted, read beneficiary from the
    # ProposalSubmitted payload directly.
    for s in submitted:
        pid = s['data']['proposalId']
        if pid not in swap_pids or pid in proposal_beneficiary:
            continue
        action = s['data'].get('proposalAction', {})
        aval = list(action.values())[0] if isinstance(action, dict) else None
        if isinstance(aval, list) and len(aval) >= 2:
            proposal_beneficiary[pid] = aval[1]

    # 3. Aye voters per swap proposal (votes <= cutoff).
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    ext_ids = [v.get('extrinsicId') for v in vote_events if v.get('extrinsicId')]
    ext_map = {e['_id']: e for e in pindex.extrinsics.find({'_id': {'$in': ext_ids}})}

    aye_voters_by_proposal = defaultdict(list)
    for v in vote_events:
        ext = ext_map.get(v.get('extrinsicId'))
        if not ext:
            continue
        data = v.get('data', {})
        if isinstance(data, dict):
            pid = data.get('proposalId')
            vote_dir = data.get('vote', '')
        elif isinstance(data, list):
            pid = data[0] if data else None
            raw = data[1] if len(data) > 1 else None
            vote_dir = 'Aye' if raw == 'Aye' or (
                isinstance(raw, dict) and 'aye' in raw) else 'Nay'
        else:
            continue
        voter = (ext.get('signer', {}) or {}).get('Id')
        if not pid or not voter or vote_dir != 'Aye':
            continue
        if pid not in swap_pids:
            continue
        aye_voters_by_proposal[pid].append({
            'voter': voter, 'timestamp': v.get('timestamp', 0)
        })

    # 4. Client classification per proposal.
    community_stats = defaultdict(
        lambda: {'aye': 0, 'clients': 0, 'non': 0, 'proposals': 0})

    print(f"Cutoff: {CUTOFF_DATE}  swap proposals (approved+confirming): "
          f"{len(swap_pids)}")
    print(f"{'ID':>4}  {'Community':<16} {'Aye':>5} {'Cli':>5} "
          f"{'Non':>5} {'Cli %':>7}")
    print("-" * 56)
    for pid in sorted(swap_pids):
        cid = proposals[pid].get('cid')
        community = COMMUNITIES.get(cid, cid or '?')
        beneficiary = proposal_beneficiary.get(pid)
        aye_voters = aye_voters_by_proposal.get(pid, [])
        if not beneficiary or not aye_voters:
            n, c, nc = len(aye_voters), 0, len(aye_voters)
        else:
            transfers = list(pindex.events.find({
                'section': 'encointerBalances', 'method': 'Transferred',
                'data.2': beneficiary,
                'timestamp': {'$lte': CUTOFF_TS_MS}
            }))
            sender_ts = defaultdict(list)
            for t in transfers:
                sender_ts[t['data'][1]].append(t.get('timestamp', 0))
            c = nc = 0
            for av in aye_voters:
                prior = any(ts < av['timestamp']
                            for ts in sender_ts.get(av['voter'], []))
                if prior:
                    c += 1
                else:
                    nc += 1
            n = len(aye_voters)
        pct = f"{c/n*100:.1f}%" if n else "-"
        print(f"{pid:>4}  {community:<16} {n:>5} {c:>5} {nc:>5} {pct:>7}")
        community_stats[community]['aye'] += n
        community_stats[community]['clients'] += c
        community_stats[community]['non'] += nc
        community_stats[community]['proposals'] += 1

    print("-" * 56)
    tot_a = tot_c = tot_nc = 0
    for comm in sorted(community_stats):
        s = community_stats[comm]
        pct = f"{s['clients']/s['aye']*100:.1f}%" if s['aye'] else "-"
        print(f"      {comm:<16} {s['aye']:>5} {s['clients']:>5} "
              f"{s['non']:>5} {pct:>7}  ({s['proposals']} proposals)")
        tot_a += s['aye']; tot_c += s['clients']; tot_nc += s['non']
    tot_pct = f"{tot_c/tot_a*100:.1f}%" if tot_a else "-"
    print("-" * 56)
    print(f"      {'TOTAL':<16} {tot_a:>5} {tot_c:>5} {tot_nc:>5} {tot_pct:>7}  "
          f"({sum(s['proposals'] for s in community_stats.values())} proposals)")
    client.close()


if __name__ == '__main__':
    main()
