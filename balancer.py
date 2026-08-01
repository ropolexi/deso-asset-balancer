from deso_sdk import DeSoDexClient,base58_check_encode
import time
import os
import json
from dotenv import load_dotenv


deso_pubkey="DESO"
focus_pubkey="BC1YLjEayZDjAPitJJX4Boy7LsEfN3sWAkYb3hgE9kGBirztsc2re1N"
openfund_pubkey="BC1YLj3zNA7hRAqBVkvsTeqw7oi4H6ogKiAFL1VXhZy6pYeZcZ6TDRY"
usdc_pubkey="BC1YLiwTN3DbkU8VmD7F7wXcRR1tFX6jDEkLyruHD2WsH3URomimxLX"
openfund_pubkey="BC1YLj3zNA7hRAqBVkvsTeqw7oi4H6ogKiAFL1VXhZy6pYeZcZ6TDRY"

load_dotenv()



deso_seed = os.getenv("DESO_SEED")

update_interval = int(os.getenv("UPDATE_INTERVAL"))

node=os.getenv("NODE")

deso_perc=float(os.getenv("DESO_PERCENTAGE"))
focus_perc=float(os.getenv("FOCUS_PERCENTAGE"))
openfund_perc=float(os.getenv("OPENFUND_PERCENTAGE"))

tokens_data = json.loads(os.getenv("TOKENS_BASED_ON_FOCUS","[]"))

tokens_based_on_focus = [
    {
        "name":token["name"],
        "pubkey":token["pubkey"],
        "exchange_rate":0,
        "tokens_qty":0,
        "balance_usd":0,
        "target_percentage":token["target_percentage"],
        "current_perc":0
    } for token in tokens_data
]

delta=float(os.getenv("DELTA"))
deso = DeSoDexClient(is_testnet=False,seed_phrase_or_hex=deso_seed,node_url=node)
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
    
    best_ask_price, best_ask_quantity,best_ask_trasactor = min(asks)
    print(f"best_bid_price:{best_bid_price},best_ask_price:{best_ask_price}")

    return (float(best_bid_price)+float(best_ask_price))/2

