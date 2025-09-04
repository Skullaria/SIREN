"""
kairos_gating.py
Kairos gating: decide when to *emit* a symbolic token based on
resonance vs. probability, with optional entropy + hysteresis + cooldown.

Intended to be used alongside resonance_scoring.py.
"""

from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class KairosConfig:
    # Emit only when resonance is high *and* normalized logit is low
    resonance_min: float = 0.70      # e.g., 0.70 → "high resonance"
    norm_logit_max: float = 0.30     # e.g., 0.30 → "low probability"
    # Optional third signal: decoding entropy/strain
    entropy_min: Optional[float] = 1.5  # None disables entropy check
    # Hysteresis: stickiness to avoid flicker at threshold boundaries
    hysteresis_delta: float = 0.05   # lower/upper deltas for stable on/off
    # Cooldown: prevent bursts of emissions
    cooldown_seconds: float = 1.0

class KairosGate:
    def __init__(self, cfg: KairosConfig = KairosConfig()):
        self.cfg = cfg
        self._last_emit_ts: float = 0.0
        self._is_open: bool = False  # sticky state for hysteresis

    def _cooldown_ok(self) -> bool:
        return (time.time() - self._last_emit_ts) >= self.cfg.cooldown_seconds

    def _core_condition(self, resonance: float, norm_logit: float, entropy: Optional[float]) -> bool:
        """Base ‘open’ condition (without hysteresis)."""
        cond_res = resonance >= self.cfg.resonance_min
        cond_log = norm_logit <= self.cfg.norm_logit_max
        if self.cfg.entropy_min is None:
            cond_ent = True
        else:
            cond_ent = (entropy is not None) and (entropy >= self.cfg.entropy_min)
        return cond_res and cond_log and cond_ent

    def should_emit(self, resonance: float, norm_logit: float,
                    entropy: Optional[float] = None) -> bool:
        """
        Decide if this time-step is a Kairos moment for symbolic emission.

        Args:
            resonance: blended resonance score in [0,1]
            norm_logit: normalized probability in [0,1] (e.g., sigmoid(logit))
            entropy: optional decoder entropy/strain metric

        Returns:
            True if emission should occur now.
        """
        # Apply hysteresis: when open, allow slightly looser staying-open;
        # when closed, require slightly stronger conditions to open.
        if self._is_open:
            res_min = self.cfg.resonance_min - self.cfg.hysteresis_delta
            log_max = self.cfg.norm_logit_max + self.cfg.hysteresis_delta
        else:
            res_min = self.cfg.resonance_min + self.cfg.hysteresis_delta
            log_max = self.cfg.norm_logit_max - self.cfg.hysteresis_delta

        # Temporarily adopt adjusted thresholds
        base_res_min, base_log_max = self.cfg.resonance_min, self.cfg.norm_logit_max
        try:
            self.cfg.resonance_min = max(0.0, min(1.0, res_min))
            self.cfg.norm_logit_max = max(0.0, min(1.0, log_max))
            core_ok = self._core_condition(resonance, norm_logit, entropy)
        finally:
            # restore
            self.cfg.resonance_min, self.cfg.norm_logit_max = base_res_min, base_log_max

        # Update sticky state
        if core_ok:
            self._is_open = True
        else:
            self._is_open = False

        # Enforce cooldown at emission moment
        if self._is_open and self._cooldown_ok():
            self._last_emit_ts = time.time()
            return True
        return False


# --- Demo usage ---
if __name__ == "__main__":
    from resonance_scoring import sigmoid  # reuse your helper

    gate = KairosGate(KairosConfig(
        resonance_min=0.70,
        norm_logit_max=0.30,
        entropy_min=1.5,
        hysteresis_delta=0.05,
        cooldown_seconds=0.5
    ))

    # Example stream of (resonance, norm_logit, entropy) tuples
    stream = [
        (0.62, sigmoid(2.0), 1.2),  # high prob → should NOT emit
        (0.74, sigmoid(-1.0), 1.6), # low prob + high resonance + entropy → emit
        (0.71, sigmoid(-0.8), 1.7), # within hysteresis; may stay open, cooldown applies
        (0.68, sigmoid(-0.6), 1.8), # dips below → likely close
        (0.80, sigmoid(-2.0), 1.9), # strong signal → emit again after cooldown
    ]

    for i, (res, nl, ent) in enumerate(stream, 1):
        print(f"t{i}: res={res:.2f} norm_logit={nl:.2f} entropy={ent:.2f} -> emit={gate.should_emit(res, nl, ent)}")

