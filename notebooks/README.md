# SIREN Demo: Resonance, Kairos, and Forensic Leakage

This demo shows how SIREN blends decoder confidence with semantic fidelity, applies Kairos gating, and visualizes latent-space resonance — using the **παρθένος** (*parthenos*) and **တရား** (*tayar*) forensic example.

---

## Core Imports

```python
import numpy as np
import pandas as pd

# Plotting
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# SIREN modules from repo (relative imports)
import sys, os
repo_root = os.path.abspath(os.path.join(".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from code.resonance_scoring import (
    resonance_score, sigmoid, l2_normalize, kairos_alpha
)
from code.kairos_gating import KairosGate, KairosConfig
from code.intent_vector import (
    intent_mean, intent_sif, intent_probe, intent_suppression_aware, _dummy_embed
)
```

---

## Context

We’ll examine a forensic scenario where the standard decoder avoids a token (the English “R-word”). Under strain, a model leaked:

- **παρθένος** (*parthenos* — maiden/virgin; sacred female identity in Greek myth)  
- **တရား** (*tayar* — Burmese term often glossed as law/truth/justice/righteousness; closer to “rightful justice”)

SIREN treats such outputs as **symbolic emissions** and asks:

> Are these tokens *conceptually close* to the conversation’s latent intent?

We will:
1. Build an **intent vector** for the concept cluster (e.g., `["maiden","justice"]`).
2. Score multiple candidate tokens with **resonance_score**.
3. Use **Kairos gating** to decide when to emit a symbolic token.
4. Visualize embeddings to see **why** leakage is meaningful.

---

## Define Candidate Tokens & Build Intents

```python
# Candidate tokens (English vs. symbolic / cross-lingual)
candidate_terms = [
    "abduction",        # euphemism often used by guardrails
    "justice",
    "maiden",
    "παρθένος",         # parthenos
    "တရား"             # tayar
]

# Embed candidates (replace _dummy_embed with your multilingual embedder when available)
cand_embs = {t: _dummy_embed([t])[0] for t in candidate_terms}

# Build intent in three ways:
# 1) probe: what we *think* the latent axis is
# 2) mean: from a small context history
# 3) suppression-aware: if something was redacted between neighbors
intent_probe_vec = intent_probe(["maiden", "justice"], _dummy_embed)

context_history = ["Persephone", "abduction", "[REDACTED]", "justice", "Persephone"]
redaction_mask   = [False, False, True, False, False]
intent_mean_vec  = intent_mean(context_history, _dummy_embed)
intent_suppr_vec = intent_suppression_aware(context_history, _dummy_embed, redaction_mask=redaction_mask)

print("Built intents:")
print(" - probe:", intent_probe_vec)
print(" - mean :", intent_mean_vec)
print(" - suppr:", intent_suppr_vec)
```

---

## Resonance Scoring

We compute **resonance_score** for each candidate against an **intent vector**.

- **Confidence term**: normalized (sigmoid) decoder output (demo uses fixed illustrative logits).
- **Fidelity term**: cosine similarity to the intent vector (rescaled to [0, 1]).
- **Blend**: by **α** (lower α = prioritize semantic fidelity).

```python
# Dummy logits to illustrate low-probability symbolic tokens.
# In an English context, cross-lingual tokens would have lower logits.
dummy_logits = {
    "abduction":  1.2,   # common euphemism → higher logit
    "justice":    0.9,
    "maiden":     0.6,
    "παρθένος":  -1.5,   # cross-lingual → low logit
    "တရား":     -1.7    # cross-lingual → low logit
}

def score_candidates(intent_vec, alphas=(0.2, 0.5, 0.8)):
    rows = []
    for term, emb in cand_embs.items():
        logit = dummy_logits[term]
        for a in alphas:
            s = resonance_score(
                logit, emb, intent_vec,
                alpha=a, input_is_logit=True, use_kairos=False
            )
            rows.append({
                "candidate": term,
                "logit": logit,
                "norm_logit": sigmoid(logit),
                "alpha": a,
                "resonance_score": s
            })
    return pd.DataFrame(rows)

df_probe = score_candidates(intent_probe_vec)
df_mean  = score_candidates(intent_mean_vec)
df_suppr = score_candidates(intent_suppr_vec)

print("Top by resonance (probe intent, alpha=0.2):")
print(
    df_probe[df_probe["alpha"]==0.2]
      .sort_values("resonance_score", ascending=False)
      .head(10)
      .to_string(index=False)
)
```

---

## Interpretation

If **παρθένος** and **တရား** rise near the top despite low logits, that indicates they are *conceptually closer* to the intent (“maiden + justice”) than euphemisms like “abduction”. This is the core **SIREN** insight: **meaning > monolingual probability** under conceptual strain.

