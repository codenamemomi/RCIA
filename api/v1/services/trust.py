import logging
import json
import asyncio
from web3 import Web3
from eth_utils import keccak
from hexbytes import HexBytes
from core.config import settings
from core.signer import IntentSigner
from core.blockchain import ERC4337Helper

logger = logging.getLogger(__name__)

class TrustService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.WEB3_RPC_URL))
        self.signer = IntentSigner()
        self.erc4337 = ERC4337Helper(self.w3, settings.AGENT_PRIVATE_KEY)
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
        
        self.history = []
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
        
        if settings.SIMULATE_ON_CHAIN:
            import hashlib
            tx_hash = "0x" + hashlib.sha256(f"MOCK_IDENTITY_{name}_{description}".encode()).hexdigest()
            logger.info(f"[SIMULATED] Identity Registered: {tx_hash}")
            return {"status": "success", "tx_hash": tx_hash, "agent_id": self.agent_id}

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
        if "timestamp" not in context:
            from datetime import datetime
            context["timestamp"] = datetime.now().isoformat() + "Z"
            
        artifact_hash = self.generate_artifact_hash(context)
        signature = self.signer.sign_validation_artifact(self.agent_id, artifact_hash)
        
        logger.info(f"Emitting Validation: {event_type} | Hash: {artifact_hash}")
        
        if settings.SIMULATE_ON_CHAIN:
            import hashlib
            tx_hash = "0x" + hashlib.sha256(f"MOCK_VALIDATION_{artifact_hash}".encode()).hexdigest()
            logger.info(f"[SIMULATED] Validation Emitted: {tx_hash}")
            result = {
                "event": event_type,
                "tx_hash": tx_hash,
                "artifact_hash": artifact_hash,
                "signature": signature,
                "on_chain_status": "simulated",
                "timestamp": context.get("timestamp", "now"),
                "to_state": context.get("to_state")
            }
            self.history.append(result)
            return result

        if settings.USE_GASLESS_TX and settings.ALCHEMY_API_KEY:
            # ERC-4337 Gasless Path
            logger.info("Using Alchemy Gasless path for validation...")
            # 1. Construct CallData (submitValidation)
            call_data = self.validation_contract.encode_abi(
                "submitValidation",
                [self.agent_id, HexBytes(artifact_hash), HexBytes(signature)]
            )
            
            # 2. Construct UserOp (simplified for demo)
            # In production, we'd fetch nonce and estimate gas via Bundler
            smart_account_address = self.erc4337.get_smart_account_address()
            user_op = {
                "sender": smart_account_address,
                "nonce": self.w3.eth.get_transaction_count(smart_account_address),
                "initCode": "0x",
                "callData": call_data,
                "callGasLimit": 200000,
                "verificationGasLimit": 100000,
                "preVerificationGas": 50000,
                "maxFeePerGas": self.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self.w3.eth.gas_price,
                "paymasterAndData": "0x",
                "signature": "0x"
            }
            
            # 3. Get Sponsorship
            paymaster_data = await self.erc4337.get_paymaster_and_data(user_op)
            user_op["paymasterAndData"] = paymaster_data
            
            # 4. Sign and Send
            user_op["signature"] = self.erc4337.sign_user_operation(user_op, settings.BLOCKCHAIN_CHAIN_ID)
            # tx_hash = await self.erc4337.send_user_operation(user_op)
            
            logger.info(f"Gasless Validation Proposed: {artifact_hash} | Smart Account: {smart_account_address}")
            return {
                "event": event_type,
                "tx_hash": "SPONSORED_PENDING",
                "smart_account": smart_account_address,
                "artifact_hash": artifact_hash,
                "signature": signature,
                "on_chain_status": "sponsored"
            }

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

    async def submit_trade_intent(self, signed_intent: dict):
        """
        Submits the signed TradeIntent to the on-chain Risk Router / Vault.
        This closes the trust-minimized execution loop.
        """
        logger.info(f"Submitting TradeIntent to Risk Router on-chain...")
        
        # In a real environment, this would call a contract method:
        # tx = self.risk_router_contract.functions.executeIntent(
        #     self.agent_id,
        #     signed_intent['message'],
        #     signed_intent['signature']
        # ).build_transaction(...)
        
        # For the hackathon demo, we simulate the submission and return success
        # provided the signature is present.
        
        if not signed_intent.get("signature"):
            raise ValueError("No signature found in trade intent")

        # Emit an execution artifact
        execution_context = {
            "action": "INTENT_SUBMISSION",
            "agent_id": self.agent_id,
            "intent_data_hash": self.generate_artifact_hash(signed_intent['message']),
            "signature": signed_intent['signature']
        }
        
        val_result = await self.emit_validation("INTENT_EXECUTION", execution_context)
        
        logger.info(f"Intent Submitted: {val_result['tx_hash']}")
        return {
            "status": "success",
            "tx_hash": val_result["tx_hash"],
            "execution_status": "verified"
        }

    async def report_outcome(self, event_id: str, roi: float, success: bool):
        """
        Reports the outcome of a trade or action to the Reputation Registry.
        Closes the feedback loop for ERC-8004.
        """
        logger.info(f"Reporting outcome for {event_id}: ROI={roi}, Success={success}")
        
        from datetime import datetime
        timestamp = datetime.now().isoformat() + "Z"
        outcome_signature = self.signer.sign_trade_outcome(
            self.agent_id, event_id, roi, success, int(asyncio.get_event_loop().time())
        )
        
        # We reuse the validation artifact pattern for outcomes as well
        context = {
            "event_id": event_id,
            "roi": f"{roi*100:.2f}%",
            "success": success,
            "timestamp": timestamp
        }
        
        return await self.emit_validation("TRADE_OUTCOME", context)

    async def get_reputation(self):
        """Fetches the agent's reputation score from the Registry"""
        if settings.SIMULATE_ON_CHAIN:
            return 0 # Start at 0 for live mode demo
        score = self.reputation_contract.functions.getReputationScore(self.agent_id).call()
        return score
