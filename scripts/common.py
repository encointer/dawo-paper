"""Shared configuration and utilities for paper analysis scripts."""
from pymongo import MongoClient
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

MONGO_URI = ('mongodb://encointer-query:rqTm4AFl9uCycSpbBEBj@'
             'bezzera.encointer.org:27417/?tls=true&authSource=admin'
             '&tlsAllowInvalidCertificates=true')

FIGURES_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures')

COMMUNITIES = {
    'u0qj944rhWE': 'Leu Zürich',
    'dpcmj33LUs9': 'Green Bay Dollar',
    'kygch5kVGq7': 'Nyota',
    's1vrqQL2SD': 'PayNuq',
}

# Springer single-column width ~3.5in, double ~7in
FIG_WIDTH_SINGLE = 3.5
FIG_WIDTH_DOUBLE = 7.0

def get_client():
    return MongoClient(MONGO_URI)

def setup_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 8,
        'axes.labelsize': 9,
        'axes.titlesize': 10,
        'legend.fontsize': 7,
        'xtick.labelsize': 7,
        'ytick.labelsize': 7,
        'figure.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
    })

def savefig(fig, name):
    path = os.path.join(FIGURES_DIR, name)
    fig.savefig(path, format='pdf')
    plt.close(fig)
    print(f"  Saved: {path}")
