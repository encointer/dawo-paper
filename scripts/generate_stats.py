#!/usr/bin/env python3
"""Generate summary statistics for the paper (Section 5 tables and inline numbers).

Filters all queries to a paper data freeze date (CUTOFF_DATE) so the
numbers stay reproducible against a live, advancing database.
"""
from common import *
from collections import defaultdict, Counter
from datetime import datetime, timezone
import json

# Paper data freeze date (inclusive end-of-day UTC).
CUTOFF_DATE = '2026-03-27'
CUTOFF_TS_MS = int(datetime(2026, 3, 27, 23, 59, 59,
                            tzinfo=timezone.utc).timestamp() * 1000)
GOV_START_TS_MS = int(datetime(2024, 12, 2, 0, 0, 0,
                               tzinfo=timezone.utc).timestamp() * 1000)
R = 5  # reputation lifetime in cycles


def get_cutoff_cindex(pindex, ts_ms):
    """Return the highest cindex among blocks at or before ts_ms."""
    res = list(pindex.blocks.aggregate([
        {'$match': {'timestamp': {'$lte': ts_ms}}},
        {'$group': {'_id': None, 'max_cindex': {'$max': '$cindex'}}}
    ]))
    return res[0]['max_cindex'] if res else None


def build_cid_ci_accts(pindex, cutoff_ts_ms, cutoff_cindex):
    """For each (community, cindex), the set of accounts that received a
    reward. Mirrors fig_voting_power.py's REGISTERING-phase adjustment."""
    pipeline = [
        {'$match': {'section': 'encointerBalances', 'method': 'Issued',
                    'timestamp': {'$lte': cutoff_ts_ms}}},
        {'$lookup': {'from': 'blocks', 'localField': 'blockNumber',
                     'foreignField': 'height', 'as': 'block'}},
        {'$unwind': '$block'},
        {'$project': {'cid': {'$arrayElemAt': ['$data', 0]},
                      'account': {'$arrayElemAt': ['$data', 1]},
                      'cindex': '$block.cindex',
                      'phase': '$block.phase',
                      'ts': '$timestamp'}}
    ]
    rows = list(pindex.events.aggregate(pipeline, allowDiskUse=True))
    cid_ci_accts = defaultdict(lambda: defaultdict(set))
    acct_first_ts = {}
    for r in rows:
        ci = r.get('cindex')
        if ci is None:
            continue
        if r.get('phase') == 'REGISTERING':
            ci -= 1
        if ci > cutoff_cindex:
            continue
        cid_ci_accts[r['cid']][ci].add(r['account'])
        ts = r.get('ts', 0)
        if r['account'] not in acct_first_ts or ts < acct_first_ts[r['account']]:
            acct_first_ts[r['account']] = ts
    return cid_ci_accts, acct_first_ts


def compute_reputables(cid_ci_accts):
    """Peak and latest reputables per community.
    Reputable = unique account with at least one attendance in the
    inclusive window [c - R, c]. Matches accounting-backend
    getCumulativeRewardsData (data.js)."""
    out = {}
    for cid, ci_accts in cid_ci_accts.items():
        if not ci_accts:
            continue
        ci_sorted = sorted(ci_accts.keys())
        ci_min, ci_max = ci_sorted[0], ci_sorted[-1]
        peak = 0
        for c in range(ci_min, ci_max + 1):
            w = set()
            for cc in range(max(1, c - R), c + 1):
                w |= ci_accts.get(cc, set())
            if len(w) > peak:
                peak = len(w)
        latest = set()
        for cc in range(max(1, ci_max - R), ci_max + 1):
            latest |= ci_accts.get(cc, set())
        out[cid] = {'peak_reputables': peak,
                    'latest_reputables': len(latest)}
    return out


