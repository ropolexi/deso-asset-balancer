from deso_sdk import DeSoDexClient,base58_check_encode
import time
import os
from dotenv import load_dotenv

deso_pubkey="DESO"
focus_pubkey="BC1YLjEayZDjAPitJJX4Boy7LsEfN3sWAkYb3hgE9kGBirztsc2re1N"
openfund_pubkey="BC1YLj3zNA7hRAqBVkvsTeqw7oi4H6ogKiAFL1VXhZy6pYeZcZ6TDRY"
usdc_pubkey="BC1YLiwTN3DbkU8VmD7F7wXcRR1tFX6jDEkLyruHD2WsH3URomimxLX"
openfund_pubkey="BC1YLj3zNA7hRAqBVkvsTeqw7oi4H6ogKiAFL1VXhZy6pYeZcZ6TDRY"
load_dotenv()

deso_seed = os.getenv("DESO_SEED")
update_interval = int(os.getenv("UPDATE_INTERVAL"))

deso = DeSoDexClient(is_testnet=False,seed_phrase_or_hex=deso_seed,node_url="https://node.deso.org")
user_public_key=base58_check_encode(deso.deso_keypair.public_key, False)

def get_exchange_rate(data,quote_currency,base_currency_selected):    
    orders=data["Orders"]

    bids = []
    asks = []

    bids_1 = [(float(order['ExchangeRateCoinsToSellPerCoinToBuy']), float(order['QuantityToFill'])*float(order['ExchangeRateCoinsToSellPerCoinToBuy']),order['TransactorPublicKeyBase58Check']) for order in orders if (order['OperationType'] == 'BID' and order['BuyingDAOCoinCreatorPublicKeyBase58Check']==base_currency_selected)]
    bids_2 = [(float(order['ExchangeRateCoinsToSellPerCoinToBuy']), float(order['QuantityToFill']),order['TransactorPublicKeyBase58Check']) for order in orders if (order['OperationType'] == 'ASK' and order['SellingDAOCoinCreatorPublicKeyBase58Check']==quote_currency)]
    bids = bids_1 + bids_2
    asks_1 = [(1.0/float(order['ExchangeRateCoinsToSellPerCoinToBuy']), float(order['QuantityToFill']),order['TransactorPublicKeyBase58Check']) for order in orders if (order['OperationType'] == 'BID' and order['BuyingDAOCoinCreatorPublicKeyBase58Check']==quote_currency)]
    asks_2 = [(1.0/float(order['ExchangeRateCoinsToSellPerCoinToBuy']), float(order['QuantityToFill'])*(1.0/float(order['ExchangeRateCoinsToSellPerCoinToBuy'])),order['TransactorPublicKeyBase58Check']) for order in orders if (order['OperationType'] == 'ASK' and order['SellingDAOCoinCreatorPublicKeyBase58Check']==base_currency_selected)]
    asks = asks_1+asks_2

    best_bid_price, best_bid_quantity,best_bid_trasactor = max(bids)
    print(f"best_bid_price:{best_bid_price}")
    best_ask_price, best_ask_quantity,best_ask_trasactor = min(asks)
    print(f"best_ask_price:{best_ask_price}")

    return (float(best_bid_price)+float(best_ask_price))/2

def get_user_balance(deso_exchange_rate,focus_exchange_rate,openfund_exchange_rate):
    res=deso.get_token_balances(
        user_public_key=user_public_key,
        creator_public_keys=[deso_pubkey,
                                focus_pubkey,
                                usdc_pubkey,
                                openfund_pubkey]
        )

    deso_coins=deso.base_units_to_coins(float(res["Balances"][deso_pubkey]["BalanceBaseUnits"]),True)
    usdc_coins=deso.base_units_to_coins(float(res["Balances"][usdc_pubkey]["BalanceBaseUnits"]),False)
    focus_coins= deso.base_units_to_coins(float(res["Balances"][focus_pubkey]["BalanceBaseUnits"]),False)
    openfund_coins = deso.base_units_to_coins(float(res["Balances"][openfund_pubkey]["BalanceBaseUnits"]),False)

    deso_balance_usd = deso_coins * deso_exchange_rate
    focus_balance_usd = focus_coins * focus_exchange_rate * deso_exchange_rate
    openfund_balance_usd = openfund_coins * openfund_exchange_rate * deso_exchange_rate

    return usdc_coins,deso_balance_usd,focus_balance_usd,openfund_balance_usd

def place_limit_order(user_public_key,operation, base_currency, quote_currency, price, quantity):
    try:
        response = deso.create_limit_order_with_fee(
            transactor_public_key=user_public_key,
            quote_currency_public_key=quote_currency,
            base_currency_public_key=base_currency,
            operation_type=operation,  # "BID" or "ASK"
            price=str(price),
            price_currency_type="quote",
            quantity=str(quantity),
            quantity_currency_type="quote",
            fill_type="IMMEDIATE_OR_CANCEL" if price == 0 else "GOOD_TILL_CANCELLED",
        )

        signed_response = deso.sign_and_submit_txn(response)
        txn_hash = signed_response['TxnHashHex']
        print(f"Order placed successfully! Transaction hash: {txn_hash}")

        return True
    except Exception as e:
        print(f"Error placing order {e}")
        return False

