"""Stage 8.38 Architecture Diagram Generator.

Generates a crisp, publication-quality system architecture flowchart:
- artifacts/stage8_38/final_architecture.png
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
OUTPUT_PNG = PROJECT_ROOT / "artifacts" / "stage8_38" / "final_architecture.png"

def generate_diagram():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    
    # Background color
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#0F172A")
    
    # Title
    ax.text(7, 9.6, "DS08 OPERATIONAL THERMAL-SOURCE ATTRIBUTION ARCHITECTURE", 
            ha="center", va="center", color="#F8FAFC", fontsize=15, fontweight="bold", fontfamily="sans-serif")
    ax.text(7, 9.25, "Real-Time Causal 4-Class Deep Neural Attribution Pipeline for Satellite Thermal Anomalies", 
            ha="center", va="center", color="#94A3B8", fontsize=10, fontfamily="sans-serif")
            
    # Box styles
    box_style_primary = dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#38BDF8", linewidth=1.5)
    box_style_neural = dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#A855F7", linewidth=2.0)
    box_style_output = dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#10B981", linewidth=1.5)
    box_style_storage = dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#F59E0B", linewidth=1.5)
    
    # Stages coordinates (x_center, y_center)
    # Layer 1: Data Ingestion (Top)
    ax.text(3, 8.1, "1. SATELLITE INGESTION\n• NASA FIRMS API / NRT Feeds\n• VIIRS (NOAA-20/Suomi-NPP) & MODIS\n• Pydantic Strict Ingestion Validation\n• Spatial deduplication & coordinate bounds",
            ha="center", va="center", color="#F1F5F9", fontsize=8.5, bbox=box_style_primary)
            
    ax.text(11, 8.1, "2. SPATIOTEMPORAL CLUSTERING\n• DBSCAN / Radius-linked Grouping\n• Radius <= 3.0 km, Window <= 24h\n• Physical thermal event condensation\n• Centroid computation & provenance audit",
            ha="center", va="center", color="#F1F5F9", fontsize=8.5, bbox=box_style_primary)

    # Arrow 1 -> 2
    ax.annotate("", xy=(8.7, 8.1), xytext=(5.3, 8.1),
                arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=1.8))

    # Layer 2: Feature Engineering (Middle-Upper)
    ax.text(7, 6.0, "3. CAUSAL FEATURE EXTRACTION (41 Clean Causal Features)\n"
                    "• Thermal Dynamics (14 feats): FRP, TI4, TI5, Delta TI, Night ratio, Spatial spread (t <= t0)\n"
                    "• Industrial Context (6 feats): Distance to facility, within 1km/5km, baseline deviation\n"
                    "• Ecological Context (3 feats): Indian Forest biome & Agricultural heartland scores\n"
                    "• Pre-Alert Recurrence (18 feats): Multi-year recurrence (t <= t0 - 7 days, registry-free)",
            ha="center", va="center", color="#F1F5F9", fontsize=9, bbox=box_style_primary)

    # Arrow 2 -> 3
    ax.annotate("", xy=(7, 6.9), xytext=(11, 7.3),
                arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=1.8))

    # Layer 3: Frozen Neural Model (Middle-Lower)
    ax.text(7, 4.0, "4. FROZEN DEEP NEURAL MODEL (Architecture1_StaticMLP)\n"
                    "• SHA-256: 5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2\n"
                    "• Multi-Branch Group Encoders + Feature Aggregator + Classification Head\n"
                    "• Pure PyTorch execution (1.0 ms forward pass, CPU/GPU compatible)\n"
                    "• Official Blind Test: 78.57% Acc | 0.8021 Macro-F1 | 81.67% Bal Acc",
            ha="center", va="center", color="#E9D5FF", fontsize=9.5, fontweight="bold", bbox=box_style_neural)

    # Arrow 3 -> 4
    ax.annotate("", xy=(7, 4.7), xytext=(7, 5.1),
                arrowprops=dict(arrowstyle="->", color="#A855F7", lw=2.0))

    # Layer 4: Outputs (Lower)
    ax.text(3, 2.0, "5. 4-CLASS ATTRIBUTION & EXPLANATION\n"
                    "• Classes: Industrial | Forest | Agricultural | Persistent\n"
                    "• Softmax calibrated class probabilities (Sum P = 1.0)\n"
                    "• Evidential Natural Language Explanation\n"
                    "• Zero hallucinations, grounded in feature values",
            ha="center", va="center", color="#F1F5F9", fontsize=8.5, bbox=box_style_output)

    ax.text(11, 2.0, "6. STORAGE, API & VISUALIZATION\n"
                     "• Operational Database: SQLite / PostGIS (Spatial GIST)\n"
                     "• FastAPI REST Endpoints (`/predict`, `/events`, `/api/geojson`)\n"
                     "• Leaflet.js Interactive Web GIS Dashboard\n"
                     "• Dockerized Microservice (`docker/Dockerfile`)",
            ha="center", va="center", color="#F1F5F9", fontsize=8.5, bbox=box_style_storage)

    # Arrow 4 -> 5 & 4 -> 6
    ax.annotate("", xy=(3, 2.8), xytext=(5.5, 3.3),
                arrowprops=dict(arrowstyle="->", color="#10B981", lw=1.8))
    ax.annotate("", xy=(11, 2.8), xytext=(8.5, 3.3),
                arrowprops=dict(arrowstyle="->", color="#F59E0B", lw=1.8))
                
    # Footer badges
    ax.text(7, 0.4, "SCIENTIFIC RIGOR: Registry-Free • Causal Invariance Verified • Single Blind 2026 Evaluation • Zero Leakage",
            ha="center", va="center", color="#64748B", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Architecture diagram successfully generated at {OUTPUT_PNG}")

if __name__ == "__main__":
    generate_diagram()