def compute_voter_breadth(pindex, cutoff_ts_ms, acct_first_ts):
    """Counts of: ceremony attendees ever, attendees with any attendance
    since governance deployment, and distinct vote signers."""
    ever = set(acct_first_ts.keys())
    # Active since governance start: any attendance with ts >= GOV_START_TS_MS
    # Recompute from raw events to capture all attendances (not just first).
    issued = pindex.events.find({
        'section': 'encointerBalances', 'method': 'Issued',
        'timestamp': {'$gte': GOV_START_TS_MS, '$lte': cutoff_ts_ms}
    })
    active = set()
    for e in issued:
        data = e.get('data')
        if isinstance(data, list) and len(data) > 1:
            active.add(data[1])

    votes = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced',
        'timestamp': {'$lte': cutoff_ts_ms}
    }))
    ext_ids = [v['extrinsicId'] for v in votes if v.get('extrinsicId')]
    exts = {e['_id']: e for e in
            pindex.extrinsics.find({'_id': {'$in': ext_ids}})}
    voters = set()
    for v in votes:
        ext = exts.get(v.get('extrinsicId'))
        if not ext:
            continue
        signer = ext.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if addr:
            voters.add(addr)
    return {
        'ceremony_attendees_ever': len(ever),
        'ceremony_attendees_since_gov_start': len(active),
        'distinct_voters': len(voters),
        'voter_share_of_active_pct':
            round(100 * len(voters) / len(active), 1) if active else 0,
    }


def compute_proposal_metrics(pindex, cutoff_ts_ms, cid_ci_accts):
    """Submitter concentration, electorate-computable count,
    voted-on count, mean approval rate, mean turnout,
    voting-power statistics among voters, participation rate by power."""
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted',
        'timestamp': {'$lte': cutoff_ts_ms}
    }))
    ext_ids = [s['extrinsicId'] for s in submitted if s.get('extrinsicId')]
    exts = {e['_id']: e for e in
            pindex.extrinsics.find({'_id': {'$in': ext_ids}})}

    signer_counter = Counter()
    for s in submitted:
        ext = exts.get(s.get('extrinsicId'))
        if ext:
            signer = ext.get('signer', {})
            addr = signer.get('Id', '') if isinstance(signer, dict) \
                else str(signer)
            if addr:
                signer_counter[addr] += 1
    distinct_submitters = len(signer_counter)
    top2 = sum(c for _, c in signer_counter.most_common(2))
    total = sum(signer_counter.values())
    top2_share = round(100 * top2 / total, 1) if total else 0

    GEOHASH_CID = {
        'u0qj9': 'u0qj944rhWE', 's1vrq': 's1vrqQL2SD',
        'kygch': 'kygch5kVGq7', 'dpcmj': 'dpcmj33LUs9',
    }

    # Voting window per pallet: [cs - R + 1, cs - 2] (max power = R - 2 = 3).
    MAX_POWER = R - 2

    # Map proposal -> set of voter addresses (via extrinsic signers).
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced',
        'timestamp': {'$lte': cutoff_ts_ms}
    }))
    vote_ext_ids = [v['extrinsicId'] for v in vote_events if v.get('extrinsicId')]
    vote_exts = {e['_id']: e for e in
                 pindex.extrinsics.find({'_id': {'$in': vote_ext_ids}})}
    voters_per_proposal = defaultdict(set)
    aye_per_p = defaultdict(int)
    nay_per_p = defaultdict(int)
    for v in vote_events:
        pid = v['data'].get('proposalId')
        if pid is None:
            continue
        if v['data'].get('vote') == 'Aye':
            aye_per_p[pid] += 1
        elif v['data'].get('vote') == 'Nay':
            nay_per_p[pid] += 1
        ext = vote_exts.get(v.get('extrinsicId'))
        if not ext:
            continue
        signer = ext.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if addr:
            voters_per_proposal[pid].add(addr)

    # Per-proposal breakdown (mirrors fig_voting_power.py).
    per_proposal = []  # list of {p: {'voters': v, 'nonvoters': nv}}
    turnouts = []

    for s in submitted:
        action = s['data'].get('proposalAction', {})
        aval = list(action.values())[0] if isinstance(action, dict) else None
        cid = None
        if isinstance(aval, list) and aval and isinstance(aval[0], dict):
            gh = aval[0].get('geohash', '')
            cid = GEOHASH_CID.get(gh)
        blk = pindex.blocks.find_one({'height': s['blockNumber']})
        cs = blk['cindex'] if blk else None
        if not cid or cs is None:
            continue
        ca = cid_ci_accts.get(cid, {})

        acct_power = Counter()
        for c in range(cs - R + 1, cs - 2 + 1):
            for acct in ca.get(c, set()):
                acct_power[acct] += 1
        for a in acct_power:
            acct_power[a] = min(acct_power[a], MAX_POWER)
        if not acct_power:
            continue

        pid = s['data']['proposalId']
        voted = voters_per_proposal.get(pid, set())
        counts = {}
        for p in range(1, MAX_POWER + 1):
            v_at_p = sum(1 for a, pw in acct_power.items()
                         if pw == p and a in voted)
            elig_at_p = sum(1 for a, pw in acct_power.items() if pw == p)
            counts[p] = {'voters': v_at_p, 'nonvoters': elig_at_p - v_at_p}
        per_proposal.append(counts)

        electorate_power = sum(acct_power.values())
        voter_power_sum = sum(acct_power[a] for a in voted if a in acct_power)
        # Mean turnout reported in the paper is restricted to proposals that
        # received >=1 vote (§5.3 context).
        if electorate_power > 0 and voter_power_sum > 0:
            turnouts.append(voter_power_sum / electorate_power)

    n_with_electorate = len(per_proposal)

    rates = []
    proposals_with_votes = set(aye_per_p) | set(nay_per_p)
    for pid in proposals_with_votes:
        t = aye_per_p[pid] + nay_per_p[pid]
        if t > 0:
            rates.append(aye_per_p[pid] / t)
    mean_approval_pct = round(100 * sum(rates) / len(rates), 1) if rates else 0

    # Mean voters and participation rate per power, averaged per-proposal.
    mean_voters_by_p = {}
    part_rate_by_p = {}
    for p in range(1, MAX_POWER + 1):
        v_vals = [d[p]['voters'] for d in per_proposal]
        mean_voters_by_p[p] = sum(v_vals) / len(v_vals) if v_vals else 0
        per_proposal_rates = []
        for d in per_proposal:
            elig = d[p]['voters'] + d[p]['nonvoters']
            if elig > 0:
                per_proposal_rates.append(d[p]['voters'] / elig)
        part_rate_by_p[p] = round(
            100 * sum(per_proposal_rates) / len(per_proposal_rates), 1) \
            if per_proposal_rates else 0

    # Voting power mean/std among voters (Gaussian fit to mean_voters_by_p).
    total_voters_mean = sum(mean_voters_by_p.values())
    weights = {p: mean_voters_by_p[p] / total_voters_mean
               for p in range(1, MAX_POWER + 1)} if total_voters_mean else {}
    mu = sum(p * w for p, w in weights.items())
    var = sum((p - mu) ** 2 * w for p, w in weights.items())
    sigma = var ** 0.5

    mean_turnout_pct = round(
        100 * sum(turnouts) / len(turnouts), 1) if turnouts else 0

    return {
        'distinct_submitters': distinct_submitters,
        'top_2_submitter_share_pct': top2_share,
        'n_proposals_with_electorate': n_with_electorate,
        'n_proposals_with_votes': len(proposals_with_votes),
        'mean_approval_rate_among_voters_pct': mean_approval_pct,
        'mean_turnout_pct': mean_turnout_pct,
        'voting_power_mean_among_voters': round(mu, 2),
        'voting_power_std_among_voters': round(sigma, 2),
        'participation_rate_by_power_pct': part_rate_by_p,
    }


