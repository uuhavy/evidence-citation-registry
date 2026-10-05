"""Execute one resumable demo step or verify public evidence without sending.

Inputs are fictional examples. All on-chain calls and LLM assessments are real.
No mocks or leader-only settings. Keys stay in gitignored .env.* files.
"""
import argparse
from datetime import datetime, timezone
import json
from eth_account import Account
from genlayer_py import create_client
from genlayer_py.chains import studionet
from deploy_public import ROOT, RPC, MANIFEST

parser = argparse.ArgumentParser()
parser.add_argument("--send", action="store_true")
opts = parser.parse_args()
manifest = json.loads(MANIFEST.read_text())
plan = json.loads((ROOT / "example-plan.json").read_text(encoding="utf-8"))
address = manifest["contract_address"]
path = ROOT / "live-example.json"
reader = create_client(chain=studionet,account=Account.create(),endpoint=RPC)
if path.exists():
    data = json.loads(path.read_text())
else:
    if not opts.send:
        raise SystemExit("No recorded example yet; --send starts it.")
    assert reader.read_contract(address=address,function_name="get_count",args=[]) == 0
    accounts = {"deployer":manifest["deployer"]}
    for role in plan.get("additional_accounts",[]):
        keyfile = ROOT / (".env.studionet-"+role)
        if not keyfile.exists(): keyfile.write_text(Account.create().key.hex(),encoding="ascii")
        accounts[role] = Account.from_key(keyfile.read_text().strip()).address
    data = {"network":"studionet","contract_address":address,"accounts":accounts,
        "plan":plan,"transactions":[],"result_kind":"REAL public execution of fictional inputs; no mocks; leader_only=False"}
assert data["contract_address"] == address and data["plan"] == plan

def save():
    path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")

def args(values):
    return [data["accounts"][x[1:]] if isinstance(x,str) and x.startswith("$") else x for x in values]

def check_subset(actual, expected):
    if isinstance(expected,dict):
        assert isinstance(actual,dict)
        for key,value in expected.items(): check_subset(actual[key],value)
    else:
        assert actual == expected, (actual,expected)

def read_checks(checks):
    results=[]
    for check in checks:
        value=reader.read_contract(address=address,function_name=check["method"],args=args(check["args"]))
        value=json.loads(value) if isinstance(value,str) else value
        check_subset(value,check["expected"])
        results.append({"method":check["method"],"args":args(check["args"]),"actual":value})
    return results

for index,tx in enumerate(data["transactions"]):
    if not (opts.send and tx.get("status")=="FINALIZED" and tx.get("checks_complete")):
        receipt=reader.get_transaction(tx["hash"])
        tx["status"]=receipt["status_name"]
        save()
        print(tx["method"],tx["status"],flush=True)
        if tx["status"] != "FINALIZED": raise SystemExit(2)
        tx["execution_result"]=receipt["consensus_data"]["leader_receipt"][0]["execution_result"]
        save()
        assert tx["execution_result"]=="SUCCESS",tx
        if not tx.get("checks_complete"):
            tx["reads_after"]=read_checks(plan["steps"][index].get("reads_after",[]))
            tx["checks_complete"]=True
            save()
index=len(data["transactions"])
if index==len(plan["steps"]):
    data["final_reads"]=read_checks(plan["final_reads"])
    data["verified_at_utc"]=datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps(data["final_reads"],indent=2))
elif opts.send:
    step=plan["steps"][index]
    role=step.get("role","deployer")
    account=Account.from_key((ROOT/(".env.studionet-"+role)).read_text().strip())
    assert account.address==data["accounts"][role]
    client=create_client(chain=studionet,account=account,endpoint=RPC)
    actual_args=args(step["args"])
    tx=client.write_contract(address=address,function_name=step["method"],args=actual_args,leader_only=False)
    data["transactions"].append({"method":step["method"],"args":actual_args,"sender":account.address,
        "hash":str(tx),"status":"submitted"})
    save()
    print("Submitted",step["method"],tx,flush=True)
else:
    print("Next step:",plan["steps"][index]["method"],"(use --send)")
