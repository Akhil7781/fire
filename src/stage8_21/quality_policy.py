"""
Stage 8.21 - Quality Policy and Specification Constants
Formal definition of the active SCL quality policy and Sentinel-2 preprocessing rules
inherited from Stage 8.20.
"""

from typing import Dict, Set

# Spatial geometry & grid specifications
CHIP_SIZE_PIXELS: int = 512
PIXEL_RESOLUTION_M: float = 10.0
CHIP_SIZE_M: float = 5120.0
BAND_ORDER_ML = ["B02", "B03", "B04", "B11", "B12"]
REQUIRED_BANDS = ["B02", "B03", "B04", "B11", "B12", "SCL"]

# Resampling methods
RESAMPLING_REFLECTANCE_20M = "bilinear"
RESAMPLING_SCL_20M = "nearest"

# Normalization
NORMALIZATION_METHOD = "DN / 10000.0, clipped to [0.0, 1.0]"
NORMALIZATION_DTYPE = "float32"

# SCL Quality Policy
AOI_CONTAMINATION_THRESHOLD_PCT: float = 5.0
CENTRAL_1KM_CONTAMINATION_PASS_PCT: float = 5.0
CENTRAL_1KM_CONTAMINATION_CONDITIONAL_PCT: float = 10.0

# SCL Class Categorization
SCL_CLASSES: Dict[int, str] = {
    0: "NO_DATA",
    1: "SATURATED_DEFECTIVE",
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW_ICE",
}

SCL_VALID_CLASSES: Set[int] = set(SCL_CLASSES.keys())
SCL_INVALID_CLASSES: Set[int] = {0, 1}
SCL_SHADOW_CLASSES: Set[int] = {3}
SCL_CLOUD_CLASSES: Set[int] = {8, 9, 10}
SCL_CONTAMINATED_CLASSES: Set[int] = {3, 8, 9, 10}
SCL_SNOW_ICE_CLASSES: Set[int] = {11}
SCL_CLEAR_CLASSES: Set[int] = {2, 4, 5, 6, 7, 11}


def evaluate_scl_quality(
    aoi_contamination_pct: float,
    central_1km_contamination_pct: float,
    cloud_exception_applied: bool = False,
) -> str:
    """
    Evaluates SCL quality status based on the locked DS08 Stage 8.20 rules.
    Returns: 'PASS', 'CONDITIONAL', or 'REJECT'.
    """
    if cloud_exception_applied:
        # DEC-U5 exception candidate
        if central_1km_contamination_pct <= CENTRAL_1KM_CONTAMINATION_PASS_PCT:
            return "CONDITIONAL" if aoi_contamination_pct > AOI_CONTAMINATION_THRESHOLD_PCT else "PASS"
        elif central_1km_contamination_pct <= CENTRAL_1KM_CONTAMINATION_CONDITIONAL_PCT:
            return "CONDITIONAL"
        else:
            return "REJECT"
    else:
        # Standard candidate rule
        if aoi_contamination_pct <= AOI_CONTAMINATION_THRESHOLD_PCT and central_1km_contamination_pct <= CENTRAL_1KM_CONTAMINATION_PASS_PCT:
            return "PASS"
        elif central_1km_contamination_pct <= CENTRAL_1KM_CONTAMINATION_CONDITIONAL_PCT:
            return "CONDITIONAL"
        else:
            return "REJECT"
