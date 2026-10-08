# Stage 8.33: Final Model Selection & Architecture Specification

**Auditor:** Autonomous Agentic AI  
**Selected Architecture:** `ModelG_BestSimplified`  
**Operational Framework:** Pure PyTorch Deep Learning Only (Zero classical ML models)  
**Checkpoint SHA-256:** `c06b8afe012096268800d26798bd8ef56573275df13142be45d62152cf3e37cc`  

---

## Architectural Rationale

1. **Simplicity Over Over-Parameterization:**
   Stage 8.32's gated residual fusion added unnecessary parameter complexity ($N=107$ train samples). Direct concatenated residual projection achieves superior generalization across spatial folds.

2. **Dedicated Persistence Branch:**
   Solves the 70% persistence regression by isolating historical recurrence gradients from spatial facility proximity.

3. **Coordinate-Free Generalization:**
   `centroid_lat` and `centroid_lon` are completely excluded. The model relies on transferable physical fire physics, diurnal overpass signatures, and static continuous ecoregion context.

4. **Multi-Task Acute Supervision:**
   Simultaneous supervision on the acute 3-class boundary reinforces Agricultural vs Forest separation.
