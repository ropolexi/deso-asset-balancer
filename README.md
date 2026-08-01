# DeSo Asset Balancer

A Python application that automatically balances a portfolio across **DeSo (DESO)**, **USDC**, **FOCUS** and **OPENFUND**.

## Features

* Balance holdings between DESO, USDC, FOCUS and OPENFUND
* Calculate required buy/sell amounts

## Supported Assets

| Asset | Description                  |
| ----- | ---------------------------- |
| DESO  | Native DeSo blockchain token |
| USDC  | USD Coin stablecoin          |
| FOCUS | FOCUS token                  |
| OPENFUND | OPENFUND token                  |

## Requirements

* Python 3.10+
* pip

## Installation

Clone the repository:

```bash
git clone https://github.com/ropolexi/deso-asset-balancer.git
cd deso-asset-balancer
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

**Linux / macOS**

```bash
source .venv/bin/activate
```

**Windows**

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```env
DESO_SEED="your_deso_seed"
UPDATE_INTERVAL=600
NODE="https://node.deso.org"

DESO_PERCENTAGE=20
FOCUS_PERCENTAGE=6.2
OPENFUND_PERCENTAGE=6.2

HARD_CAP = 30 # max asset $ value per token to keep
DEVIATION=1 #how much % difference before triggering BUY/SELL to avoid small rapid fluctuations
TOKENS_BASED_ON_FOCUS = [{"name":"Kaanha","pubkey":"BC1YLhvxVMEUp5y8zpq17VaRE264JX4r4T4XU4Ff8NJ4MrchkGDq4q3","target_percentage":42},{"name":"Arnoud","pubkey":"BC1YLgBND6GqfWYb8HyY3hAm2UpT8aeFv2fX41sMPAu7uuVjuSQtDju","target_percentage":3},{"name":"SeanSlater","pubkey":"BC1YLirtb7CjNwVmWEt7t1487Qpo4LoPBDEGvfqYwXXZcj2dDLNMBVU","target_percentage":3}]
BALANCER_ACTIVE=False
PRINT_DEBUG=False
```

## Usage

Run the application:

```bash
python balancer.py
```

## How It Works

1. Retrieve current balances.
2. Fetch current market prices.
3. Calculate the total portfolio value.
4. Compare the current allocation against the target allocation.
5. Determine the required buy/sell amounts.
6. Execute or display the rebalance plan.

## Project Structure

```text
.
├── balancer.py
├── requirements.txt
├── .env
└── README.md
```


## Safety

Before enabling automatic trading:

* Verify your seed credentials.
* Test using small balances.
* Review the calculated trades.
* Keep your seed secure.
* Never commit your `.env` file to version control.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request with improvements or bug fixes.

## License

This project is licensed under the MIT License.
