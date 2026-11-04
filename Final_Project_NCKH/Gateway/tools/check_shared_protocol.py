"""Fail if local Gateway protocol snapshot differs from the team Node header."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
local = root / "include/Secure_Protocol.h"
shared = root.parent / "Patient_Node/shared/Secure_Protocol.h"
if not shared.is_file():
    sys.exit("FAIL: missing Patient_Node/shared/Secure_Protocol.h; run inside team repo")
if local.read_bytes() != shared.read_bytes():
    sys.exit("FAIL: protocol headers differ; coordinate Node/Gateway migration before build")
print("PASS: Gateway and Patient Node protocol headers are byte-identical")
