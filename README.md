# RCIA (Real-world Capital Intelligence Agent)

RCIA is an autonomous, trust-minimized financial agent designed for mode-aware capital management. It leverages a sophisticated State Machine and the **ERC-8004** standard to provide verifiable, reputation-backed financial intelligence.

## 🚀 Key Features

- **Autonomous Mode-Aware Trading**:
  - **GROWTH**: Automated momentum-based trading (MA Fast/Slow crossover).
  - **DEFENSIVE**: Immediate risk-off transition and exit during high drawdown or market crashes.
  - **YIELD**: Optimizes passive income on idle capital through simulated on-chain yield parking.
  - **HEDGE**: Active protection strategies triggered during medium-to-high volatility.
- **Capital State Machine**: Automated transitions between modes based on real-time market metrics (Volatility, Drawdown, Momentum).
- **Embedded Risk Engine**:
  - **Volatility-Adjusted Sizing**: Automatically scales position sizes down during high-volatility periods.
  - **Performance Guards**: Hard stops for daily loss limits and max drawdown.
- **Robust Market Data**:
  - **Global Aggregator (CryptoCompare)**: Bypasses regional geo-blocking of major exchanges for reliable real-time data.
  - **Multi-Layer Fallback**: Seamlessly switches between Aggregator -> Exchange (CCXT) -> Mock Data for maximum demo uptime.
- **Alchemy Gasless Transactions (ERC-4337)**:
  - **Account Abstraction**: The agent uses a deterministic Smart Account for all on-chain operations.
  - **Sponsored Execution**: Seamlessly utilizes **Alchemy Gas Manager** to sponsor transaction fees, ensuring the agent is always liquid and ready to act.
- **Model Context Protocol (MCP)**:
  - **Direct AI Connectivity**: Exposes a real-time SSE endpoint for AI-to-AI interaction, providing tools for market evaluation, reputation checks, and status monitoring.
- **Hackathon Capital Vault & Risk Router**:
  - **Step 2 (Capital)**: Integrated on-chain funding via the Hackathon Capital Vault.
  - **Step 3 (Risk Router)**: Every trade intent is cryptographically signed and routed through the authorized Risk Router contract for enforced safety limits.
- **Simulated Trust Mode**: Toggle `SIMULATE_ON_CHAIN` for testing or switch to `False` for real sponsored on-chain actions via Alchemy.

## 📂 Project Structure

```text
RCIA/
├── api/
│   ├── db/                  # Database session & models
│   ├── utils/               # Shared utilities
│   └── v1/
│       ├── routes/          # API endpoints (FastAPI)
│       └── services/        # Business logic (Trading, Trust, Risk, Market Data)
├── core/
│   ├── abis/                # ERC-8004 Contract ABIs
│   ├── config.py            # Pydantic settings & ENV loading
│   ├── signer.py            # EIP-712 Structured Data Signer
│   └── state_machine.py     # Capital State Machine logic
├── scripts/                 # Utility & Verification scripts
├── test/                    # Unit, Integration & Stability tests
├── .env.example             # Environment template
├── main.py                  # App entry point
└── requirements.txt         # Project dependencies
```

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (for Celery background tasks)

### Installation

1. **Clone & Enter**:

    ```bash
    git clone https://github.com/codenamemomi/RCIA
    cd RCIA
    ```

2. **Environment Setup**:

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    ```

3. **Configure .env**:
    - `MOCK_MARKET_DATA=False`: Enables real-time price data (Aggregator).
    - `SIMULATE_ON_CHAIN=True`: Bypasses real gas fees for on-chain DECISION artifacts.
    - `AGENT_PRIVATE_KEY`: Your agent's unique signing identity.

4. **Run Application**:

    ```bash
    uvicorn main:app --reload
    ```

## 🧪 Testing & Verification

RCIA includes a comprehensive test suite for stability and trust verification.

```bash
# Run all tests (Unit + Integration + Stability)
./venv/bin/pytest

# Verify Aggregator Integration
./venv/bin/python /tmp/test_cryptocompare.py
```

- **Losing Streak Simulation**: Verifies state transitions under performance pressure.
- **RPC Failure Simulation**: Tests agent resilience against network connectivity issues.

## 📜 Documentation

- [ERC-8004 Integration Guide](ERC8004_INTEGRATION_GUIDE.md) - Deep dive into trust layer architecture.
- [Development Steps](DEVELOPMENT_STEPS.md) - History of Phase implementation.
- [Project Walkthrough](file:///home/codenamemomi/.gemini/antigravity/brain/76a08297-6768-494a-9410-f1fca8cd1f5b/walkthrough.md) - Detailed breakdown of recent enhancements.