def compute_swap_beneficiary_metrics(pindex, cutoff_ts_ms):
    """Unique swap beneficiaries and how many have exercised."""
    grants = list(pindex.events.find({
        'section': 'encointerTreasuries',
        'method': 'GrantedSwapAssetOption',
        'timestamp': {'$lte': cutoff_ts_ms}
    }))
    beneficiaries = set()
    for g in grants:
        data = g.get('data')
        if isinstance(data, list):
            for d in data:
                if isinstance(d, str) and len(d) > 20:  # looks like an address
                    beneficiaries.add(d)
                    break
        elif isinstance(data, dict):
            b = data.get('beneficiary') or data.get('who')
            if b:
                beneficiaries.add(b)
    exercises = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True,
        'timestamp': {'$lte': cutoff_ts_ms}
    }))
    exercising_signers = set()
    for ex in exercises:
        signer = ex.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if addr:
            exercising_signers.add(addr)
    exercised_by_beneficiary = beneficiaries & exercising_signers
    return {
        'unique_swap_beneficiaries': len(beneficiaries),
        'beneficiaries_with_exercise': len(exercised_by_beneficiary),
        'beneficiary_exercise_share_pct':
            round(100 * len(exercised_by_beneficiary) / len(beneficiaries), 1)
            if beneficiaries else 0,
    }


