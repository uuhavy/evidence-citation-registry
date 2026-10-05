"""Verify public deployment, exact source bytes, schema and read behavior.

No saved key or logged-in browser is required. The temporary read-only sender
is generated locally; it signs no transaction and is never funded.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import studionet
from deploy_public import ROOT, SOURCE, MANIFEST, RPC, rpc


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    address = manifest["contract_address"]
    chain_id = int(rpc("eth_chainId", []), 16)
    assert chain_id == manifest["chain_id"] == 61999
    remote_source = base64.b64decode(rpc("gen_getContractCode", [address]), validate=True)
    assert remote_source == SOURCE.read_bytes(), "Deployed source differs from repository"
    validation = json.loads((ROOT / "schema-validation.json").read_text(encoding="utf-8"))
    assert validation["source_sha256"] == hashlib.sha256(remote_source).hexdigest()
    assert validation["exit_code"] == 0 and validation["result"]["ok"] is True
    assert validation["result"]["validate"]["contract"] == "EvidenceCitationRegistry"
    schema = rpc("gen_getContractSchema", [address])
    assert set(schema["methods"]) == {
        'register_document', 'submit_citation', 'audit', 'get_document', 'get_citation', 'get_count'}
    client = create_client(chain=studionet, account=Account.create(), endpoint=RPC)
    receipt = client.get_transaction(manifest["transaction_hash"])
    assert receipt["status_name"] == "FINALIZED"
    assert receipt["data"]["contract_address"].lower() == address.lower()
    assert receipt["consensus_data"]["leader_receipt"][0]["execution_result"] == "SUCCESS"
    count = client.read_contract(address=address, function_name="get_count", args=[])
    assert isinstance(count, int) and count >= 0
    evidence = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "network": "studionet", "chain_id": chain_id, "rpc_url": RPC,
        "contract_address": address, "transaction_hash": manifest["transaction_hash"],
        "deployment_status": receipt["status_name"], "deployment_execution": "SUCCESS",
        "deployed_source_matches_repository": True,
        "official_linter_source_matches_deployment": True,
        "official_linter_evidence": "schema-validation.json",
        "source_sha256": hashlib.sha256(remote_source).hexdigest(),
        "source_bytes": len(remote_source), "schema": schema,
        "read_call": {"method": "get_count", "args": [], "result": count},
        "authentication": "none; public RPC; no browser session or saved key",
    }
    (ROOT / "deployment-verification.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    manifest.update(status="FINALIZED", execution_result="SUCCESS")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