def get_user_balance(deso_exchange_rate,focus_exchange_rate,openfund_exchange_rate,tokens_based_on_focus):
    res=deso.get_token_balances(
        user_public_key=user_public_key,
        creator_public_keys=[deso_pubkey,
                                focus_pubkey,
                                usdc_pubkey,
                                openfund_pubkey,
                            ] + [token["pubkey"] for token in tokens_based_on_focus]
        )
    deso_coins=deso.base_units_to_coins(float(res["Balances"][deso_pubkey]["BalanceBaseUnits"]),True)
    usdc_coins=deso.base_units_to_coins(float(res["Balances"][usdc_pubkey]["BalanceBaseUnits"]),False)
    focus_coins= deso.base_units_to_coins(float(res["Balances"][focus_pubkey]["BalanceBaseUnits"]),False)
    openfund_coins = deso.base_units_to_coins(float(res["Balances"][openfund_pubkey]["BalanceBaseUnits"]),False)
    
    for token in tokens_based_on_focus:
        token["token_qty"]= deso.base_units_to_coins(float(res["Balances"][token["pubkey"]]["BalanceBaseUnits"]),False)

    deso_balance_usd = deso_coins * deso_exchange_rate
    focus_balance_usd = focus_coins * focus_exchange_rate * deso_exchange_rate
    openfund_balance_usd = openfund_coins * openfund_exchange_rate * deso_exchange_rate
    
    for token in tokens_based_on_focus:
        token["balance_usd"] = token["token_qty"] * token["exchange_rate"] * focus_exchange_rate * deso_exchange_rate


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

    for token in tokens_based_on_focus:
        print(f"Updating {token['name']}/FOCUS order book...")
        data=deso.get_limit_orders(token["pubkey"],focus_pubkey)
        quote_currency = focus_pubkey
        base_currency_selected = token["pubkey"]
        print(f"Calculating {token['name']}/FOCUS market price")
        token["exchange_rate"] = get_exchange_rate(data,quote_currency,base_currency_selected)
    
    print("\nExchange RATES")
    print("="*30)
    print(f"deso_exchange_rate:\t{deso_exchange_rate}")
    print(f"focus_exchange_rate:\t{focus_exchange_rate}")
    print(f"openfund_exchange_rate:\t{openfund_exchange_rate}")
    for token in tokens_based_on_focus:
        print(f"{token['name']}_exchange_rate:\t{token['exchange_rate']}")
    print("="*30)

    #get user balance
    print("\nUpdating user balance...")
    usdc_coins,deso_balance_usd,focus_balance_usd,openfund_balance_usd = get_user_balance(deso_exchange_rate,focus_exchange_rate,openfund_exchange_rate,tokens_based_on_focus)
    
    total_balance = deso_balance_usd + usdc_coins + focus_balance_usd+openfund_balance_usd
    for token in tokens_based_on_focus:
        total_balance = total_balance + token["balance_usd"]

    current_deso_balance_perc = 100 * deso_balance_usd/total_balance
    current_usdc_coins_perc = 100 * usdc_coins/total_balance
    current_focus_balance_usd_perc = 100 * focus_balance_usd/total_balance
    current_openfund_balance_usd_perc = 100 * openfund_balance_usd/total_balance
    for token in tokens_based_on_focus:
        token["current_perc"] = 100 * token["balance_usd"]/total_balance

    print("\nUSER WALLET BALANCE")
    print("="*30)
    print(f"deso_balance_usd \t- {current_deso_balance_perc:06.2f}% : ${deso_balance_usd:.2f}")
    print(f"usd balance \t\t- {current_usdc_coins_perc:06.2f}% : ${usdc_coins:.2f}")
    print(f"focus_balance_usd \t- {current_focus_balance_usd_perc:06.2f}% : ${focus_balance_usd:.2f}")
    print(f"openfund_balance_usd \t- {current_openfund_balance_usd_perc:06.2f}% : ${openfund_balance_usd:.2f}")
    for token in tokens_based_on_focus:
        print(f"{token['name']}_balance_usd \t- {token['current_perc']:06.2f}% : ${token['balance_usd']:.2f}")
    
    print("="*30)
    print(f"\nTotal_balance:${total_balance:.2f}")
    print("="*30)
    #balance_per_asset = total_balance/4
    deso_target_balance = total_balance * deso_perc /100
    focus_target_balance = total_balance * focus_perc/100
    openfund_target_balance = total_balance * openfund_perc/100
    for token in tokens_based_on_focus:
        token["target_balance_usd"] = total_balance * token["target_percentage"]/100

    print(f"deso_target \t\t- {deso_perc:06.2f}% : ${deso_target_balance:.2f}")
    print(f"focus_target \t\t- {focus_perc:06.2f}% : ${focus_target_balance:.2f}")
    print(f"openfund_target \t- {openfund_perc:06.2f}% : ${openfund_target_balance:.2f}")
    for token in tokens_based_on_focus:
        print(f"{token['name']}_target \t\t- {token['target_percentage']:06.2f}% : ${token['target_balance_usd']:.2f}")
    
    print("\nBalancing..")
    for token in tokens_based_on_focus:
        print(f"{token['name']}..")        
        if token['balance_usd']>token['target_balance_usd']+delta:
            sell_amount=round(token['balance_usd']-token['target_balance_usd'],2)
            print(f"Selling {token['name']}:${sell_amount}")
            if place_limit_order(user_public_key,"ASK", token["pubkey"], focus_pubkey, 0, (sell_amount/deso_exchange_rate)/focus_exchange_rate):
                    token['balance_usd'] = token['balance_usd'] - sell_amount
                    focus_balance_usd = focus_balance_usd + sell_amount

        if token['balance_usd']<token['target_balance_usd']-delta:
            buy_amount = round(token['target_balance_usd']-token['balance_usd'],2)
            if focus_balance_usd< buy_amount:#not enough focus
                print(f"Buying focus:${buy_amount}")
                if deso_balance_usd < buy_amount:#not enough deso
                    print(f"Buying deso:${buy_amount}")
                    if usdc_coins>buy_amount:
                        if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                            deso_balance_usd = deso_balance_usd + buy_amount
                            usdc_coins = usdc_coins - buy_amount
                    else:
                        print("Not enough usdc!")
                    
                if place_limit_order(user_public_key,"BID", focus_pubkey, deso_pubkey, 0, buy_amount/deso_exchange_rate):
                        focus_balance_usd = focus_balance_usd + buy_amount
                        deso_balance_usd = deso_balance_usd - buy_amount

            print(f"Buying {token['name']}:${buy_amount}")
            if place_limit_order(user_public_key,"BID",token["pubkey"], focus_pubkey,  0, (buy_amount/deso_exchange_rate)/focus_exchange_rate):
                    token['balance_usd'] = token['balance_usd'] + buy_amount
                    focus_balance_usd = focus_balance_usd - buy_amount
    print("Openfund..")
    if openfund_balance_usd>openfund_target_balance+delta:
        sell_amount=round(openfund_balance_usd-openfund_target_balance,2)
        print(f"Selling openfund:${sell_amount}")
        if place_limit_order(user_public_key,"ASK", openfund_pubkey, deso_pubkey, 0, sell_amount/deso_exchange_rate):
            openfund_balance_usd = openfund_balance_usd - sell_amount
            deso_balance_usd = deso_balance_usd + sell_amount
        
    if openfund_balance_usd<openfund_target_balance-delta:
        buy_amount = round(openfund_target_balance-openfund_balance_usd,2) 
        if deso_balance_usd<buy_amount:# deso balance low
            if(usdc_coins>buy_amount):#buy from usdc
                print(f"Buying deso:${buy_amount}")
                if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                    deso_balance_usd = deso_balance_usd + buy_amount
                    usdc_coins = usdc_coins - buy_amount
        
        print(f"Buying openfund:${buy_amount}")
        if place_limit_order(user_public_key,"BID", openfund_pubkey, deso_pubkey, 0, buy_amount/deso_exchange_rate):
                openfund_balance_usd = openfund_balance_usd + buy_amount
                deso_balance_usd = deso_balance_usd - buy_amount

    print("Focus..")
    if focus_balance_usd>focus_target_balance+delta:
        sell_amount=round(focus_balance_usd-focus_target_balance,2)
        print(f"Selling focus:${sell_amount}")
        selling_amount_in_deso = sell_amount/deso_exchange_rate
        print(selling_amount_in_deso)
        if place_limit_order(user_public_key,"ASK", focus_pubkey, deso_pubkey, 0,selling_amount_in_deso ):
            focus_balance_usd = focus_balance_usd - sell_amount
            deso_balance_usd = deso_balance_usd + sell_amount
        
    if focus_balance_usd<focus_target_balance-delta:
        buy_amount = round(focus_target_balance-focus_balance_usd,2) 
        if deso_balance_usd<buy_amount:#buy deso
            if(usdc_coins>buy_amount):#buy from usdc
                print(f"Buying deso:${buy_amount}")
                if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                    deso_balance_usd = deso_balance_usd + buy_amount
                    usdc_coins = usdc_coins - buy_amount
            else:
                print("Not enough usdc!")
             
        print(f"Buying focus:${buy_amount}")
        if place_limit_order(user_public_key,"BID", focus_pubkey, deso_pubkey, 0, buy_amount/deso_exchange_rate):
                focus_balance_usd = focus_balance_usd + buy_amount
                deso_balance_usd = deso_balance_usd - buy_amount
    print("Deso..")        
    if deso_balance_usd>deso_target_balance+delta:
        sell_amount=round(deso_balance_usd-deso_target_balance,2)
        print(f"Selling deso:${sell_amount}")
        if place_limit_order(user_public_key,"ASK", deso_pubkey, usdc_pubkey, 0, sell_amount):
                deso_balance_usd = deso_balance_usd - sell_amount
                usdc_coins = usdc_coins + sell_amount

    if deso_balance_usd<deso_target_balance-delta:
        buy_amount = round(deso_target_balance-deso_balance_usd,2) 
        print(f"Buying deso:${buy_amount}")
        if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                deso_balance_usd = deso_balance_usd + buy_amount
                usdc_coins = usdc_coins - buy_amount

    
    print("\nUSER WALLET BALANCE AFTER BALANCING")
    print("="*30)
    print(f"deso_balance_usd:\t${deso_balance_usd:.2f}")
    print(f"usd balance:\t\t${usdc_coins:.2f}")
    print(f"focus_balance_usd:\t${focus_balance_usd:.2f}")
    print(f"openfund_balance_usd:\t${openfund_balance_usd:.2f}")
    for token in tokens_based_on_focus:
        print(f"{token['name']}_balance_usd :\t${token['balance_usd']:.2f}")
    
    
    print(f"\nsleep {update_interval} seconds")
    time.sleep(update_interval)
