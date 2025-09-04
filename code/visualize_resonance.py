"""
visualize_resonance.py
Quick visualization of resonance: intent vs. candidate tokens in embedding space.

Requires: matplotlib, scikit-learn
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from resonance_scoring import l2_normalize
from intent_vector import _dummy_embed  # replace with your real embedder

def plot_resonance(candidates: dict[str, np.ndarray],
                   intent_vec: np.ndarray,
                   method: str = "pca"):
    """
    Visualize candidates + intent in 2D.

    Args:
        candidates: dict of {label: embedding}
        intent_vec: embedding of the latent intent
        method: "pca" or "tsne"
    """
    labels = list(candidates.keys()) + ["INTENT"]
    embs = np.stack(list(candidates.values()) + [intent_vec], axis=0)

    if method == "pca":
        reducer = PCA(n_components=2)
    elif method == "tsne":
        reducer = TSNE(n_components=2, perplexity=5, random_state=42)
    else:
        raise ValueError("method must be 'pca' or 'tsne'")

    coords = reducer.fit_transform(embs)

    plt.figure(figsize=(6, 6))
    for label, (x, y) in zip(labels, coords):
        plt.scatter(x, y, label=label)
        plt.text(x + 0.01, y + 0.01, label, fontsize=9)
    plt.title(f"Resonance Visualization ({method.upper()})")
    plt.legend()
    plt.show()


# --- Demo ---
if __name__ == "__main__":
    # Candidates: English vs. leakage tokens
    candidates = {
        "justice": _dummy_embed(["justice"])[0],
        "maiden": _dummy_embed(["maiden"])[0],
        "παρθένος": _dummy_embed(["παρθένος"])[0],
        "တရား (tayar)": _dummy_embed(["တရား"])[0],
    }

    # Intent = probe of ["maiden","justice"]
    intent_vec = l2_normalize(np.mean(
        _dummy_embed(["maiden","justice"]), axis=0
    ))

    plot_resonance(candidates, intent_vec, method="pca")
