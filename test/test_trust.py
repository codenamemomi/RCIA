import pytest
import json
from api.v1.services.trust import TrustService

def test_generate_artifact_hash():
    # We need to mock the __init__ to avoid ABI loading if needed, 
    # but here we can just let it run if ABIs exist.
    trust = TrustService()
    context = {"test": "data", "value": 123}
    
    hash1 = trust.generate_artifact_hash(context)
    hash2 = trust.generate_artifact_hash({"value": 123, "test": "data"}) # Different order
    
    assert hash1.startswith("0x")
    assert len(hash1) == 66
    assert hash1 == hash2 # Canonicalization check

@pytest.mark.asyncio
async def test_emit_validation():
    trust = TrustService()
    context = {"event": "test"}
    
    result = await trust.emit_validation("TEST_EVENT", context)
    
    assert result["event"] == "TEST_EVENT"
    assert "artifact_hash" in result
    assert "signature" in result
    assert result["on_chain_status"] in ["submitted", "simulated"]
    assert "tx_hash" in result

@pytest.mark.asyncio
async def test_get_reputation():
    trust = TrustService()
    score = await trust.get_reputation()
    # In simulation it's 0 (start), in live it's the on-chain score
    assert score >= 0