print("DESO Asset Balancer")
print("="*30)
while True:
    #get Order book for DESO/USDC
    print("Updating DESO/USDC order book...")
    data=deso.get_limit_orders(deso_pubkey,usdc_pubkey)
    quote_currency = usdc_pubkey
    base_currency_selected = deso_pubkey
    print("Calculating DESO/USDC market price")
    deso_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)

    #get Order book for FOCUS/DESO
    print("Updating FOCUS/DESO order book...")
    data=deso.get_limit_orders(focus_pubkey,deso_pubkey)
    quote_currency = deso_pubkey
    base_currency_selected = focus_pubkey
    print("Calculating FOCUS/DESO market price")
    focus_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)

    
    #get Order book for OPENFUND/DESO
    print("Updating OPENFUND/DESO order book...")
    data=deso.get_limit_orders(openfund_pubkey,deso_pubkey)
    quote_currency = deso_pubkey
    base_currency_selected = openfund_pubkey
    print("Calculating OPENFUND/DESO market price")
    openfund_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)
    
    #get user balance
    print("Updating user balance...")
    usdc_coins,deso_balance_usd,focus_balance_usd,openfund_balance_usd = get_user_balance(deso_exchange_rate,focus_exchange_rate,openfund_exchange_rate)
    print("*"*30)
    print(f"deso_exchange_rate:{deso_exchange_rate}")
    print(f"focus_exchange_rate:{focus_exchange_rate}")
    print(f"openfund_exchange_rate:{openfund_exchange_rate}")
    print(f"deso_balance_usd:${deso_balance_usd}")
    print(f"usd balance:${usdc_coins}")
    print(f"focus_balance_usd:${focus_balance_usd}")
    print(f"openfund_balance_usd:${openfund_balance_usd}")
    print("*"*30)
    total_balance = deso_balance_usd + usdc_coins + focus_balance_usd+openfund_balance_usd
    print(f"total_balance:${total_balance}")
    balance_per_asset = total_balance/4
    print(f"balance_per_asset:${balance_per_asset}")
    print("*"*30)

    if openfund_balance_usd>balance_per_asset+0.01:
        sell_amount=round(openfund_balance_usd-balance_per_asset,2)/deso_exchange_rate
        print(f"Selling openfund:${sell_amount}")
        if place_limit_order(user_public_key,"ASK", openfund_pubkey, deso_pubkey, 0, sell_amount):
            openfund_balance_usd = openfund_balance_usd - sell_amount
            deso_balance_usd = deso_balance_usd + sell_amount
        
    if openfund_balance_usd<balance_per_asset-0.01:
        if deso_balance_usd<round(balance_per_asset-openfund_balance_usd,2):# deso balance low
            if(usdc_coins>round(balance_per_asset-openfund_balance_usd,2)):#buy from usdc
                buy_amount = round(balance_per_asset-openfund_balance_usd,2) 
                print(f"Buying deso:${buy_amount}")
                if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                    deso_balance_usd = deso_balance_usd + buy_amount
                    usdc_coins = usdc_coins - buy_amount
        
        buy_amount = round(balance_per_asset-openfund_balance_usd,2)/deso_exchange_rate 
        print(f"Buying openfund:${buy_amount}")
        if place_limit_order(user_public_key,"BID", openfund_pubkey, deso_pubkey, 0, buy_amount):
                openfund_balance_usd = openfund_balance_usd + buy_amount
                deso_balance_usd = deso_balance_usd - buy_amount

    if focus_balance_usd>balance_per_asset+0.01:
        sell_amount=round(focus_balance_usd-balance_per_asset,2)/deso_exchange_rate
        print(f"Selling focus:${sell_amount}")
        if place_limit_order(user_public_key,"ASK", focus_pubkey, deso_pubkey, 0, sell_amount):
            focus_balance_usd = focus_balance_usd - sell_amount
            deso_balance_usd = deso_balance_usd + sell_amount
        
    if focus_balance_usd<balance_per_asset-0.01:
        if deso_balance_usd<round(balance_per_asset-focus_balance_usd,2):#buy deso
            if(usdc_coins>round(balance_per_asset-focus_balance_usd,2)):#buy from usdc
                buy_amount = round(balance_per_asset-focus_balance_usd,2) 
                print(f"Buying deso:${buy_amount}")
                if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                    deso_balance_usd = deso_balance_usd + buy_amount
                    usdc_coins = usdc_coins - buy_amount
             
        buy_amount = round(balance_per_asset-focus_balance_usd,2)/deso_exchange_rate
        print(f"Buying focus:${buy_amount}")
        if place_limit_order(user_public_key,"BID", focus_pubkey, deso_pubkey, 0, buy_amount):
                focus_balance_usd = focus_balance_usd + buy_amount
                deso_balance_usd = deso_balance_usd - buy_amount
             
    if deso_balance_usd>balance_per_asset+0.01:
        sell_amount=round(deso_balance_usd-balance_per_asset,2)
        print(f"Selling deso:${sell_amount}")
        if place_limit_order(user_public_key,"ASK", deso_pubkey, usdc_pubkey, 0, sell_amount):
                deso_balance_usd = deso_balance_usd - sell_amount
                usdc_coins = usdc_coins + sell_amount

    if deso_balance_usd<balance_per_asset-0.01:
        buy_amount = round(balance_per_asset-deso_balance_usd,2) 
        print(f"Buying deso:${buy_amount}")
        if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                deso_balance_usd = deso_balance_usd + buy_amount
                usdc_coins = usdc_coins - buy_amount

    print(f"usd:${usdc_coins},deso:${deso_balance_usd},focus:${focus_balance_usd},openfund:${openfund_balance_usd}")
    
    print(f"sleep {update_interval} seconds")
    time.sleep(update_interval)
