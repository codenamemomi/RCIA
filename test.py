from web3 import Web3
import os

WEB3_RPC_URL = os.getenv("WEB3_RPC_URL")

w3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))

print(w3.is_connected())
print(w3.eth.block_number)