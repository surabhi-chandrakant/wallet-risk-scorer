#!/usr/bin/env python3
"""
Wallet Risk Scoring System
Calculates risk scores (0-1000) for cryptocurrency wallets based on transaction history
"""

import os
import time
import json
import requests
import numpy as np
import pandas as pd
from tqdm import tqdm
from web3 import Web3
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import matplotlib.pyplot as plt 

# Load environment variables
load_dotenv()

# Configuration
class Config:
    INFURA_URL = f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}"
    ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
    INPUT_CSV = "data/Wallet_id.csv"
    OUTPUT_CSV = "data/wallet_risk_scores.csv"
    MAX_WORKERS = 10  # Number of parallel threads
    REQUEST_DELAY = 0.1  # Delay between API calls (seconds)
    MAX_RETRIES = 3  # Max retries for API calls
    TIMEOUT = 15  # API timeout in seconds

# Predefined DeFi contracts for faster lookup
DEFI_CONTRACTS = {
    '0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9',  # Aave
    '0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b',  # Compound
    '0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f',  # SushiSwap
    '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',  # Uniswap
    '0x1111111254fb6c44bac0bed2854e76f90643097d'   # 1inch
}

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(Config.INFURA_URL))

def fetch_transaction_data(wallet_address: str, action: str) -> List[Dict]:
    """Fetch transaction data from Etherscan with retry logic"""
    url = (
        f"https://api.etherscan.io/api?module=account&action={action}&"
        f"address={wallet_address}&startblock=0&endblock=99999999&"
        f"sort=asc&apikey={Config.ETHERSCAN_API_KEY}"
    )
    
    for attempt in range(Config.MAX_RETRIES):
        try:
            response = requests.get(url, timeout=Config.TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1':
                    return data['result']
            time.sleep(Config.REQUEST_DELAY)
        except requests.exceptions.RequestException:
            time.sleep(1)
    
    return []

def fetch_wallet_data(wallet_address: str) -> Tuple[List[Dict], List[Dict]]:
    """Fetch all transaction data for a wallet in parallel"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        native_txs = executor.submit(
            fetch_transaction_data,
            wallet_address,
            'txlist'
        )
        erc20_txs = executor.submit(
            fetch_transaction_data,
            wallet_address,
            'tokentx'
        )
        return native_txs.result(), erc20_txs.result()

def calculate_wallet_features(wallet_address: str) -> Dict:
    """Calculate all features for a single wallet"""
    native_txs, erc20_txs = fetch_wallet_data(wallet_address)
    all_txs = native_txs + erc20_txs
    
    # Basic metrics
    tx_count = len(all_txs)
    defi_interactions = sum(
        1 for tx in all_txs 
        if tx.get('to', '').lower() in DEFI_CONTRACTS
    )
    
    # Timing metrics
    if tx_count > 0:
        first_tx = int(all_txs[0]['timeStamp'])
        last_tx = int(all_txs[-1]['timeStamp'])
        age_days = (last_tx - first_tx) / 86400
        tx_freq = tx_count / age_days if age_days > 0 else 0
    else:
        age_days = 0
        tx_freq = 0
    
    # ETH balance
    try:
        balance = w3.eth.get_balance(Web3.to_checksum_address(wallet_address))
    except:
        balance = 0
    
    return {
        'wallet_id': wallet_address,
        'tx_count': tx_count,
        'defi_interactions': defi_interactions,
        'account_age_days': age_days,
        'tx_frequency': tx_freq,
        'balance_eth': float(Web3.from_wei(balance, 'ether')),
        'is_active': int(tx_count > 0)
    }

def normalize_features(features: Dict) -> Dict:
    """Normalize features to 0-1 scale"""
    return {
        'tx_volume': min(np.log1p(features['tx_count']) / 6, 1),
        'defi_usage': min(features['defi_interactions'] / 15, 1),
        'account_age': 1 - min(features['account_age_days'] / 730, 1),  # 2 year max
        'tx_freq': min(features['tx_frequency'] / 10, 1),
        'balance_risk': 1 - (min(features['balance_eth'], 10) / 10)
    }

def calculate_risk_score(normalized: Dict) -> int:
    """Calculate final risk score (0-1000)"""
    if not normalized.get('is_active', 1):
        return 0  # Inactive wallet
    
    behavior_score = (
        0.6 * normalized['defi_usage'] +
        0.4 * normalized['balance_risk']
    )
    
    activity_score = (
        0.4 * normalized['tx_volume'] +
        0.3 * normalized['tx_freq'] +
        0.3 * normalized['account_age']
    )
    
    risk_score = (0.6 * behavior_score + 0.4 * activity_score)
    return int(min(max(risk_score * 1000, 0), 1000))

def process_wallet(wallet_address: str) -> Dict:
    """Process a single wallet and return score"""
    try:
        features = calculate_wallet_features(wallet_address)
        normalized = normalize_features(features)
        score = calculate_risk_score(normalized)
        return {
            'wallet_id': wallet_address,
            'score': score,
            **features  # Include raw features for debugging
        }
    except Exception as e:
        print(f"\nError processing {wallet_address}: {str(e)}")
        return {
            'wallet_id': wallet_address,
            'score': 0,
            'error': str(e)
        }

def process_wallets_parallel(wallet_ids: List[str]) -> pd.DataFrame:
    """Process all wallets in parallel"""
    results = []
    
    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_wallet, wallet): wallet 
            for wallet in wallet_ids
        }
        
        for future in tqdm(
            as_completed(futures), 
            total=len(wallet_ids),
            desc="Processing Wallets",
            unit="wallet"
        ):
            results.append(future.result())
            time.sleep(Config.REQUEST_DELAY)
    
    return pd.DataFrame(results)

def analyze_results(df: pd.DataFrame):
    """Analyze and display score distribution"""
    print("\nScore Distribution Analysis:")
    print(df['score'].describe())
    
    # Plot histogram
    plt.figure(figsize=(10, 6))
    plt.hist(df['score'], bins=20, color='skyblue', edgecolor='black')
    plt.title("Wallet Risk Score Distribution", pad=20)
    plt.xlabel("Risk Score (0-1000)", labelpad=10)
    plt.ylabel("Number of Wallets", labelpad=10)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.show()

def save_sample_results(df: pd.DataFrame, n: int = 5):
    """Save sample results for verification"""
    sample = df.sample(n).sort_values('score', ascending=False)
    print("\nSample Results:")
    print(sample[['wallet_id', 'score']].to_string(index=False))
    
    # Save sample to file
    sample.to_csv("data/sample_results.csv", index=False)
    print("\nSaved sample results to data/sample_results.csv")

def main():
    """Main execution function"""
    try:
        print("Wallet Risk Scoring System")
        print("=" * 40)
        
        # Load wallet data
        wallets_df = pd.read_csv(Config.INPUT_CSV)
        wallet_ids = (
            wallets_df['wallet_id']
            .astype(str)
            .str.strip()
            .str.lower()
            .unique()
            .tolist()
        )
        print(f"\nLoaded {len(wallet_ids)} wallet addresses")
        
        # Process wallets
        start_time = time.time()
        risk_scores = process_wallets_parallel(wallet_ids)
        elapsed = time.time() - start_time
        
        print(f"\nProcessed {len(wallet_ids)} wallets in {elapsed:.2f} seconds")
        print(f"Average time per wallet: {elapsed/len(wallet_ids):.2f} seconds")
        
        # Analyze and save results
        analyze_results(risk_scores)
        save_sample_results(risk_scores)
        
        # Save full results
        risk_scores.to_csv(Config.OUTPUT_CSV, index=False)
        print(f"\nSaved full results to {Config.OUTPUT_CSV}")
        
    except Exception as e:
        print(f"\nError in main execution: {str(e)}")

if __name__ == "__main__":
    main()