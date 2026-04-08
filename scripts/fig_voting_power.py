#!/usr/bin/env python3
"""Fig 5: Voting power distribution — voters vs non-voters double-bar plot.

For each proposal, computes the electorate (accounts with eligible voting
power) and identifies which electorate members voted. Participation rate
per power level is averaged across all proposals.

The pallet's voting_cindexes function defines the eligible window as
[cs - R + proposal_lifetime_cycles, cs - 2], where cs is the proposal's
start_cindex. With R=5 and proposal_lifetime_cycles=1: max power = 3.
Ceremony cs-1 is deliberately excluded by the pallet (saturating_sub(2)).
"""
from common import *
from collections import defaultdict, Counter
import numpy as np


def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']
    R = 5  # reputation lifetime
    MAX_POWER = R - 2  # = 3

    GEOHASH_CID = {
        'u0qj9': 'u0qj944rhWE', 's1vrq': 's1vrqQL2SD', 'kygch': 'kygch5kVGq7'
    }

    # 1. Build (cid, cindex) -> set(accounts) from Issued events
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
        # Match backend: adjust for REGISTERING phase
        if r.get('phase') == 'REGISTERING':
            ci -= 1
        cid_ci_accts[r['cid']][ci].add(r['account'])

    # 2. Get proposals with startCindex and cid
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'ProposalSubmitted'
    }))
    proposals = {}
    for s in submitted:
        pid = s['data']['proposalId']
        action = s['data'].get('proposalAction', {})
        aval = list(action.values())[0] if isinstance(action, dict) else None
        cid = None
        if isinstance(aval, list) and aval and isinstance(aval[0], dict):
            gh = aval[0].get('geohash', '')
            cid = GEOHASH_CID.get(gh)
        blk = pindex.blocks.find_one({'height': s['blockNumber']})
        cs = blk['cindex'] if blk else None
        proposals[pid] = {'cid': cid, 'cs': cs}

    # 3. Get voter addresses per proposal via extrinsic matching
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy', 'method': 'VotePlaced'
    }))
    ext_ids = [v.get('extrinsicId') for v in vote_events if v.get('extrinsicId')]
    extrinsics = {e['_id']: e for e in pindex.extrinsics.find({'_id': {'$in': ext_ids}})}

    voters_per_proposal = defaultdict(set)
    for v in vote_events:
        ext = extrinsics.get(v.get('extrinsicId'))
        if not ext:
            continue
        pid = v['data'].get('proposalId', v['data'].get(0))
        signer = ext.get('signer', {})
        addr = signer.get('Id', '') if isinstance(signer, dict) else str(signer)
        if pid and addr:
            voters_per_proposal[pid].add(addr)

    # 4. Per proposal: compute electorate power, split voters/non-voters.
    #    Pallet window: [cs - R + proposal_lifetime_cycles, cs - 2].
    #    With R=5, proposal_lifetime_cycles=1: [cs-4, cs-2], max power = 3.
    levels = list(range(1, MAX_POWER + 1))
    per_proposal_data = []

    for pid, pinfo in proposals.items():
        cid = pinfo['cid']
        cs = pinfo['cs']
        if not cid or not cs:
            continue

        ca = cid_ci_accts[cid]

        # Pallet window: cs-2 is the upper bound (saturating_sub(2))
        window_start = cs - R + 1
        window_end = cs - 2

        acct_power = Counter()
        for ci in range(window_start, window_end + 1):
            for acct in ca.get(ci, set()):
                acct_power[acct] += 1
        for acct in acct_power:
            acct_power[acct] = min(acct_power[acct], MAX_POWER)

        if not acct_power:
            continue

        voted = voters_per_proposal.get(pid, set())

        counts = {}
        for p in levels:
            v = sum(1 for a, pw in acct_power.items() if pw == p and a in voted)
            nv = sum(1 for a, pw in acct_power.items() if pw == p and a not in voted)
            counts[p] = {'voters': v, 'nonvoters': nv}
        per_proposal_data.append(counts)

    n_proposals = len(per_proposal_data)
    print(f"Proposals with computable electorate: {n_proposals}")

    # Average counts across proposals
    mean_voters = []
    mean_nonvoters = []
    participation_rates = []
    for p in levels:
        v_vals = [d[p]['voters'] for d in per_proposal_data]
        nv_vals = [d[p]['nonvoters'] for d in per_proposal_data]
        mv = np.mean(v_vals)
        mnv = np.mean(nv_vals)
        mean_voters.append(mv)
        mean_nonvoters.append(mnv)
        # Participation: mean of per-proposal ratios (equal weight per proposal)
        rates = []
        for d in per_proposal_data:
            eligible = d[p]['voters'] + d[p]['nonvoters']
            if eligible > 0:
                rates.append(d[p]['voters'] / eligible)
        rate = np.mean(rates) * 100 if rates else 0
        participation_rates.append(rate)
        print(f"  Power {p}: mean voters {mv:.1f}, mean non-voters {mnv:.1f}, "
              f"participation rate {rate:.1f}%")

    # 5. Compute Gaussian fit for voter power distribution
    total_mean_voters = sum(mean_voters)
    weights = [mv / total_mean_voters for mv in mean_voters]
    mu = sum(p * w for p, w in zip(levels, weights))
    var = sum((p - mu) ** 2 * w for p, w in zip(levels, weights))
    sigma = np.sqrt(var)
    print(f"\nVoter power: mean={mu:.2f}, std={sigma:.2f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(FIG_WIDTH_DOUBLE, 2.5))

    x = np.arange(len(levels))
    width = 0.5

    # Left: voter voting power distribution with Gaussian fit
    ax1.bar(x, mean_voters, width, color='#4878a8',
            edgecolor='black', linewidth=0.5)

    # Gaussian curve scaled to match bar heights
    x_fine = np.linspace(-0.5, len(levels) - 0.5, 200)
    gauss = np.exp(-0.5 * ((x_fine + levels[0] - mu) / sigma) ** 2)
    gauss = gauss / gauss.max() * max(mean_voters)
    ax1.plot(x_fine, gauss, 'r--', linewidth=1.0,
             label=f'$\\mu={mu:.2f},\\ \\sigma={sigma:.2f}$')

    ax1.set_xlabel('Voting Power')
    ax1.set_ylabel('Mean Voters per Proposal')
    ax1.set_xticks(x)
    ax1.set_xticklabels(levels)
    ax1.set_ylim(0, max(mean_voters) * 1.35)
    ax1.legend(fontsize=6)
    ax1.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)

    # Right: participation rate vs voting power
    ax2.bar(x, participation_rates, width, color='#4878a8',
            edgecolor='black', linewidth=0.5)
    ax2.set_xlabel('Voting Power')
    ax2.set_ylabel('Participation Rate (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(levels)
    ax2.set_ylim(0, max(participation_rates) * 1.25)
    ax2.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)

    fig.tight_layout(w_pad=2.0)

    savefig(fig, 'fig-voting-power.pdf')
    client.close()


if __name__ == '__main__':
    main()
