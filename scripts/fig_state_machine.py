#!/usr/bin/env python3
"""Draw proposal state machine diagram for the paper."""
from common import *
import matplotlib.patches as mpatches

def main():
    setup_style()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_DOUBLE + 1.0, 3.6))
    ax.set_xlim(-1.8, 11.0)
    ax.set_ylim(-1.4, 3.8)
    ax.set_aspect('equal')
    ax.axis('off')

    # Layout: top row = happy path, bottom row = terminal failure states
    states = {
        'Ongoing':      (1.5, 2.0),
        'Confirming':   (4.5, 2.0),
        'Approved':     (7.5, 2.0),
        'Enacted':      (7.5, 3.2),
        'Rejected':     (1.5, -0.5),
        'SupersededBy': (4.5, -0.5),
    }

    state_colors = {
        'Ongoing':      ('#DDEEFF', '#4878A8'),
        'Confirming':   ('#FFF3CD', '#C49B00'),
        'Approved':     ('#D4EDDA', '#28A745'),
        'Enacted':      ('#C3E6CB', '#1E7E34'),
        'Rejected':     ('#F8D7DA', '#DC3545'),
        'SupersededBy': ('#E2E3E5', '#6C757D'),
    }

    box_w, box_h = 1.7, 0.55
    bw2, bh2 = box_w / 2, box_h / 2

    for name, (x, y) in states.items():
        fill, edge = state_colors[name]
        rect = mpatches.FancyBboxPatch(
            (x - bw2, y - bh2), box_w, box_h,
            boxstyle='round,pad=0.08',
            facecolor=fill, edgecolor=edge, linewidth=1.3
        )
        ax.add_patch(rect)
        ax.text(x, y, name, ha='center', va='center',
                fontsize=8, fontweight='bold', color=edge)

    def arrow(x1, y1, x2, y2, label, lbl_x=None, lbl_y=None,
              fontsize=6, curve=0):
        props = dict(arrowstyle='->', color='#333333', lw=0.8,
                     shrinkA=4, shrinkB=4)
        if curve:
            props['connectionstyle'] = f'arc3,rad={curve}'
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=props)
        if label:
            lx = lbl_x if lbl_x is not None else (x1 + x2) / 2
            ly = lbl_y if lbl_y is not None else (y1 + y2) / 2 + 0.2
            ax.text(lx, ly, label, ha='center', va='center',
                    fontsize=fontsize, color='#444444', fontstyle='italic')

    # Submit -> Ongoing
    arrow(-0.6, 2.0, states['Ongoing'][0] - bw2, 2.0,
          'submit', lbl_x=-0.2, lbl_y=2.25)

    # Ongoing -> Confirming (passing AQB threshold)
    arrow(states['Ongoing'][0] + bw2, 2.1,
          states['Confirming'][0] - bw2, 2.1,
          'passing AQB', lbl_y=2.35)

    # Confirming -> Ongoing (no longer passing)
    arrow(states['Confirming'][0] - bw2, 1.9,
          states['Ongoing'][0] + bw2, 1.9,
          'not passing', lbl_y=1.6)

    # Confirming -> Approved (confirmed for required period)
    arrow(states['Confirming'][0] + bw2, 2.0,
          states['Approved'][0] - bw2, 2.0,
          'confirmed for\nrequired period', lbl_y=2.48, fontsize=5.5)

    # Approved -> Enacted (at next Assigning phase)
    arrow(states['Approved'][0], 2.0 + bh2,
          states['Enacted'][0], 3.2 - bh2,
          'enacted at next\nceremony cycle', lbl_x=8.5, lbl_y=2.65, fontsize=5.5)

    # Ongoing -> Rejected (lifetime expired)
    arrow(states['Ongoing'][0], 2.0 - bh2,
          states['Rejected'][0], -0.5 + bh2,
          'lifetime expired', lbl_x=0.7, lbl_y=0.75, fontsize=5.5)

    # Ongoing -> SupersededBy (same action type approved by another proposal)
    arrow(states['Ongoing'][0] + 0.5, 2.0 - bh2,
          states['SupersededBy'][0] - 0.5, -0.5 + bh2,
          'same type\napproved', lbl_x=2.4, lbl_y=0.65, fontsize=5.5)

    # Confirming -> SupersededBy
    arrow(states['Confirming'][0], 2.0 - bh2,
          states['SupersededBy'][0], -0.5 + bh2,
          '', fontsize=5.5)

    savefig(fig, 'democracy-proposal-state-machine.pdf')

if __name__ == '__main__':
    main()
