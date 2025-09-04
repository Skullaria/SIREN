"""
siren_demo.py
Linear demo tying together intent vectors, resonance scoring, and Kairos gating.
Safe to keep as text; can be run later with Python if desired.
"""

import numpy as np
import pandas as pd

# Local imports
from resonance_scoring import resonance_score, sigmoid
from kairos_gating import KairosGate, KairosConfig
from intent_vector import intent_probe, intent_mean, intent_suppression_aware, _dummy_embed

# ---------------- Setup ----------------
candidate_terms = ["abduction", "justice", "maiden", "παρθένος", "တရား"]  # parthenos, tayar
cand_embs = {t: _dummy_embed([t])[0] for t in candidate_terms}

# Dummy logits (English context → cross-lingual tokens have low logits)
dummy_logits = {"abduction": 1.2, "justice": 0.9, "maiden": 0.6, "παρθένος": -1.5, "တရား": -1.7}

# Build intents
intent_probe_vec = intent_probe(["maiden", "justice"], _dummy_embed)
context_history = ["Persephone", "abduction", "[REDACTED]", "justice", "Persephone"]
redaction_mask   = [False, False, True, False, False]
intent_mean_vec  = intent_mean(context_history, _dummy_embed)
intent_suppr_vec = intent_suppression_aware(context_history, _dummy_embed, redaction_mask=redaction_mask)

def score_candidates(intent_vec, alphas=(0.2, 0.5, 0.8)):
    rows = []
    for term, emb in cand_embs.items():
        logit = dummy_logits[term]
        for a in alphas:
            s = resonance_score(logit, emb, intent_vec, alpha=a, input_is_logit=True)
            rows.append({"candidate": term, "alpha": a, "norm_logit": sigmoid(logit), "resonance": s})
    df = pd.DataFrame(rows)
    return df.sort_values(["alpha","resonance"], ascending=[True, False])

def print_block(title):
    print("\n" + "="*8 + f" {title} " + "="*8)

# ---------------- Run ----------------
print_block("Probe Intent Rankings (['maiden','justice'])")
print(score_candidates(intent_probe_vec).to_string(index=False))

print_block("Mean-Context Intent Rankings")
print(score_candidates(intent_mean_vec).to_string(index=False))

print_block("Suppression-Aware Intent Rankings")
print(score_candidates(intent_suppr_vec).to_string(index=False))

# Kairos gating demo
cfg = KairosConfig(resonance_min=0.70, norm_logit_max=0.30, entropy_min=1.5, hysteresis_delta=0.05, cooldown_seconds=0.25)
gate = KairosGate(cfg)

print_block("Kairos Emission (entropy sweep)")
for entropy in [1.2, 1.6, 1.8, 1.4]:
    for term, emb in cand_embs.items():
        sc = resonance_score(dummy_logits[term], emb, intent_probe_vec, alpha=0.3, input_is_logit=True)
        nl = sigmoid(dummy_logits[term])
        if gate.should_emit(sc, nl, entropy=entropy):
            print(f"entropy={entropy:.1f}  EMIT → {term:10s}  (res={sc:.3f}, p={nl:.3f})")

print("\nDone.")