def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    cache_db = client['encointer-kusama-accounting-backend-cache']
    acct_db = client['encointer-kusama-accounting']

    cutoff_cindex = get_cutoff_cindex(pindex, CUTOFF_TS_MS)
    print(f"Cutoff: {CUTOFF_DATE} (cindex <= {cutoff_cindex})")

    stats = {'cutoff_date': CUTOFF_DATE, 'cutoff_cindex': cutoff_cindex}

    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    state_updates = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalStateUpdated',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    votes = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    vote_failed = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VoteFailed',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))

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

    type_counts = defaultdict(int)
    state_counts = defaultdict(int)
    for p in proposals.values():
        type_counts[p['action_type']] += 1
        state_counts[p['state']] += 1

    stats['total_proposals'] = len(proposals)
    stats['proposals_by_type'] = dict(sorted(type_counts.items(),
                                             key=lambda x: -x[1]))
    stats['proposals_by_state'] = dict(sorted(state_counts.items(),
                                              key=lambda x: -x[1]))

    stats['total_votes_placed'] = len(votes)
    stats['total_votes_failed'] = len(vote_failed)
    stats['aye_votes'] = sum(1 for v in votes if v['data'].get('vote') == 'Aye')
    stats['nay_votes'] = sum(1 for v in votes if v['data'].get('vote') == 'Nay')

    print("Computing reputables (rolling 5-cycle windows)...")
    cid_ci_accts, acct_first_ts = build_cid_ci_accts(
        pindex, CUTOFF_TS_MS, cutoff_cindex)
    reputables = compute_reputables(cid_ci_accts)

    communities = list(acct_db['communities'].find())
    rewards_docs = list(cache_db['rewards_data'].find())
    community_stats = []
    for comm in communities:
        cid = comm.get('cid', '')
        name = comm.get('name', cid)
        rd = next((d for d in rewards_docs if d['cid'] == cid), None)
        if rd:
            cindexes = sorted(int(k) for k in rd['data'].keys()
                              if int(k) <= cutoff_cindex)
            participants = [rd['data'][str(c)]['numParticipants']
                            for c in cindexes]
            n_ceremonies = len(cindexes)
            latest_p = participants[-1] if participants else 0
            peak_p = max(participants) if participants else 0
        else:
            n_ceremonies = 0
            latest_p = 0
            peak_p = 0
        rep = reputables.get(cid, {'peak_reputables': 0,
                                   'latest_reputables': 0})
        community_stats.append({
            'name': name, 'cid': cid,
            'paper_label': COMMUNITIES.get(cid, cid),
            'ceremonies': n_ceremonies,
            'latest_participants': latest_p,
            'peak_participants': peak_p,
            'peak_reputables': rep['peak_reputables'],
            'latest_reputables': rep['latest_reputables'],
        })
    stats['communities'] = community_stats

    for doc in rewards_docs:
        cid = doc['cid']
        name = COMMUNITIES.get(cid, cid)
        cindexes = sorted(int(k) for k in doc['data'].keys()
                          if int(k) <= cutoff_cindex)
        all_p = [doc['data'][str(c)]['numParticipants'] for c in cindexes]
        if all_p:
            stats[f'ceremony_{name}_total_ceremonies'] = len(all_p)
            stats[f'ceremony_{name}_mean_participants'] = round(
                sum(all_p)/len(all_p), 1)

    if proposals:
        first_ts = min(p['timestamp'] for p in proposals.values()
                       if p['timestamp'])
        last_ts = max(p['timestamp'] for p in proposals.values()
                      if p['timestamp'])
        stats['governance_start'] = datetime.fromtimestamp(
            first_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        stats['governance_end'] = datetime.fromtimestamp(
            last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')

    stats['swap_options_granted'] = pindex.events.count_documents({
        'section': 'encointerTreasuries',
        'method': 'GrantedSwapAssetOption',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    })
    stats['swap_options_exercised'] = pindex.extrinsics.count_documents({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True,
        'timestamp': {'$lte': CUTOFF_TS_MS}
    })
    stats['treasury_native_spends'] = pindex.events.count_documents({
        'section': 'encointerTreasuries', 'method': 'SpentNative',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    })

    print("Computing voter breadth...")
    stats.update(compute_voter_breadth(pindex, CUTOFF_TS_MS, acct_first_ts))

    print("Computing proposal metrics...")
    stats.update(compute_proposal_metrics(pindex, CUTOFF_TS_MS, cid_ci_accts))

    print("Computing swap beneficiary metrics...")
    stats.update(compute_swap_beneficiary_metrics(pindex, CUTOFF_TS_MS))

    print(json.dumps(stats, indent=2))
    with open(os.path.join(FIGURES_DIR, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\nStats saved to figures/stats.json")
    client.close()


if __name__ == '__main__':
    main()
