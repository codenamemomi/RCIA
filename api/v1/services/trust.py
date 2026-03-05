import logging
import json
import asyncio
from web3 import Web3
from eth_utils import keccak
from hexbytes import HexBytes
from core.config import settings
from core.signer import IntentSigner

logger = logging.getLogger(__name__)

class TrustService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.WEB3_RPC_URL))
        self.signer = IntentSigner()
        self.agent_id = settings.AGENT_ID
        
        # Load ABIs
        with open("core/abis/IdentityRegistry.json", "r") as f:
            self.identity_abi = json.load(f)
        with open("core/abis/ValidationRegistry.json", "r") as f:
            self.validation_abi = json.load(f)
        with open("core/abis/ReputationRegistry.json", "r") as f:
            self.reputation_abi = json.load(f)
            
        self.identity_contract = self.w3.eth.contract(
            address=settings.ERC8004_IDENTITY_REGISTRY, 
            abi=self.identity_abi
        )
        self.validation_contract = self.w3.eth.contract(
            address=settings.ERC8004_VALIDATION_REGISTRY, 
            abi=self.validation_abi
        )
        self.reputation_contract = self.w3.eth.contract(
            address=settings.ERC8004_REPUTATION_REGISTRY, 
            abi=self.reputation_abi
        )
        
        logger.info(f"TrustService initialized (Agent ID: {self.agent_id})")

    def generate_artifact_hash(self, context: dict) -> str:
        """Serializes context and returns its Keccak-256 hash"""
        artifact_json = json.dumps(context, sort_keys=True)
        artifact_hash = keccak(text=artifact_json)
        return "0x" + artifact_hash.hex()

    async def register_identity(self, name: str, description: str):
        """
        Registers the agent identity on-chain.
        Note: Requires the signer account to have gas funds.
        """
        logger.info(f"Registering identity: {name} on-chain...")
        
        account = self.signer.account
        nonce = self.w3.eth.get_transaction_count(account.address)
        
        tx = self.identity_contract.functions.registerAgent(
            name, description
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 200000, # Estimated
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.signer.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Identity Registered: {tx_hash.hex()} | Status: {receipt.status}")
        
        return {"status": "success", "tx_hash": tx_hash.hex(), "agent_id": self.agent_id}

    async def emit_validation(self, event_type: str, context: dict):
        """
        Generates, signs, and submits a validation artifact to the on-chain Registry.
        """
        artifact_hash = self.generate_artifact_hash(context)
        signature = self.signer.sign_validation_artifact(self.agent_id, artifact_hash)
        
        logger.info(f"Emitting Validation: {event_type} | Hash: {artifact_hash}")
        
        account = self.signer.account
        nonce = self.w3.eth.get_transaction_count(account.address)
        
        tx = self.validation_contract.functions.submitValidation(
            self.agent_id, 
            HexBytes(artifact_hash), 
            HexBytes(signature)
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 150000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.signer.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return {
            "event": event_type,
            "tx_hash": tx_hash.hex(),
            "artifact_hash": artifact_hash,
            "signature": signature,
            "on_chain_status": "submitted"
        }

    async def report_outcome(self, event_id: str, roi: float, success: bool):
        """
        Reports the outcome of a trade or action to the Reputation Registry.
        Closes the feedback loop for ERC-8004.
        """
        logger.info(f"Reporting outcome for {event_id}: ROI={roi}, Success={success}")
        
        timestamp = int(asyncio.get_event_loop().time()) # Simplified timestamp
        outcome_signature = self.signer.sign_trade_outcome(
            self.agent_id, event_id, roi, success, timestamp
        )
        
        # We reuse the validation artifact pattern for outcomes as well
        # In a more specialized implementation, this might call a specific contract method
        context = {
            "event_id": event_id,
            "roi": roi,
            "success": success,
            "timestamp": timestamp
        }
        
        return await self.emit_validation("TRADE_OUTCOME", context)

    async def get_reputation(self):
        """Fetches the agent's reputation score from the Registry"""
        score = self.reputation_contract.functions.getReputationScore(self.agent_id).call()
        return score
