"""Deploy the unchanged source to public studionet and retain the transaction ID.

The dedicated test-network key stays in a gitignored .env file. No mocks or
leader-only setting are used on the shared network. Re-running resumes the
recorded transaction rather than submitting a duplicate deployment.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import requests
from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).resolve().parents[1]
RPC = "https://studio.genlayer.com/api"
SOURCE = ROOT / "contracts/evidence_citation_registry.py"
MANIFEST = ROOT / "deployment-studionet.json"


def rpc(method, params):
    response = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1,
                                      "method": method, "params": params}, timeout=45)
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise RuntimeError(json.dumps(result["error"]))
    return result["result"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py")], check=True)
    code = SOURCE.read_bytes()
    assert code.isascii()
    assert code.splitlines()[0] == b"# v0.2.16"
    assert code.splitlines()[2] == b"from genlayer import *"
    assert int(rpc("eth_chainId", []), 16) == 61999
    schema = rpc("gen_getContractSchemaForCode", ["0x" + code.hex()])
    print("Public RPC schema:", json.dumps(schema), flush=True)
    if not args.deploy:
        return
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        assert manifest["source_sha256"] == hashlib.sha256(code).hexdigest()
        print("Existing deployment transaction:", manifest["transaction_hash"], flush=True)
        return
    keyfile = ROOT / ".env.studionet-deployer"
    if not keyfile.exists():
        keyfile.write_text(Account.create().key.hex(), encoding="ascii")
    account = Account.from_key(keyfile.read_text(encoding="ascii").strip())
    client = create_client(chain=studionet, account=account, endpoint=RPC)
    tx = client.deploy_contract(code=code, args=[], leader_only=False)
    manifest = {"network": "studionet", "chain_id": 61999, "rpc_url": RPC,
                "source_sha256": hashlib.sha256(code).hexdigest(),
                "deployer": account.address, "transaction_hash": str(tx),
                "status": "submitted"}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
