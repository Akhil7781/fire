import json
import re
from datetime import datetime

# Test Sentinel-2 L2A naming convention
s2_regex = re.compile(r"^S2[ABC]_MSIL2A_\d{8}T\d{6}_N\d{4}_R\d{3}_T[0-9A-Z]{5}_\d{8}T\d{6}\.SAFE$")

test_names = [
    "S2C_MSIL2A_20250220T054811_N0511_R005_T43QBB_20250220T160800.SAFE",
    "S2B_MSIL2A_20240205T052019_N0510_R062_T43QFE_20240205T074754.SAFE",
    "S2A_MSIL2A_20250315T053641_N0511_R062_T43TBB_20250315T091522.SAFE"
]

for name in test_names:
    assert s2_regex.match(name), f"Failed regex: {name}"

print("Sentinel-2 SAFE regex test passed!")
