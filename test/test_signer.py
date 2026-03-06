import pytest
from core.signer import IntentSigner
from eth_account import Account
from hexbytes import HexBytes

def test_signer_initialization():
    signer = IntentSigner()
    assert signer.account.address is not None
    assert len(signer.private_key) > 0

def test_sign_trade_intent():
    signer = IntentSigner()
    agent_id = 1
    token_in = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    token_out = "0x4200000000000000000000000000000000000006"
    amount = 1000
    timestamp = 1715210000
    
    result = signer.sign_trade_intent(agent_id, token_in, token_out, amount, timestamp)
    
    assert "signature" in result
    assert result["message"]["agentId"] == agent_id
    assert result["message"]["tokenIn"] == token_in
    assert result["message"]["tokenOut"] == token_out
    assert result["signature"].startswith("0x")

def test_sign_trade_user_format():
    signer = IntentSigner()
    trade_intent = {
        "agentId": 1,
        "action": "BUY",
        "asset": "ETH",
        "amount": 10,
        "timestamp": 1715210000
    }
    
    signature = signer.sign_trade(trade_intent)
    
    assert signature.startswith("0x")
    assert len(signature) == 132

def test_sign_validation_artifact():
    signer = IntentSigner()
    agent_id = 1
    artifact_hash = "0x9ac4aa8c536a9ffb518cd288a809f87eeccb49f1ad9feb6e658e952e5c5bf2ae"
    
    signature = signer.sign_validation_artifact(agent_id, artifact_hash)
    
    assert signature.startswith("0x")
    assert len(signature) == 132 # 65 bytes + 0x prefix
