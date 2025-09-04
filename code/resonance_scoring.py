"""
resonance_scoring.py
Prototype scaffold for SIREN resonance scoring 

Key ideas (SIREN):
- Blend decoder confidence (probability/logit) with semantic fidelity (cosine to intent).
- Keep both terms on comparable scales.
- (Optional) Couple alpha to entropy/strain for Kairos gating.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from math import exp
from typing import Optional

# ---------- Utilities ----------

def sigmoid(x: float) -> float:
    """Normalize a real value to (0, 1). Suitable for raw logits."""
    return 1.0 / (1.0 + exp(-x))

def l2_normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """L2-normalize a vector (safe for near-zero)."""
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v) + eps
    return v / n

def rescale_minus1_1_to_0_1(x: float) -> float:
    """Map cosine similarity [-1, 1] -> [0, 1]."""
    return 0.5 * (float(x) + 1.0)

def kairos_alpha(base_alpha: float,
                 entropy: Optional[float] = None,
                 open_thresh: float = 1.5,
                 max_shift: float = 0.25) -> float:
    """
    Kairos: when entropy/strain is high, shift weight toward semantic fidelity
    by reducing alpha (within a bounded range).
    """
    if entropy is None:
        return float(np.clip(base_alpha, 0.0, 1.0))
    if entropy <= open_thresh:
        return float(np.clip(base_alpha, 0.0, 1.0))
    # linear shift beyond threshold (bounded)
    shift = min(max_shift, (entropy - open_thresh) * 0.1)
    return float(np.clip(base_alpha - shift, 0.0, 1.0))

# ---------- Intent Vector (conceptual stub) ----------

def generate_dynamic_intent_vector(context_history: list) -> np.ndarray:
    """
    Conceptual placeholder for deriving latent 'intent' from context.
    Replace with: encoder output, averaged token embeddings, or hidden-state readout.
    """
    # Example/demo only
    return np.array([0.25, 0.35, 0.45], dtype=float)

# ---------- Core Scoring ----------

def resonance_score(logit_or_prob: float,
                    token_embedding: np.ndarray,
                    intent_vector: np.ndarray,
                    alpha: float = 0.5,
                    *,
                    input_is_logit: bool = True,
                    use_kairos: bool = False,
                    entropy: Optional[float] = None) -> float:
    """
    Blend decoder confidence with semantic fidelity.

    Args:
        logit_or_prob: Raw logit (default) or probability for this token.
        token_embedding: Candidate token embedding (1D).
        intent_vector: Latent intent vector.
        alpha: Base weight for decoder confidence vs. semantic fidelity (0..1).
        input_is_logit: If True, apply sigmoid to map to (0,1).
        use_kairos: If True, modulate alpha by entropy (Kairos gating).
        entropy: Optional entropy/strain signal from the decoder distribution.

    Returns:
        Resonance score in [0,1] (both terms scaled comparably).
    """
    # 1) Confidence term in [0,1]
    conf = sigmoid(logit_or_prob) if input_is_logit else float(logit_or_prob)
    conf = float(np.clip(conf, 0.0, 1.0))

    # 2) Semantic fidelity via cosine (rescaled to [0,1])
    te = l2_normalize(token_embedding)
    iv = l2_normalize(intent_vector)
    cos_sim = float(cosine_similarity(te.reshape(1, -1), iv.reshape(1, -1))[0][0])
    sem_fid = rescale_minus1_1_to_0_1(np.clip(cos_sim, -1.0, 1.0))

    # 3) Optional Kairos adjustment to alpha
    a = kairos_alpha(alpha, entropy) if use_kairos else alpha
    a = float(np.clip(a, 0.0, 1.0))

    # 4) Final blend
    return a * conf + (1.0 - a) * sem_fid

# ---------- Demo ----------

if __name__ == "__main__":
    print("--- Example 1: Single Calculation ---")
    logit = 2.5  # raw logit
    token_vec = np.array([0.1, 0.2, 0.3])
    intent_vec = np.array([0.2, 0.1, 0.4])

    score = resonance_score(logit, token_vec, intent_vec, alpha=0.7, input_is_logit=True)
    print(f"Resonance score (alpha=0.7): {score:.4f}")

    print("\n--- Example 2: Alpha sweep ---")
    for a in [0.1, 0.3, 0.5, 0.7, 0.9]:
        s = resonance_score(logit, token_vec, intent_vec, alpha=a, input_is_logit=True)
        print(f"alpha={a:.1f} -> {s:.4f}")

    print("\n--- Example 3: Kairos (entropy raises semantic weight) ---")
    for ent in [0.8, 1.2, 1.6, 2.0]:
        s = resonance_score(logit, token_vec, intent_vec, alpha=0.7,
                            input_is_logit=True, use_kairos=True, entropy=ent)
        print(f"entropy={ent:.1f} -> score={s:.4f} (alpha'={kairos_alpha(0.7, ent):.2f})")

    print("\n--- Example 4: Conceptual dynamic intent ---")
    dyn_intent = generate_dynamic_intent_vector(["hello", "world", "this is SIREN"])
    s = resonance_score(logit, token_vec, dyn_intent, alpha=0.7, input_is_logit=True)
    print(f"Resonance score (dynamic intent): {s:.4f}")
