# Stage 8.41: Final Live Demo Rehearsal & Recording Sequence

This document defines the exact step-by-step click order and spoken talking points for rehearsing and recording the live DS08 system demonstration.

---

## Exact Click Order & Script

### 1. START REVIEWER DEMO
- **Action:** Click the gold **[▶ START REVIEWER DEMO]** button in the top navigation bar.
- **Visual:** The 12-step guided walkthrough modal appears at the bottom-right of the screen (`STEP 1 OF 12`).
- **Talking Point:** *"Welcome to the live operational demonstration of the DS08 Thermal-Source Attribution System. This system processes satellite thermal anomalies from NASA FIRMS and performs 4-class source attribution using a pure deep learning model frozen in Stage 8.36."*

---

### 2. LOAD DEMO FIRMS DATA
- **Action:** Click the blue **[LOAD DEMO FIRMS DATA (2025)]** button or click *Next Step* in the tour modal.
- **Visual:** Loading indicator appears for ~4.9s. Summary counters update:
  - Raw Detections: **619**
  - Thermal Events: **428**
- **Talking Point:** *"We load verified, non-test operational observations from June 2025 (VIIRS NOAA-20). In under 5 seconds, the backend spatio-temporally clusters 619 soundings into 428 physical thermal events, extracts 41 causal features, and executes deep neural inference."*

---

### 3. SHOW MAP
- **Action:** Ensure the **OPERATIONAL MAP** tab is active and view the full Indian landmass.
- **Visual:** 428 color-coded circle markers populate the map across India:
  - Red: Industrial Fire (50)
  - Green: Forest Fire (73)
  - Yellow: Agricultural Fire (305)
  - Purple: Other / Persistent Thermal Source
- **Talking Point:** *"The nationwide GIS interface displays every detected event color-coded by the model's predicted class. Detections span from the northern Himalayas to southern Tamil Nadu, classified purely causally without geographic leakage."*

---

### 4. SELECT INDUSTRIAL
- **Action:** Click on the **REVIEWER SCENARIOS** tab, then click **[VIEW EVENT ON MAP & DRAWER]** on Scenario Card 1 (Industrial Fire, Event `EVT_20250627_05B3B989`).
- **Visual:** The map smoothly pans and zooms to Jamnagar, Gujarat ($22.3172^\circ\text{N}, 69.8536^\circ\text{E}$). The event details drawer slides out on the right.
- **Talking Point:** *"Our first scenario examines an industrial thermal anomaly in Jamnagar, Gujarat. The model predicts Industrial Fire. Notice the `MODEL UNCERTAINTY` badge: the model expresses calibrated uncertainty (35.9% Industrial vs 26.8% Forest) rather than artificial overconfidence."*

---

### 5. SHOW EVIDENCE
- **Action:** Scroll through the Event Detail Drawer on the right.
- **Visual:** Highlight the 4 feature evidence cards and natural language explanation:
  - Industrial Context: *4.36 km to RIL Jamnagar Refinery Complex (SEZ)*
  - Thermal Dynamics: *Single nocturnal observation (FRP: 2.72 MW, TI4: 300.61 K, TI5: 283.76 K)*
  - Recurrence: *0 prior alerts (episodic thermal signature)*
  - Natural Language Explanation with calibrated phrasing (*supports*, *consistent with*).
- **Talking Point:** *"The explanation drawer grounds the decision in physical evidence: the 4.36 km proximity to one of the world's largest refinery complexes and nocturnal overpass timing strongly support industrial fire attribution over agricultural burning."*

---

### 6. SELECT FOREST
- **Action:** Return to Reviewer Scenarios or click *Next Step* in the tour modal to select Scenario Card 2 (Forest Fire, Event `EVT_20250625_70A2651C`).
- **Visual:** Map flies to the Northern Himalayan Forest Biome ($29.2749^\circ\text{N}, 88.9035^\circ\text{E}$). Drawer updates with Forest Fire badge (42.8% confidence).
- **Talking Point:** *"Scenario 2 shows a remote forest wildfire in the Himalayas. The event consists of a 4-pixel spatial cluster with a Forest Biome Score of 1.0 (dense canopy) and is located over 500 km away from any industrial infrastructure."*

