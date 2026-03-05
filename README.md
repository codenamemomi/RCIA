# RCIA (Real-world Capital Intelligence Agent)

RCIA is an autonomous, trust-minimized financial agent designed for mode-aware capital management. It leverages a sophisticated State Machine and the **ERC-8004** standard to provide verifiable, reputation-backed financial intelligence.

## 🚀 Key Features

- **Autonomous Mode-Aware Trading**:
  - **GROWTH**: Automated momentum-based trading (MA Fast/Slow crossover).
  - **DEFENSIVE**: Immediate risk-off transition and exit during high drawdown or market crashes.
  - **YIELD**: Optimizes passive income on idle capital through specialized stablecoin allocation.
  - **HEDGE**: Active protection strategies triggered during medium-to-high volatility.
- **Capital State Machine**: Automated transitions between modes based on real-time market metrics (Volatility, Drawdown, Momentum).
- **ERC-8004 Trust Integration**:
  - **On-chain Identity**: Verifiable agent registration on the ERC-8004 Identity Registry.
  - **Validation Artifacts**: Every key decision (trade signals, mode transitions) generates a cryptographically signed EIP-712 artifact.
  - **Reputation Feedback Loop**: Closed-loop reporting of trade outcomes (ROI/Success) to maintain an on-chain reputation score.
- **Risk Management Engine**: Embedded risk checks ensuring all trades comply with daily loss limits, max exposure, and drawdown thresholds.

## 📂 Project Structure

```text
RCIA/
├── api/
│   ├── db/                  # Database session & models
│   ├── utils/               # Shared utilities
│   └── v1/
│       ├── routes/          # API endpoints (FastAPI)
│       └── services/        # Business logic (Trading, Trust, Risk, etc.)
├── core/
│   ├── abis/                # ERC-8004 Contract ABIs
│   ├── config.py            # Pydantic settings & ENV loading
│   ├── signer.py            # EIP-712 Structured Data Signer
│   └── state_machine.py     # Capital State Machine logic
├── scripts/                 # Utility & Verification scripts
├── test/                    # Unit & Integration tests (Pytest)
├── .env.example             # Environment template
├── ERC8004_INTEGRATION_GUIDE.md
├── main.py                  # App entry point & lifespan management
└── requirements.txt         # Project dependencies
```

- `api/v1/services/`: Core business logic (Trading, Trust, Risk, Yield, Hedge, Market Data).
- `core/`:
  - `state_machine.py`: The logic for agent mode transitions.
  - `signer.py`: EIP-712 structured data signing for ERC-8004 compliance.
  - `abis/`: JSON ABIs for ERC-8004 Registry contracts.
- `scripts/`: Implementation verification and utility scripts.
- `test/`: Comprehensive test suite including unit, integration, and mock on-chain testing.

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (for Celery background tasks)

### Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/codenamemomi/RCIA
    cd RCIA
    ```

2. **Create and activate a virtual environment**:

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Environment Configuration**:
    Copy the example environment file and update your secrets:

    ```bash
    cp .env.example .env
    ```

    *Note: Ensure `AGENT_PRIVATE_KEY` is a valid 32-byte hex string for ERC-8004 signing.*

5. **Run the Application**:

    ```bash
    uvicorn main:app --reload
    ```

## 🧪 Testing

RCIA uses `pytest` with a global mocking strategy for blockchain interactions.

```bash
# Run all tests
pytest test/

# Run specific trust layer verification
python scripts/test_live_logic.py
```

## 📜 Documentation

- [ERC-8004 Integration Guide](ERC8004_INTEGRATION_GUIDE.md) - Deep dive into the trust layer architecture.
- [Development Steps](DEVELOPMENT_STEPS.md) - History of Phase implementation.
