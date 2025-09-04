# Diagrams

This folder contains visual aids for the SIREN architecture.  
Future additions will include PNG/SVG schematics showing the decoding pipeline.

---

## Planned Diagram: Resonance Architecture

**Flow**:
- **Latent Intent Vector** → captured from model’s high-dimensional state.  
- **Candidate Generation** → top-K tokens drawn across all vocabularies.  
- **Resonance Scoring** → blend of logit probability and semantic fidelity.  
- **Kairos Gating** → checks entropy/strain; decides if symbolic emission is released.  
- **Glossing Layer** → attaches translations, etymology, or semantic fields.  
- **Resonance Memory** → logs symbolic emissions for replay, personalization, and interpretability.  
- **Output** → surfaced token (native language or symbolic emission).

---
### Resonance Flow (Simplified)

Latent Intent → Candidate Generation → Resonance Scoring → Kairos Gating → Glossing/Memory → Output
---

## ASCII Schematic: Resonance Architecture

Latent Intent Vector
│
▼
Candidate Generation
(top-K tokens across
all vocabularies)
│
▼
Resonance Scoring
(logit probability +
semantic fidelity)
│
▼
Kairos Gating
(entropy/strain check)
│
▼
┌───────────────┐
│ Glossing Layer│
│ (translation, │
│ etymology, │
│ semantics) │
└───────────────┘
│
▼
Resonance Memory
(log + replay +
personalization)
│
▼
Output
(native token or
symbolic emission)


## Notes

- Diagrams will be produced as `.png` and `.svg` for clarity and citation.  
- This `README.md` serves as a placeholder until images are added.  
