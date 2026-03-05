import pytest
from unittest.mock import MagicMock, patch
from hexbytes import HexBytes

@pytest.fixture(autouse=True)
def mock_eth_dependencies():
    """
    Globally mocks Web3 and contract interactions for all tests.
    Ensures that any service initializing TrustService doesn't hit a real network.
    """
    with patch("api.v1.services.trust.Web3") as mock_web3:
        mock_w3 = mock_web3.return_value
        mock_w3.eth.get_transaction_count.return_value = 1
        mock_w3.eth.gas_price = 20000000000
        mock_w3.eth.wait_for_transaction_receipt.return_value = MagicMock(status=1)
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(raw_transaction=b"0x123")
        mock_w3.eth.send_raw_transaction.return_value = HexBytes("0xabcdef123456")
        
        # Mock contracts
        mock_contract = MagicMock()
        mock_contract.functions.registerAgent.return_value.build_transaction.return_value = {"to": "0x1"}
        mock_contract.functions.submitValidation.return_value.build_transaction.return_value = {"to": "0x2"}
        mock_contract.functions.getReputationScore.return_value.call.return_value = 100
        
        mock_w3.eth.contract.return_value = mock_contract
        
        yield mock_w3
