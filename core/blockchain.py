import logging
import json
from typing import Dict, Any, Optional
from eth_account import Account
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from web3 import Web3
from eth_utils import keccak
from core.config import settings

logger = logging.getLogger(__name__)

class ERC4337Helper:
    def __init__(self, w3: Web3, signer_key: str):
        self.w3 = w3
        self.signer = Account.from_key(signer_key)
        self.entry_point_address = settings.ERC4337_ENTRY_POINT
        
    def get_user_op_hash(self, user_op: Dict[str, Any], chain_id: int) -> bytes:
        """Calculates the UserOperation hash for signing."""
        # Simple implementation for v0.6 UserOp hashing
        # In a full implementation, we'd use encode_abi for all fields
        # This is a placeholder for the logic handled by bundlers usually
        encoded_op = self.w3.codec.encode(
            "(address,uint256,bytes,bytes,uint256,uint256,uint256,uint256,uint256,bytes,bytes)",
            [
                user_op['sender'],
                user_op['nonce'],
                HexBytes(user_op['initCode']),
                HexBytes(user_op['callData']),
                user_op['callGasLimit'],
                user_op['verificationGasLimit'],
                user_op['preVerificationGas'],
                user_op['maxFeePerGas'],
                user_op['maxPriorityFeePerGas'],
                HexBytes(user_op['paymasterAndData']),
                HexBytes("0x") # Signature placeholder
            ]
        )
        op_hash = keccak(encoded_op)
        
        # Hash with EntryPoint and ChainID
        final_hash = keccak(self.w3.codec.encode(
            "(bytes32,address,uint256)",
            [op_hash, self.entry_point_address, chain_id]
        ))
        return final_hash

    async def get_paymaster_and_data(self, user_op: Dict[str, Any]) -> str:
        """Requests paymasterAndData from Alchemy Gas Manager."""
        if not settings.ALCHEMY_API_KEY or not settings.ALCHEMY_POLICY_ID:
            logger.warning("Alchemy credentials missing. Falling back to empty paymasterAndData.")
            return "0x"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_requestPaymasterAndData",
            "params": [
                {
                    "policyId": settings.ALCHEMY_POLICY_ID,
                    "entryPoint": self.entry_point_address,
                    "userOperation": {
                        "sender": user_op["sender"],
                        "nonce": hex(user_op["nonce"]),
                        "initCode": user_op["initCode"],
                        "callData": user_op["callData"],
                        "callGasLimit": hex(user_op["callGasLimit"]),
                        "verificationGasLimit": hex(user_op["verificationGasLimit"]),
                        "preVerificationGas": hex(user_op["preVerificationGas"]),
                        "maxFeePerGas": hex(user_op["maxFeePerGas"]),
                        "maxPriorityFeePerGas": hex(user_op["maxPriorityFeePerGas"]),
                        "paymasterAndData": "0x",
                        "signature": "0x"
                    }
                }
            ]
        }
        
        # Internal call to Alchemy
        import httpx
        url = f"{settings.ALCHEMY_BUNDLER_URL}{settings.ALCHEMY_API_KEY}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                if "result" in result:
                    return result["result"].get("paymasterAndData", "0x")
            
        logger.error(f"Alchemy paymaster request failed: {resp.text}")
        return "0x"

    def sign_user_operation(self, user_op: Dict[str, Any], chain_id: int) -> str:
        """Signs the UserOperation with the signer's private key."""
        op_hash = self.get_user_op_hash(user_op, chain_id)
        # EntryPoint expects a simple signature of the hash
        signed = self.signer.sign_message(encode_defunct(primitive=op_hash))
        return "0x" + signed.signature.hex()

    def get_smart_account_address(self, salt: Optional[int] = None) -> str:
        """
        Calculates the deterministic address of the LightAccount smart account.
        This uses CREATE2-style logic (simplified for placeholder).
        """
        # For the hackathon, we'll return a deterministic address derived from the signer
        # In a real setup, this would use the Factory contract address and initCode
        actual_salt = salt if salt is not None else settings.ERC4337_ACCOUNT_SALT
        combined = f"{settings.ERC4337_ACCOUNT_PREFIX}_{self.signer.address}_{actual_salt}".encode()
        addr_hash = keccak(combined)
        return Web3.to_checksum_address("0x" + addr_hash.hex()[-40:])

    async def send_user_operation(self, user_op: Dict[str, Any]) -> str:
        """Sends UserOperation to Alchemy Bundler."""
        if not settings.ALCHEMY_API_KEY:
             raise ValueError("ALCHEMY_API_KEY is required for bundler submission")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_sendUserOperation",
            "params": [user_op, self.entry_point_address]
        }
        
        import httpx
        url = f"{settings.ALCHEMY_BUNDLER_URL}{settings.ALCHEMY_API_KEY}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                if "result" in result:
                    return result["result"] # This is the userOpHash
                if "error" in result:
                    raise Exception(f"Bundler error: {result['error']}")
            
        raise Exception(f"Alchemy bundler request failed: {resp.text}")
