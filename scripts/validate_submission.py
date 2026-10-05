"""Run the unmodified official linter on the exact deployable source bytes."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "contracts/evidence_citation_registry.py"
code = source.read_bytes()
assert code.isascii(), "Contract must be ASCII"
assert code.splitlines()[0] == b"# v0.2.16"
assert code.splitlines()[2] == b"from genlayer import *"
assert list((ROOT / "contracts").glob("*.py")) == [source]
env = dict(os.environ, GENVM_VERSION="v0.2.16", PYTHONUTF8="1")
command = [sys.executable, "-m", "genvm_linter.cli", "check", str(source), "--json"]
result = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8")
try:
    report = json.loads(result.stdout)
except ValueError:
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode or 1)
record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
          "tool": "genvm-linter", "tool_version": importlib.metadata.version("genvm-linter"),
          "genvm_version": "v0.2.16", "source": "contracts/evidence_citation_registry.py",
          "source_sha256": hashlib.sha256(code).hexdigest(),
          "command": "genvm-lint check contracts/evidence_citation_registry.py --json",
          "exit_code": result.returncode, "result": report}
(ROOT / "schema-validation.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
print(json.dumps(record, indent=2))
raise SystemExit(result.returncode)
