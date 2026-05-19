#!/usr/bin/env python3
"""Fig: Real USD value distributed through treasury governance proposals.

Pie chart with categories: SpendNative (KSM valued at daily exchange rate),
SwapAsset exercised (USDC). Contextualizes amounts relative to ceremony
reward and local median daily income.
"""
from common import *
from datetime import datetime, timezone
from collections import defaultdict
import json
import os

# KSM prices fetched from CoinGecko (daily close, USD)
PRICES_FILE = os.path.join(os.path.dirname(__file__), 'ksm_prices.json')

# Paper data freeze date (inclusive end-of-day UTC). Matches generate_stats.py.
CUTOFF_TS_MS = int(datetime(2026, 4, 14, 23, 59, 59,
                            tzinfo=timezone.utc).timestamp() * 1000)


def get_ksm_price(date_str, prices):
    """Get KSM price for date, or closest available."""
    if date_str in prices:
        return prices[date_str]
    target = datetime.strptime(date_str, '%Y-%m-%d').timestamp()
    closest = min(prices.keys(),
                  key=lambda x: abs(datetime.strptime(x, '%Y-%m-%d').timestamp() - target))
    return prices[closest]


def main():
    setup_style()
    client = get_client()
    pindex = client['encointer-kusama-pindex']

    with open(PRICES_FILE) as f:
        ksm_prices = json.load(f)

    TREASURY_CID = {
        'HNJDzJEGaBgWRXz7bjERsRidJFQBnj1AZ2Tn3Q9uRGynhwq': 'u0qj944rhWE',
        'E9KVuDLEtBBWSqhCiKn31VPBBLe33CbYJTrnWAbjszwskWH': 'kygch5kVGq7',
        'E2mZ1u2xepTF8nuEQVkrimPVwqtqq1joC56cUwYPftXAEQL': 's1vrqQL2SD',
    }

    # SpendNative events
    spend_native = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'SpentNative',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }).sort('timestamp', 1))

    total_native_usd = 0
    native_by_community = defaultdict(float)
    for sn in spend_native:
        amt_ksm = int(sn['data']['amount'].replace(',', '')) / 1e12
        ts = sn.get('timestamp', 0)
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
        price = get_ksm_price(dt, ksm_prices)
        usd = amt_ksm * price
        total_native_usd += usd
        cid = TREASURY_CID.get(sn['data']['treasury'], '?')
        name = COMMUNITIES.get(cid, cid)
        native_by_community[name] += usd

    # SwapAsset exercised (SpentAsset events from swap extrinsics)
    exercises = list(pindex.extrinsics.find({
        'section': 'encointerTreasuries',
        'method': {'$in': ['swapAsset', 'swapNative']},
        'success': True,
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }))
    exercise_blocks = set(e['blockNumber'] for e in exercises)

    spent_asset = list(pindex.events.find({
        'section': 'encointerTreasuries', 'method': 'SpentAsset',
        'timestamp': {'$lte': CUTOFF_TS_MS}
    }).sort('timestamp', 1))

    total_swap_usd = 0
    swap_by_community = defaultdict(float)
    for sa in spent_asset:
        if sa['blockNumber'] in exercise_blocks:
            amt_usdc = int(sa['data']['amount'].replace(',', '')) / 1e6
            total_swap_usd += amt_usdc
            cid = TREASURY_CID.get(sa['data']['treasury'], '?')
            name = COMMUNITIES.get(cid, cid)
            swap_by_community[name] += amt_usdc

    total_usd = total_native_usd + total_swap_usd

    print(f"SpendNative total: ${total_native_usd:.2f}")
    for c, v in sorted(native_by_community.items()):
        print(f"  {c}: ${v:.2f}")
    print(f"SwapAsset exercised total: ${total_swap_usd:.2f}")
    for c, v in sorted(swap_by_community.items()):
        print(f"  {c}: ${v:.2f}")
    print(f"Grand total: ${total_usd:.2f}")

    # Context: ceremony reward ~$2, observation period ~16 months
    # Median daily income estimates (from World Bank / local surveys):
    #   Dar es Salaam informal sector: ~$3-5/day
    #   Zaria, Nigeria: ~$2-4/day
    ceremony_reward_usd = 2.0
    print(f"\nCeremony reward: ${ceremony_reward_usd:.2f}")
    print(f"Total = {total_usd / ceremony_reward_usd:.0f} ceremony rewards")

    # Pie chart
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_SINGLE, 2.8))

    # Categories: SpendNative by community, SwapAsset by community
    labels = []
    sizes = []
    colors_list = []
    color_map = {
        'Leu Zürich': '#1f77b4', 'Nyota': '#ff7f0e',
        'PayNuq': '#d62728', 'Green Bay Dollar': '#2ca02c'
    }

    for comm in ['Nyota', 'PayNuq', 'Leu Zürich']:
        val = native_by_community.get(comm, 0)
        if val > 0:
            labels.append(f'SpendNative\n{comm}')
            sizes.append(val)
            colors_list.append(color_map.get(comm, 'gray'))

    for comm in ['Nyota', 'PayNuq', 'Leu Zürich']:
        val = swap_by_community.get(comm, 0)
        if val > 0:
            labels.append(f'SwapAsset\n{comm}')
            sizes.append(val)
            # Lighter version of community color
            base = color_map.get(comm, 'gray')
            colors_list.append(base + '80')  # won't work for named colors

    # Use hatching instead for swap categories
    # Simpler approach: just use distinct colors
    swap_colors = {
        'Leu Zürich': '#aec7e8', 'Nyota': '#ffbb78',
        'PayNuq': '#ff9896'
    }
    colors_list = []
    labels = []
    sizes = []

    for comm in ['Nyota', 'PayNuq', 'Leu Zürich']:
        val = native_by_community.get(comm, 0)
        if val > 0:
            labels.append(f'SpendNative ({comm})')
            sizes.append(val)
            colors_list.append(color_map.get(comm, 'gray'))

    for comm in ['Nyota', 'PayNuq', 'Leu Zürich']:
        val = swap_by_community.get(comm, 0)
        if val > 0:
            labels.append(f'SwapAsset ({comm})')
            sizes.append(val)
            colors_list.append(swap_colors.get(comm, '#cccccc'))

    def autopct(pct):
        val = pct * total_usd / 100
        return f'${val:.0f}\n({pct:.0f}%)' if pct >= 3 else ''

    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct=autopct,
        colors=colors_list, startangle=90,
        pctdistance=0.75, textprops={'fontsize': 6}
    )

    ax.legend(wedges, labels, loc='center left', bbox_to_anchor=(1, 0.5),
              fontsize=6)

    ax.set_title(f'Total: ${total_usd:,.0f} ({total_usd / ceremony_reward_usd:,.0f} ceremony rewards)',
                 fontsize=8, pad=10)

    fig.subplots_adjust(right=0.6)
    savefig(fig, 'fig-value-distribution.pdf')
    client.close()


if __name__ == '__main__':
    main()
