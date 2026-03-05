import logging
from eth_account import Account
from eth_account.messages import encode_typed_data
from hexbytes import HexBytes
from web3 import Web3
from core.config import settings

logger = logging.getLogger(__name__)

class IntentSigner:
    def __init__(self):
        self.private_key = settings.AGENT_PRIVATE_KEY
        if self.private_key == "0x...":
            logger.warning("AGENT_PRIVATE_KEY is not set. Signing will fail.")
        self.account = Account.from_key(self.private_key)
        logger.info(f"IntentSigner initialized for account: {self.account.address}")

    def get_domain_data(self, contract_address: str = None):
        target_addr = contract_address or settings.ERC8004_VALIDATION_REGISTRY
        if target_addr and target_addr.startswith("0x") and len(target_addr) == 42:
            target_addr = Web3.to_checksum_address(target_addr)
            
        return {
            "name": "RCIA-Trust-Layer",
            "version": "1",
            "chainId": settings.BLOCKCHAIN_CHAIN_ID,
            "verifyingContract": target_addr
        }

    def sign_trade_intent(self, agent_id: int, action: str, amount: int, timestamp: int):
        """Signs a TradeIntent structured data packet using EIP-712"""
        domain_data = self.get_domain_data()
        
        types = {
            "TradeIntent": [
                {"name": "agentId", "type": "uint256"},
                {"name": "action", "type": "string"},
                {"name": "amount", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"}
            ]
        }
        
        message = {
            "agentId": agent_id,
            "action": action,
            "amount": amount,
            "timestamp": timestamp
        }
        
        structured_data = encode_typed_data(self.get_domain_data(), types, message)
        signed_message = self.account.sign_message(structured_data)
        
        return {
            "signature": "0x" + signed_message.signature.hex(),
            "message": message,
            "domain": self.get_domain_data()
        }

    def sign_trade_outcome(self, agent_id: int, event_id: str, roi: float, success: bool, timestamp: int):
        """Signs a TradeOutcome packet to close the reputation loop"""
        types = {
            "TradeOutcome": [
                {"name": "agentId", "type": "uint256"},
                {"name": "eventId", "type": "string"},
                {"name": "roi", "type": "string"}, # Using string for float precision safety in structured data
                {"name": "success", "type": "bool"},
                {"name": "timestamp", "type": "uint256"}
            ]
        }
        
        message = {
            "agentId": agent_id,
            "eventId": event_id,
            "roi": str(roi),
            "success": success,
            "timestamp": timestamp
        }
        
        structured_data = encode_typed_data(
            self.get_domain_data(settings.ERC8004_REPUTATION_REGISTRY), 
            types, 
            message
        )
        signed_message = self.account.sign_message(structured_data)
        
        return {
            "signature": "0x" + signed_message.signature.hex(),
            "message": message
        }

    def sign_validation_artifact(self, agent_id: int, artifact_hash: str):
        """Signs the hash of a validation artifact for on-chain submission"""
        # Note: Usually on-chain we might sign the hash itself or use another EIP-712 type
        # For ERC-8004, we sign the artifact hash
        
        # Ensure hash is in bytes
        if isinstance(artifact_hash, str) and artifact_hash.startswith("0x"):
            artifact_hash_bytes = HexBytes(artifact_hash)
        else:
            artifact_hash_bytes = HexBytes(artifact_hash)
            
        signed_message = self.account.sign_message(encode_typed_data(
            self.get_domain_data(),
            {"Validation": [{"name": "agentId", "type": "uint256"}, {"name": "artifactHash", "type": "bytes32"}]},
            {"agentId": agent_id, "artifactHash": artifact_hash_bytes}
        ))
        
        return "0x" + signed_message.signature.hex()
