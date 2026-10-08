# STAGE 8.18A — INTER-ANNOTATOR AGREEMENT METRICS SPECIFICATION
**Mathematical Formulations, Edge-Case Handling, and Applicability Rules**

- **Document Version:** 2.0.0
- **Stage:** Stage 8.18A — Protocol Review & Sign-Off Preparation
- **Status:** **REVISED SPECIFICATION — LOCKED FOR HUMAN REVIEW**
- **Domain:** Double-Blind Human Annotation Consensus, Quality Auditing, and Verification

---

## 1. Problem Statement & Audit Finding

In Stage 8.18, the proposed annotation protocol mandated double-blind annotation with consensus adjudication, targeting agreement thresholds across Cohen's Kappa, mean Intersection over Union (IoU), and flag Jaccard similarity.

**Defect in Stage 8.18:**
1. **The Kappa Paradox:** When negative chips heavily dominate a batch (e.g., $80\%$ negative controls), standard Cohen's Kappa experiences severe deflation due to high expected agreement $P_e$, reporting poor agreement despite $98\%$ raw concordant decisions.
2. **Degenerate Edge Cases ($0/0$):** In batches where annotators unanimously agree on a single class, $P_e = 1.0$ and $P_o = 1.0$, producing a division-by-zero error.
3. **Empty Bounding Box Distortion:** When both annotators correctly observe `NO_VISIBLE_TARGET` ($N_1 = 0, N_2 = 0$), calculating spatial bounding-box IoU produces $0/0$. Scoring this as $1.0$ artificially inflates bounding box localization scores; scoring as $0.0$ severely penalizes correct negative consensus.
4. **Rare-Class Masking:** Macro-aggregating metrics across classes conceals critical disagreements in rare, high-consequence classes like `Industrial Fire`.

---

## 2. Metric 1: Chip-Level Observation Status Agreement

### 2.1 Cohen's Kappa ($\kappa$)
Let $N$ be the number of chips evaluated by Annotator 1 and Annotator 2 across $K$ nominal categories (e.g., `NO_VISIBLE_TARGET`, `HAS_ANNOTATIONS`).

$$\kappa = \frac{P_o - P_e}{1 - P_e}$$

where:
- Observed agreement: $P_o = \frac{1}{N} \sum_{i=1}^K n_{ii}$
- Expected chance agreement: $P_e = \sum_{i=1}^K \left( \frac{n_{i\cdot}}{N} \cdot \frac{n_{\cdot i}}{N} \right)$

### 2.2 Degenerate Edge-Case Resolution:
- **Condition:** $P_e = 1.0$ and $P_o = 1.0$ (complete unanimity on a single category).
- **Formal Definition:** When $P_o = P_e = 1.0$, the metric is mathematically defined as:
  $$\kappa \equiv 1.00 \quad (\text{Perfect Deterministic Concordance})$$
- The audit engine must trap $1 - P_e < 10^{-6}$ and return $1.00$ rather than `NaN` or ZeroDivisionError.

### 2.3 Mitigation of the Kappa Paradox: PABAK & Gwet's $AC_1$
To protect against misleadingly low $\kappa$ values under extreme class imbalance, the audit system must compute and report two additional complementary statistics:

1. **Prevalence-Adjusted Bias-Adjusted Kappa (PABAK):**
   $$\text{PABAK} = 2P_o - 1$$
   Provides the true concordant proportion unaffected by marginal prevalence skew.

2. **Gwet's First-Order Agreement Coefficient ($AC_1$):**
   $$AC_1 = \frac{P_o - P_e^{\gamma}}{1 - P_e^{\gamma}}$$
   where $P_e^{\gamma} = \frac{1}{K-1} \sum_{i=1}^K \pi_i (1 - \pi_i)$ with $\pi_i = \frac{n_{i\cdot} + n_{\cdot i}}{2N}$.
   Gwet's $AC_1$ is statistically stable against high negative-class prevalence.

---

## 3. Metric 2: Bounding Box Spatial Agreement (Matched IoU & Hungarian Bipartite Matching)

### 3.1 Intersection over Union (IoU)
For two bounding boxes $B_1, B_2 \in [x_{\min}, y_{\min}, x_{\max}, y_{\max}]$:

$$\text{IoU}(B_1, B_2) = \frac{\text{Area}(B_1 \cap B_2)}{\text{Area}(B_1 \cup B_2)}$$