---

### 7. SELECT AGRICULTURAL
- **Action:** Select Scenario Card 3 (Agricultural Fire, Event `EVT_20250628_96ABE7CB`).
- **Visual:** Map flies to Salem, Tamil Nadu ($11.6958^\circ\text{N}, 78.6631^\circ\text{E}$). Drawer shows Agricultural Fire badge (51.0% confidence).
- **Talking Point:** *"Scenario 3 illustrates seasonal agricultural residue burning in southern India. The Agricultural Heartland Score is 1.0, timing is diurnal, and historical multi-year recurrence is low, leading to confident agricultural attribution."*

---

### 8. SELECT PERSISTENT
- **Action:** Select Scenario Card 4 (Persistent / Other, Event `EVT_825_PER_PER_SRC_05`).
- **Visual:** Map flies to the Hazira/Surat industrial corridor ($21.1250^\circ\text{N}, 72.6948^\circ\text{E}$). Drawer displays Other / Persistent Thermal Source badge (35.0% confidence, top-2 classes within 0.15% margin).
- **Talking Point:** *"Scenario 4 demonstrates the detection of a persistent flaring source. Critically, we do NOT use a forbidden static registry. Instead, the model relies on 18 causal pre-alert recurrence features: 8 historical detections across 4 distinct calendar months at this exact coordinate support stationary flaring rather than an acute biomass blaze."*

---

### 9. OPEN MODEL PERFORMANCE
- **Action:** Click the **MODEL BENCHMARK** navigation tab.
- **Visual:** Model Performance Dashboard displays high-contrast metric cards:
  - Overall Accuracy: **78.57%**
  - Macro-F1: **0.8021**
  - Balanced Accuracy: **81.67%**
  - Correct Predictions: **22 / 28**
  - Visual separation between Development Validation (Spatial CV: 80.00%, Temporal 2025: 85.00%) and Independent Frozen 2026 Test (78.57%).
- **Talking Point:** *"We now view the official frozen benchmark. The model was evaluated exactly once on the frozen, blind 2026 independent test cohort of 28 events, achieving 78.57% accuracy and 0.8021 Macro-F1. Development CV and test results are strictly separated."*

---

### 10. SHOW CONFUSION MATRIX
- **Action:** Scroll to the interactive Confusion Matrix section in the benchmark view.
- **Visual:** 4x4 matrix grid showing:
  - Industrial: 6/6 correct (100% precision, 100% recall)
  - Forest: 5/6 correct (83.3% recall, 1 misclassified as Agricultural)
  - Agricultural: 5/6 correct (83.3% recall, 1 misclassified as Forest)
  - Persistent: 6/10 correct (60.0% recall, 4 misclassified as Agricultural, 100% precision)
- **Talking Point:** *"The confusion matrix shows zero false alarms on Industrial fires (6/6 perfect precision and recall). Forest and Agricultural fires each achieved 83.3% recall. Persistent sources achieved 100% precision with 60% recall, reflecting the physical reality of sparse satellite revisits."*

---

### 11. SHOW LIMITATIONS
- **Action:** Scroll down to the Defense FAQ / Reviewer Quick Answers section. Click on the button **[WHAT IS THE MAIN LIMITATION?]**, then **[WHAT DOES THE SYSTEM DO THAT FIRMS DOES NOT?]**.
- **Visual:** The accordion expands and smoothly highlights the answered questions:
  - Main limitations: Biomass spectral overlap, sparse persistent revisits, and cohort size ($N=28$).
  - Core distinction: *DETECTION $\neq$ SOURCE ATTRIBUTION*. FIRMS detects temperature anomalies; our system attributes the causal source category with contextual GIS evidence.
- **Talking Point:** *"Finally, we transparently address system limitations and defense questions. NASA FIRMS detects thermal anomalies; our system performs source-type attribution to enable prioritized emergency dispatch. This concludes the live demonstration."*
