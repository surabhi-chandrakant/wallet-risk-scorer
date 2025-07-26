# 🧠 Wallet Risk Scorer

A Python-based system to **score Ethereum wallets** on a scale of **0 to 1000** based on their **on-chain behavior**, using transaction data fetched from **Etherscan** and **Infura (Web3)**.

This tool is useful for **DeFi credit scoring**, **wallet profiling**, and **risk analysis** in decentralized financial systems.

---

## 🚀 What It Does

The system performs the following steps:

1. **Reads a list of wallet addresses** from a CSV file.
2. Fetches each wallet's:
   - Native ETH transactions
   - ERC-20 token transfers
3. Calculates behavioral and activity-based features:
   - Total transactions
   - Interactions with DeFi contracts
   - Age of the wallet
   - Transaction frequency
   - ETH balance
4. **Normalizes** the data to standard scales.
5. Calculates a **final risk score** (0–1000) using weighted logic.
6. Saves:
   - Full results in `wallet_risk_scores.csv`
   - A sample analysis with a histogram of score distribution.

---

## 📊 Sample Output Format

Here is a preview of the output file:

| wallet_id | score | tx_count | defi_interactions | account_age_days | tx_frequency | balance_eth | is_active |
|-----------|-------|----------|--------------------|------------------|--------------|-------------|-----------|
| 0x0039f... | 776   | 4081     | 35                 | 2972.85          | 1.37         | 0.0         | 1         |
| 0x06b51... | 522   | 4        | 0                  | 0.00489          | 817.02       | 0.0         | 1         |
| ...       | ...   | ...      | ...                | ...              | ...          | ...         | ...       |

---

## 📁 Folder Structure

wallet-risk-scorer/
│
├── data/
│ ├── Wallet_id.csv # Input list of wallet addresses
│ ├── wallet_risk_scores.csv # Output: Full result with scores
│ └── sample_results.csv # Output: Sample score results
│
├── .gitignore
├── readme.md
├── requirements.txt
└── risk_scorer.py # Main logic script


---

## ⚙️ How It Works (Logic Breakdown)

### ✅ `calculate_wallet_features(wallet)`
- Counts total transactions
- Detects known DeFi contract interactions (e.g., Aave, Uniswap)
- Measures account age (in days)
- Estimates transaction frequency
- Fetches current ETH balance

### ✅ `normalize_features(features)`
- Applies scaling to values:
  - Log-scale for `tx_count`
  - Cap and normalize `defi_interactions`
  - Invert `account_age` (newer = riskier)
  - Normalize `tx_freq` and `balance_eth`

### ✅ `calculate_risk_score(normalized)`
- Computes:
  - **Behavior Score** = 60% DeFi usage + 40% balance risk
  - **Activity Score** = 40% tx volume + 30% tx freq + 30% account age
  - **Risk Score** = 60% behavior + 40% activity
- Final score range: **0 to 1000**

---


## Output Format Explanation

The system generates a CSV file with the following columns:

| Column | Description | Example Value |
|--------|-------------|---------------|
| `wallet_id` | Ethereum wallet address | `0x13b1c8b0e696aff8b4fee742119b549b605f3cbc` |
| `score` | Risk score (0-1000) where:<br>• 0-300: Low risk<br>• 300-600: Medium risk<br>• 600-1000: High risk | `522` |
| `tx_count` | Total number of transactions (both native and ERC20) | `4` |
| `defi_interactions` | Number of transactions with known DeFi protocols (Aave, Compound, etc.) | `35` |
| `account_age_days` | Wallet age in days (time between first and last transaction) | `2972.85` |
| `tx_frequency` | Average transactions per day (tx_count/account_age_days) | `817.02` |
| `balance_eth` | Current ETH balance in the wallet | `0` |
| `is_active` | Binary flag (0=inactive, 1=active wallet with transactions) | `1` |

### How Scores Are Calculated

The risk score (0-1000) is computed using these weighted factors:

1. **DeFi Usage (40%)**:
   - More interactions with DeFi protocols → Higher risk
   - Normalized by: `min(defi_interactions / 15, 1)`

2. **Transaction Volume (30%)**:
   - More transactions → Higher risk
   - Logarithmic scaling: `log(tx_count + 1) / 6`

3. **Activity Patterns (20%)**:
   - Newer wallets (account_age < 2 years) → Higher risk
   - High frequency transactions → Higher risk
   - Formula: `0.3*frequency_score + 0.7*age_score`

4. **Balance (10%)**:
   - Lower balances → Slightly higher risk
   - Normalized: `1 - (min(balance, 10) / 10)`

### Interpreting Your Results

1. **High Risk (600-1000)**:
   - Example: `0x003...` (Score: 776)
   - Characteristics: 4000+ transactions, 35 DeFi interactions, active for 8+ years

2. **Medium Risk (300-600)**:
   - Example: `0x06b...` (Score: 522)
   - Characteristics: Few transactions but very high frequency (817/day)

3. **Low Risk (0-300)**:
   - Example: `0x13b...` (Score: 0)
   - Characteristics: No transaction history (inactive wallet)

### Notes

- Wallets with `is_active=0` receive base scores (0-300)
- Extremely high transaction frequencies (>1000/day) may indicate bot activity
- DeFi interactions have the highest impact on scores
- Zero-balance wallets get a small risk boost (5-10 points)

## 🧪 Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/surabhi-chandrakant/wallet-risk-scorer.git
cd wallet-risk-scorer

### 2.pip install -r requirements.txt


### 3. Create .env File
Create a .env file in the root directory:

INFURA_API_KEY=your_infura_project_id
ETHERSCAN_API_KEY=your_etherscan_api_key