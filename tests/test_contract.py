import json
import pytest

BODY="The service supports offline mode. This statement applies to version 2 only."
QUOTE="The service supports offline mode."
CLAIM="Version 2 supports offline mode."

def answer(quote="SUPPORTS",context="CONSISTENT",reason="The selected source supports the claim."):
    return json.dumps(dict(quote_relation=quote,context_relation=context,reason=reason))

def mock(vm,raw=None):
    vm.clear_mocks(); vm.mock_llm(r".*",answer() if raw is None else raw)

@pytest.fixture
def contract(direct_vm,direct_deploy,direct_alice):
    direct_vm.sender=direct_alice
    return direct_deploy("contracts/evidence_citation_registry.py",sdk_version="v0.2.16")

@pytest.fixture
def pending(contract,direct_vm,direct_bob):
    assert contract.register_document("Release note",BODY)=="0"
    direct_vm.sender=direct_bob
    assert contract.submit_citation("0",CLAIM,QUOTE,0)=="0"
    return contract

@pytest.mark.parametrize("quote,context,verdict",[
    ("SUPPORTS","CONSISTENT","VERIFIED"),("SUPPORTS","CONTRADICTS","REJECTED"),
    ("SUPPORTS","INSUFFICIENT","UNRESOLVED"),("CONTRADICTS","CONSISTENT","REJECTED"),
    ("CONTRADICTS","CONTRADICTS","REJECTED"),("CONTRADICTS","INSUFFICIENT","REJECTED"),
    ("INSUFFICIENT","CONSISTENT","UNRESOLVED"),("INSUFFICIENT","CONTRADICTS","REJECTED"),
    ("INSUFFICIENT","INSUFFICIENT","UNRESOLVED")])
def test_all_outcomes(pending,direct_vm,quote,context,verdict):
    mock(direct_vm,answer(quote,context))
    result=json.loads(pending.audit("0"))
    assert result["verdict"]==verdict
    row=json.loads(pending.get_citation("0"))
    assert row["assessment"]==result and row["state"]==verdict
    assert row["start"]==0 and row["end"]==len(QUOTE)
    assert direct_vm.run_validator() is True

@pytest.mark.parametrize("a,b,agree",[
    (("SUPPORTS","CONSISTENT"),("SUPPORTS","CONSISTENT"),True),
    (("SUPPORTS","CONTRADICTS"),("CONTRADICTS","CONSISTENT"),False),
    (("INSUFFICIENT","CONSISTENT"),("SUPPORTS","INSUFFICIENT"),False),
    (("SUPPORTS","CONSISTENT"),("SUPPORTS","CONTRADICTS"),False)])
def test_independent_meaning(pending,direct_vm,a,b,agree):
    mock(direct_vm,answer(*a)); pending.audit("0")
    mock(direct_vm,answer(*b,reason="Independent explanation."))
    assert direct_vm.run_validator() is agree

@pytest.mark.parametrize("raw",["{}","[]","null","bad",answer("BAD"),answer(context=""),answer(reason=""),answer(reason="x"*501)])
def test_invalid_model_retry(pending,direct_vm,raw):
    mock(direct_vm,raw)
    with direct_vm.expect_revert("assessment unavailable or invalid"):
        pending.audit("0")
    assert json.loads(pending.get_citation("0"))["state"]=="PENDING"
    mock(direct_vm); pending.audit("0")

def test_validator_fail_closed(pending,direct_vm):
    mock(direct_vm); pending.audit("0")
    assert direct_vm.run_validator(leader_result="{}") is False
    assert direct_vm.run_validator(leader_error=ValueError("provider unavailable")) is False
    mock(direct_vm,"broken"); assert direct_vm.run_validator() is False

@pytest.mark.parametrize("quote,start",[(QUOTE,1),(QUOTE,-1),(QUOTE,999),("invented",0),("",0),(" ",0),("x"*3001,0),(QUOTE,True)])
def test_bad_span(pending,direct_vm,quote,start):
    with direct_vm.expect_revert():
        pending.submit_citation("0",CLAIM,quote,start)
    assert pending.get_count()==1

@pytest.mark.parametrize("title,body",[("",BODY),("x"*161,BODY),("Title",""),("Title","x"*12001)])
def test_bad_document(contract,direct_vm,title,body):
    with direct_vm.expect_revert(): contract.register_document(title,body)
    assert contract.register_document("Title",BODY)=="0"

@pytest.mark.parametrize("claim",["", " ", "x"*2001])
def test_bad_claim(pending,direct_vm,claim):
    with direct_vm.expect_revert(): pending.submit_citation("0",claim,QUOTE,0)

def test_exact_unicode_offsets_and_repeat_quote(contract):
    body="\u00e9\U0001f600 abc abc"
    contract.register_document("Unicode",body)
    assert contract.submit_citation("0","abc","abc",7)=="0"
    row=json.loads(contract.get_citation("0"))
    assert row["start"]==7 and row["end"]==10
    assert json.loads(contract.get_document("0"))["body"]==body

def test_immutable_and_document_isolation(pending,direct_vm):
    pending.register_document("Another","A different document.")
    with direct_vm.expect_revert(): pending.submit_citation("1",CLAIM,QUOTE,0)
    mock(direct_vm); pending.audit("0")
    before=pending.get_citation("0")
    with direct_vm.expect_revert("not pending"): pending.audit("0")
    assert pending.get_citation("0")==before

def test_missing(contract,direct_vm):
    for fn,args in [(contract.get_document,["404"]),(contract.get_citation,["404"]),(contract.audit,["404"]),(contract.submit_citation,["404",CLAIM,QUOTE,0])]:
        with direct_vm.expect_revert(): fn(*args)
