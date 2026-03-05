import asyncio
import unittest
from unittest.mock import MagicMock, patch
from api.v1.services.trust import TrustService
from core.signer import IntentSigner
from hexbytes import HexBytes

class TestERC8004Live(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Web3 and Contracts
        self.mock_w3 = MagicMock()
        self.mock_w3.eth.get_transaction_count.return_value = 1
        self.mock_w3.eth.gas_price = 20000000000
        self.mock_w3.eth.wait_for_transaction_receipt.return_value = MagicMock(status=1)
        self.mock_w3.eth.account.sign_transaction.return_value = MagicMock(rawTransaction=b"0x123")
        self.mock_w3.eth.send_raw_transaction.return_value = HexBytes("0xabcdef123456")

        # Mock contract methods
        self.mock_contract = MagicMock()
        self.mock_contract.functions.registerAgent.return_value.build_transaction.return_value = {"to": "0x1"}
        self.mock_contract.functions.submitValidation.return_value.build_transaction.return_value = {"to": "0x2"}
        self.mock_contract.functions.getReputationScore.return_value.call.return_value = 150

        patcher = patch('api.v1.services.trust.Web3', return_value=self.mock_w3)
        self.addCleanup(patcher.stop)
        self.mock_web3_class = patcher.start()

    async def test_live_registration(self):
        # We need to mock the contract creation inside TrustService
        with patch('api.v1.services.trust.TrustService.__init__', return_value=None):
            trust = TrustService()
            trust.w3 = self.mock_w3
            trust.signer = IntentSigner()
            trust.agent_id = 1
            trust.identity_contract = self.mock_contract
            
            result = await trust.register_identity("TestAgent", "TestDesc")
            print(f"Registration Result: {result}")
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["tx_hash"], "abcdef123456") # HexBytes.hex() returns hex without 0x prefix

    async def test_reputation_loop(self):
        with patch('api.v1.services.trust.TrustService.__init__', return_value=None):
            trust = TrustService()
            trust.w3 = self.mock_w3
            trust.signer = IntentSigner()
            trust.agent_id = 1
            trust.validation_contract = self.mock_contract
            
            # This calls emit_validation internally
            result = await trust.report_outcome("TRADE_BTC_123", 0.05, True)
            print(f"Outcome Report Result: {result}")
            self.assertEqual(result["on_chain_status"], "submitted")
            self.assertEqual(result["event"], "TRADE_OUTCOME")

if __name__ == "__main__":
    unittest.main()
