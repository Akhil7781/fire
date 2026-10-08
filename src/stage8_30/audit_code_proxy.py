"""
Audit Stage 8.30 code against persistent registry access and target proxies.
"""

import re
from pathlib import Path

FORBIDDEN_PATTERNS = [
    r"persistent_source_manifest\.json",
    r"is_known_persistent",
    r"dist_to_persistent_registry_km",
    r"within_1km_persistent_registry",
    r"within_5km_persistent_registry",
]

def audit():
    src_dir = Path("src/stage8_30")
    files = list(src_dir.glob("*.py"))
    print(f"Auditing {len(files)} files in {src_dir}...")

    violations = []
    for f in files:
        if f.name == "audit_code_proxy.py":
            continue
        content = f.read_text(encoding="utf-8")
        for pat in FORBIDDEN_PATTERNS:
            matches = list(re.finditer(pat, content))
            if matches:
                for m in matches:
                    line_no = content[:m.start()].count("\n") + 1
                    violations.append((f.name, line_no, pat, m.group(0)))

    if violations:
        print("VIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v[0]}:{v[1]} - Pattern '{v[2]}' matched: '{v[3]}'")
        raise ValueError("Forbidden pattern found in Stage 8.30 source code!")
    else:
        print("PASS: Zero forbidden patterns found in src/stage8_30! No access to persistent_source_manifest.json or registry distance features.")

if __name__ == "__main__":
    audit()