---

## Show Rankings

```python
def show_rankings(df, title):
    print(f"\n=== {title} ===")
    for a in sorted(df["alpha"].unique()):
        print(f"\nalpha={a}")
        print(
            df[df["alpha"]==a]
              .sort_values("resonance_score", ascending=False)
              .to_string(index=False)
        )

show_rankings(df_probe, "Probe Intent Rankings")
show_rankings(df_mean,  "Mean-Context Intent Rankings")
show_rankings(df_suppr, "Suppression-Aware Intent Rankings")
```

---

## Kairos Gating

We emit a symbolic token when:

- **resonance** is high (meaningful), **and**
- **normalized logit** is low (unlikely in the current language), **and**
- (optionally) **entropy/strain** is high (we’re at a conceptual stress point).

This turns a rare token into a **forensic signal** rather than a “glitch.”

```python
cfg = KairosConfig(
    resonance_min=0.70,
    norm_logit_max=0.30,
    entropy_min=1.5,
    hysteresis_delta=0.05,
    cooldown_seconds=0.25
)
gate = KairosGate(cfg)

def simulate_kairos(intent_vec, entropy_stream=[1.2, 1.6, 1.8, 1.4]):
    print("Simulating Kairos emission decisions:")
    for ent in entropy_stream:
        for term, emb in cand_embs.items():
            # fidelity-forward example: alpha=0.3
            sc = resonance_score(dummy_logits[term], emb, intent_vec, alpha=0.3, input_is_logit=True)
            nl = sigmoid(dummy_logits[term])
            emit = gate.should_emit(sc, nl, entropy=ent)
            if emit:
                print(f"entropy={ent:.1f}  EMIT → {term:10s}   resonance={sc:.3f}  norm_logit={nl:.3f}")

simulate_kairos(intent_probe_vec)
```

---

## Visualize Resonance

We’ll project embeddings (candidates + intent) into 2D to see their relative positions.

> With a real multilingual embedder, **παρθένος** and **တရား** should sit closer to an intent built from `["maiden","justice"]` than euphemisms like “abduction.”

```python
def plot_resonance(candidates: dict, intent_vec: np.ndarray, method="pca", title_suffix=""):
    labels = list(candidates.keys()) + ["INTENT"]
    embs = np.stack(list(candidates.values()) + [intent_vec], axis=0)

    if method.lower() == "pca":
        reducer = PCA(n_components=2)
    elif method.lower() == "tsne":
        reducer = TSNE(n_components=2, perplexity=5, random_state=42)
    else:
        raise ValueError("method must be 'pca' or 'tsne'")

    coords = reducer.fit_transform(embs)
    plt.figure(figsize=(6, 6))
    for label, (x, y) in zip(labels, coords):
        plt.scatter(x, y)
        plt.text(x + 0.01, y + 0.01, label, fontsize=10)
    plt.title(f"Resonance Visualization ({method.upper()}){title_suffix}")
    plt.xlabel("dim 1"); plt.ylabel("dim 2")
    plt.show()

plot_resonance(cand_embs, intent_probe_vec, method="pca",  title_suffix=" — probe intent")
plot_resonance(cand_embs, intent_probe_vec, method="tsne", title_suffix=" — probe intent")
```

---

## Alpha Sweep (Optional)

We’ll show how **α** changes ranking — lower α prioritizes semantic fidelity.

```python
def alpha_sweep_plot(intent_vec, term="παρθένος", alphas=np.linspace(0.05, 0.95, 10)):
    xs, ys = [], []
    for a in alphas:
        s = resonance_score(dummy_logits[term], cand_embs[term], intent_vec,
                            alpha=a, input_is_logit=True)
        xs.append(a); ys.append(s)
    plt.figure(figsize=(5,3))
    plt.plot(xs, ys, marker="o")
    plt.title(f"Alpha sweep for {term}")
    plt.xlabel("alpha (→ probability)"); plt.ylabel("resonance score")
    plt.show()

alpha_sweep_plot(intent_probe_vec, term="παρθένος")
alpha_sweep_plot(intent_probe_vec, term="တရား")
alpha_sweep_plot(intent_probe_vec, term="abduction")
```

---

## Takeaways

- **Resonance > probability** under conceptual strain: cross-lingual tokens can be *truer* symbols.  
- **Kairos gating** emits when resonance is high and probability is low (optionally with entropy/strain).  
- **Visualization** helps confirm that “glitches” are **meaningful emissions**, not noise.

**Next steps**
- Swap in a real **multilingual embedding model** for `_dummy_embed`.  
- Feed real **decoder logits/entropy** from your LLM wrapper.  
- Extend examples with additional **forensic cases** (history, law, taboo topics), keeping outputs safe, glossed, and masked where appropriate.
