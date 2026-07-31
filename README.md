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
KAANHA_PERCENTAGE=40
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