### 3.2 Bipartite Matching via Hungarian Algorithm:
For a chip where Annotator 1 proposes $M$ boxes $\{A_i\}_{i=1}^M$ and Annotator 2 proposes $N$ boxes $\{B_j\}_{j=1}^N$:
1. Construct cost matrix $C_{ij} = 1.0 - \text{IoU}(A_i, B_j)$.
2. Solve the linear sum assignment problem (Hungarian algorithm) to find the optimal assignment minimizing total distance.
3. A pair $(A_i, B_j)$ is considered a **Spatial Match** if and only if $\text{IoU}(A_i, B_j) \ge 0.50$.

### 3.3 Strict Edge-Case Handling Rules for IoU:
1. **Both Annotators Propose Zero Boxes ($M = 0, N = 0$):**
   - **Applicability Rule:** IoU is **NOT DEFINED** for empty bounding box sets.
   - **Enforcement:** Such chips are classified as **True Negative Detection Consensus**. They are **STRICTLY EXCLUDED** from the box-level Mean IoU denominator. They must never be scored as $0.00$ or $1.00$.
2. **One Proposes Boxes, One Proposes Zero ($M > 0, N = 0$ or $M = 0, N > 0$):**
   - **Applicability Rule:** Box IoU is undefined for unmatched boxes.
   - **Enforcement:** These represent localization false positives / false negatives and are penalized in the **Detection F1-Score**, not by polluting the continuous IoU metric with synthetic zeros.

$$\text{Mean Matched IoU} = \frac{1}{|\mathcal{M}|} \sum_{(i, j) \in \mathcal{M}} \text{IoU}(A_i, B_j) \quad \text{where } \mathcal{M} = \{(i, j) \mid \text{IoU}(A_i, B_j) \ge 0.50\}$$
If $|\mathcal{M}| = 0$, Mean Matched IoU is reported as `N/A (No paired positive boxes)`.

---

## 4. Metric 3: Object Detection F1-Score

To capture box-level omissions and false detections, annotator agreement is evaluated as a symmetric detection retrieval task:

Let:
- $TP = |\mathcal{M}_{\text{class}}| = \text{Count of matched box pairs with } \text{IoU} \ge 0.50 \text{ and } \text{Class}_1 = \text{Class}_2$
- $FP = M - TP = \text{Unmatched boxes from Annotator 1}$
- $FN = N - TP = \text{Unmatched boxes from Annotator 2}$

$$\text{Precision} = \frac{TP}{TP + FP} = \frac{TP}{M}, \quad \text{Recall} = \frac{TP}{TP + FN} = \frac{TP}{N}$$

$$\text{Detection } F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} = \frac{2 \cdot TP}{M + N}$$

### Edge-Case Handling:
- If $M = 0$ and $N = 0$: Detection $F_1$ is recorded as `N/A (Zero candidate boxes, Chip Concordance = 1.0)`.

---

## 5. Metric 4: Visual Evidence Flag Agreement (Jaccard Index)

For matched bounding boxes or chips with active observations, each annotator assigns a set of binary evidence tags:
$E_1, E_2 \subseteq \{\text{DIRECT\_FIRE}, \text{SMOKE\_PLUME}, \text{SWIR\_ANOMALY}, \text{BURN\_SCAR}, \dots\}$

$$\text{Jaccard Similarity } J(E_1, E_2) = \frac{|E_1 \cap E_2|}{|E_1 \cup E_2|}$$

### Edge-Case Handling:
- If both sets are empty ($E_1 = \emptyset$ and $E_2 = \emptyset$):
  $$J(\emptyset, \emptyset) \equiv 1.00 \quad (\text{Perfect Unanimous Absence of Evidence})$$
- If one set is empty and the other non-empty:
  $$J(E_1, \emptyset) = 0.00$$

---

## 6. Rare-Class Stratification Requirements

To prevent majority classes from hiding catastrophic failure on rare classes:
1. **One-vs-Rest Evaluation:** Every metric must be computed independently for each class $c \in \{\text{Industrial Fire}, \text{Forest Fire}, \text{Agricultural Fire}, \text{Other Thermal}, \text{Non-Fire Background}\}$.
2. **Mandatory Adjudication Trigger for Rare Classes:**
   - Any disagreement involving `Industrial Fire` (e.g., Annotator 1 says `Industrial Fire`, Annotator 2 says `Forest Fire` or `NO_VISIBLE_TARGET`) **instantly bypasses automated thresholds and triggers mandatory Stage 8.16 human adjudication**, regardless of overall batch agreement scores.
