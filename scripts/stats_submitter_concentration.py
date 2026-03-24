#!/usr/bin/env python3
"""Analyze proposal submitter and vote submitter concentration."""
from common import *
from collections import Counter

def main():
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    # --- Proposal submitters ---
    submitted = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'ProposalSubmitted'
    }))
    ext_ids = [s['extrinsicId'] for s in submitted]
    extrinsics = {e['_id']: e for e in pindex.extrinsics.find({'_id': {'$in': ext_ids}})}

    signers = []
    for s in submitted:
        ext = extrinsics.get(s['extrinsicId'])
        if ext:
            signers.append(ext.get('signer', {}).get('Id', 'unknown'))

    signer_counts = Counter(signers)
    top2 = sum(c for _, c in signer_counts.most_common(2))

    print(f"Total proposals: {len(submitted)}")
    print(f"Unique proposal submitters: {len(signer_counts)}")
    print(f"Top 2 submitters: {top2} proposals ({top2/len(submitted)*100:.0f}%)")
    print(f"\nProposals per submitter:")
    for addr, count in signer_counts.most_common():
        print(f"  {addr[:12]}...: {count} ({count/len(submitted)*100:.0f}%)")

    # --- Vote submitters ---
    vote_events = list(pindex.events.find({
        'section': 'encointerDemocracy',
        'method': 'VotePlaced'
    }))
    vote_ext_ids = [v['extrinsicId'] for v in vote_events]
    vote_exts = {e['_id']: e for e in pindex.extrinsics.find({'_id': {'$in': vote_ext_ids}})}

    vote_signers = []
    for v in vote_events:
        ext = vote_exts.get(v['extrinsicId'])
        if ext:
            vote_signers.append(ext.get('signer', {}).get('Id', 'unknown'))

    vote_signer_counts = Counter(vote_signers)
    print(f"\nTotal vote transactions: {len(vote_events)}")
    print(f"Unique vote submitters: {len(vote_signer_counts)}")
    print(f"\nTop 5 vote submitters:")
    for addr, count in vote_signer_counts.most_common(5):
        print(f"  {addr[:12]}...: {count} ({count/len(vote_events)*100:.0f}%)")

    client.close()

if __name__ == '__main__':
    main()
