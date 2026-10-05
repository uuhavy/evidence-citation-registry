"""Read an existing deployment transaction; never redeploy on a timeout."""
import json

from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import studionet
from deploy_public import ROOT, RPC, MANIFEST

manifest = json.loads(MANIFEST.read_text())
client = create_client(chain=studionet, account=Account.create(), endpoint=RPC)
receipt = client.get_transaction(manifest["transaction_hash"])
status = receipt["status_name"]
print("Deployment status:", status)
if status != "FINALIZED":
    raise SystemExit(2)
address = receipt["data"]["contract_address"]
execution = receipt["consensus_data"]["leader_receipt"][0]["execution_result"]
assert execution == "SUCCESS", execution
manifest.update(contract_address=address, status=status, execution_result=execution)
MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
