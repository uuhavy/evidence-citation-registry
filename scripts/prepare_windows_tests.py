"""Fix gltest 0.29.2's POSIX-only open-temp-file cleanup on Windows.

This changes only the installed test loader, never contract code. Windows
O_TEMPORARY deletes the message file when its last duplicated handle closes.
Run once after installing requirements-dev.txt, before glsim or gltest.
"""
import importlib.metadata
import os
from pathlib import Path

if os.name != "nt":
    print("Windows compatibility patch not needed on this platform.")
    raise SystemExit(0)

assert importlib.metadata.version("genlayer-test") == "0.29.2"
from gltest.direct import loader

path = Path(loader.__file__)
source = path.read_text(encoding="utf-8")
marker = "# Windows: delete when the final stdin handle closes."
if marker in source:
    print("Windows gltest compatibility patch already installed.")
    raise SystemExit(0)

old_create = "    fd, path = tempfile.mkstemp()\n"
new_create = old_create + (
    "    # Windows: delete when the final stdin handle closes.\n"
    "    if os.name == 'nt':\n"
    "        os.close(fd)\n"
    "        fd = os.open(path, os.O_RDWR | os.O_BINARY | os.O_TEMPORARY)\n"
)
old_unlink = "        os.unlink(path)\n"
new_unlink = "        if os.name != 'nt':\n            os.unlink(path)\n"
assert source.count(old_create) == 1 and source.count(old_unlink) == 1
source = source.replace(old_create, new_create).replace(old_unlink, new_unlink)
path.write_text(source, encoding="utf-8")
print("Applied Windows gltest temporary-file compatibility patch.")
