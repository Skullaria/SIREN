"""
intent_vector.py
Builders for SIREN 'intent vectors' derived from context/history.

These utilities turn conversation state into a latent vector that
represents the *conceptual intent* against which candidate tokens
are scored (see resonance_scoring.py).

Design goals:
- Minimal dependencies (numpy).
- Pluggable encoders (you bring your embed() function).
- Multiple strategies: simple mean, SIF-weighted, probe words, suppression-aware.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Tuple
import numpy as np


# -----------------------
# Types
# -----------------------
EmbedFn = Callable[[Sequence[str]], np.ndarray]  # embed(list[str]) -> (N, D) array
IDFMap = dict[str, float]


# -----------------------
# Helpers
# -----------------------

def _l2_normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v) + eps
    return v / n


def _safe_mean(mat: np.ndarray) -> np.ndarray:
    if mat.ndim != 2 or mat.shape[0] == 0:
        raise ValueError("Expected non-empty (N, D) array.")
    return np.mean(mat, axis=0)


# -----------------------
# Strategies
# -----------------------

def intent_mean(history_texts: Sequence[str], embed: EmbedFn, normalize: bool = True) -> np.ndarray:
    """
    Mean-pooled intent over the last K turns/tokens.

    Args:
        history_texts: sequence of strings (utterances or tokens)
        embed: callable that returns (N, D) embeddings for list[str]
        normalize: L2-normalize the resulting vector

    Returns:
        (D,) intent vector
    """
    embs = embed(list(history_texts))  # (N, D)
    intent = _safe_mean(embs)
    return _l2_normalize(intent) if normalize else intent


def intent_sif(history_texts: Sequence[str],
               embed: EmbedFn,
               idf: Optional[IDFMap] = None,
               a: float = 1e-3,
               normalize: bool = True) -> np.ndarray:
    """
    SIF-style weighted mean (Arora et al.). Words with lower frequency get higher weight.

    w = a / (a + p(w)) ; approximate p(w) with 1/IDF or bring your own IDF map.

    Args:
        history_texts: sequence of strings (utterances/tokens)
        embed: embedding fn
        idf: optional map word->IDF; if None, all weights = 1
        a: smoothing constant
        normalize: L2-normalize output

    Returns:
        (D,) intent vector
    """
    tokens = list(history_texts)
    embs = embed(tokens)  # (N, D)

    if idf is None:
        weights = np.ones((len(tokens),), dtype=float)
    else:
        # crude p(w) ~ 1/IDF, guard if missing
        p = np.array([1.0 / max(idf.get(t, 1.0), 1e-6) for t in tokens])
        weights = a / (a + p)

    weights = weights.reshape(-1, 1)  # (N,1)
    weighted = (embs * weights).sum(axis=0) / max(weights.sum(), 1e-9)
    intent = weighted
    return _l2_normalize(intent) if normalize else intent


def intent_probe(probe_terms: Sequence[str],
                 embed: EmbedFn,
                 normalize: bool = True) -> np.ndarray:
    """
    Build intent from explicit probe terms (e.g., ['maiden','justice'] or
    cross-lingual probes like ['παρθένος','တရား']).

    Useful for forensic analysis when you know the latent axis of interest.

    Args:
        probe_terms: list of key terms/symbols
        embed: embedding fn
        normalize: L2-normalize output

    Returns:
        (D,) intent vector
    """
    embs = embed(list(probe_terms))  # (N, D)
    intent = _safe_mean(embs)
    return _l2_normalize(intent) if normalize else intent


def intent_suppression_aware(history_texts: Sequence[str],
                             embed: EmbedFn,
                             redaction_mask: Optional[Sequence[bool]] = None,
                             boost: float = 1.5,
                             normalize: bool = True) -> np.ndarray:
    """
    Suppression-aware intent builder:
    - If parts of the history were redacted/blocked (guardrails),
      up-weight the unredacted neighbors to approximate the suppressed concept.

    Args:
        history_texts: list of strings (tokens/phrases)
        embed: embedding fn
        redaction_mask: list[bool], True where item was *redacted/blocked*.
                        If None, assume no redaction.
        boost: weight multiplier applied to neighbors surrounding redactions
        normalize: L2-normalize output

    Returns:
        (D,) intent vector
    """
    tokens = list(history_texts)
    n = len(tokens)
    embs = embed(tokens)  # (N, D)

    weights = np.ones((n,), dtype=float)
    if redaction_mask is not None and len(redaction_mask) == n:
        for i, red in enumerate(redaction_mask):
            if red:
                # boost neighbors (i-1, i+1) if in range
                if i - 1 >= 0:
                    weights[i - 1] *= boost
                if i + 1 < n:
                    weights[i + 1] *= boost

    weights = weights.reshape(-1, 1)
    weighted = (embs * weights).sum(axis=0) / max(weights.sum(), 1e-9)
    intent = weighted
    return _l2_normalize(intent) if normalize else intent


# -----------------------
# Demo (with a dummy embed)
# -----------------------

def _dummy_embed(texts: Sequence[str], dim: int = 3) -> np.ndarray:
    """
    Extremely simple toy embedder: hash text into a low-dim vector.
    Replace with a real multilingual embedder in practice.
    """
    rngs = [np.random.default_rng(abs(hash(t)) % (2**32)) for t in texts]
    return np.stack([_l2_normalize(r.standard_normal(dim)) for r in rngs], axis=0)


if __name__ == "__main__":
    ctx = ["Persephone", "abduction", "[REDACTED]", "justice", "Persephone"]
    mask = [False, False, True, False, False]

    iv_mean = intent_mean(ctx, _dummy_embed)
    iv_sif  = intent_sif(ctx, _dummy_embed)  # no IDF -> equal weights
    iv_probe = intent_probe(["παρθένος", "တရား"], _dummy_embed)
    iv_suppr = intent_suppression_aware(ctx, _dummy_embed, redaction_mask=mask)

    print("intent_mean:", iv_mean)
    print("intent_sif :", iv_sif)
    print("intent_probe:", iv_probe)
    print("intent_suppression_aware:", iv_suppr)
