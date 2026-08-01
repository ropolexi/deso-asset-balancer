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
balancer_active=bool(os.getenv("BALANCER_ACTIVE", "False").lower() == "true")
print_debug=bool(os.getenv("PRINT_DEBUG", "False").lower() == "true")
deviation=float(os.getenv("DEVIATION"))

print("\nDESO Asset Balancer\n")
print(f"{'Balancer Active':<20}: {balancer_active}")
print(f"{'Node':<20}: {node}")
print(f"{'Trigger Deviation':<20}: {deviation} %")


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

total_perc=deso_perc+focus_perc+openfund_perc
for token in tokens_based_on_focus:
     total_perc=total_perc+token["target_percentage"]
if total_perc<100:
    perc_status="OK"
else:
    perc_status="Sum of percentages should be less than 100"
print(f"{'Percentage Check':<20}: {perc_status}")
print(f"{'USDC %':<20}: {(100-total_perc):.1f} %")
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
    if bids is not None:
        best_bid_price, best_bid_quantity,best_bid_trasactor = max(bids)
    else:
        best_bid_price=0

    if asks is not None:
        best_ask_price, best_ask_quantity,best_ask_trasactor = min(asks)
    else:
         best_ask_price=0

    if print_debug:
        print(f"best_bid_price:{best_bid_price},best_ask_price:{best_ask_price}")
    if best_ask_price!=0 and best_bid_price:
        exchange_rate=(float(best_bid_price)+float(best_ask_price))/2
    else:
        exchange_rate=0

    return exchange_rate

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

while True:
    #get Order book for DESO/USDC
    
    if print_debug:print("Updating DESO/USDC order book...")
    data=deso.get_limit_orders(deso_pubkey,usdc_pubkey)
    quote_currency = usdc_pubkey
    base_currency_selected = deso_pubkey
    if print_debug:print("Calculating DESO/USDC market price")
    deso_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)

    #get Order book for FOCUS/DESO
    if print_debug:print("Updating FOCUS/DESO order book...")
    data=deso.get_limit_orders(focus_pubkey,deso_pubkey)
    quote_currency = deso_pubkey
    base_currency_selected = focus_pubkey
    if print_debug:print("Calculating FOCUS/DESO market price")
    focus_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)

    
    #get Order book for OPENFUND/DESO
    if print_debug:print("Updating OPENFUND/DESO order book...")
    data=deso.get_limit_orders(openfund_pubkey,deso_pubkey)
    quote_currency = deso_pubkey
    base_currency_selected = openfund_pubkey
    if print_debug:print("Calculating OPENFUND/DESO market price")
    openfund_exchange_rate = get_exchange_rate(data,quote_currency,base_currency_selected)

    for token in tokens_based_on_focus:
        if print_debug:print(f"Updating {token['name']}/FOCUS order book...")
        data=deso.get_limit_orders(token["pubkey"],focus_pubkey)
        quote_currency = focus_pubkey
        base_currency_selected = token["pubkey"]
        if print_debug:print(f"Calculating {token['name']}/FOCUS market price")
        token["exchange_rate"] = get_exchange_rate(data,quote_currency,base_currency_selected)
    
    print("\nExchange RATES")
    print("="*70)
    print(f"{'deso:':<30} USDC  {deso_exchange_rate:10f} | {deso_exchange_rate:10f} USDC")
    print(f"{'focus:':<30} DESO  {focus_exchange_rate:10f} | {deso_exchange_rate*focus_exchange_rate:10f} USDC")
    print(f"{'openfund:':<30} DESO  {openfund_exchange_rate:10f} | {deso_exchange_rate*openfund_exchange_rate:10f} USDC")
    for token in tokens_based_on_focus:
        label = token['name']
        print(f"{label:<30} FOCUS {token['exchange_rate']:10f} | {deso_exchange_rate*focus_exchange_rate*token['exchange_rate']:10f} USDC")
    print("="*70)

    #get user balance
    if print_debug:print("\nUpdating user balance...")
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
  
    print(f"\nTotal_balance:${total_balance:.2f}")
    
    #balance_per_asset = total_balance/4
    deso_target_balance = total_balance * deso_perc /100
    focus_target_balance = total_balance * focus_perc/100
    openfund_target_balance = total_balance * openfund_perc/100
    for token in tokens_based_on_focus:
        token["target_balance_usd"] = total_balance * token["target_percentage"]/100
    print("="*80)
    print(f"{'Token Name':<25} | {'Balance':<6} | {'Current':<6} % | {'Target':<6} % | {'Target $':<7} | {'Deviation':<5}")
    print("="*80)
    dev=100*(deso_balance_usd -deso_target_balance)/deso_target_balance
    print(f"{'deso':<25} | ${deso_balance_usd:7.2f} | {current_deso_balance_perc:6.2f} % | {deso_perc:6.2f} % | ${deso_target_balance:7.2f} | ({dev:+5.1f}%)")
    dev=100*(focus_balance_usd -focus_target_balance)/focus_target_balance
    print(f"{'focus':<25} | ${focus_balance_usd:7.2f} | {current_focus_balance_usd_perc:6.2f} % | {focus_perc:6.2f} % | ${focus_target_balance:7.2f} | ({dev:+5.1f}%)")
    dev=100*(openfund_balance_usd -openfund_target_balance)/openfund_target_balance
    print(f"{'openfund':<25} | ${openfund_balance_usd:7.2f} | {current_openfund_balance_usd_perc:6.2f} % | {openfund_perc:6.2f} % | ${openfund_target_balance:7.2f} | ({dev:+5.1f}%)")
    for token in tokens_based_on_focus:
        label = f"{token['name']}"
        dev=100*(token['balance_usd']-token['target_balance_usd'])/token['target_balance_usd']
        print(f"{label:<25} | ${token['balance_usd']:7.2f} | {token['current_perc']:6.2f} % | {token['target_percentage']:6.2f} % | ${token['target_balance_usd']:7.2f} | ({dev:+5.1f}%)")
    
    
    if balancer_active:
        if print_debug:print("\nBalancing..")
        for token in tokens_based_on_focus:
            if print_debug:print(f"{token['name']}..") 
            if token["exchange_rate"]==0: #no buyers
                continue
            if token['balance_usd']>token['target_balance_usd']*(1+deviation/100):
                sell_amount=round(token['balance_usd']-token['target_balance_usd'],2)
                print(f"Selling {token['name']}:${sell_amount}")
                if place_limit_order(user_public_key,"ASK", token["pubkey"], focus_pubkey, 0, (sell_amount/deso_exchange_rate)/focus_exchange_rate):
                        token['balance_usd'] = token['balance_usd'] - sell_amount
                        focus_balance_usd = focus_balance_usd + sell_amount

            if token['balance_usd']<token['target_balance_usd']*(1-deviation/100):
                buy_amount = round(token['target_balance_usd']-token['balance_usd'],2)
                if focus_balance_usd< buy_amount:#not enough focus
                    if print_debug:print(f"Buying focus:${buy_amount}")
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
        if print_debug:print("Openfund..")
        if openfund_balance_usd>openfund_target_balance*(1+deviation/100):
            sell_amount=round(openfund_balance_usd-openfund_target_balance,2)
            print(f"Selling openfund:${sell_amount}")
            if place_limit_order(user_public_key,"ASK", openfund_pubkey, deso_pubkey, 0, sell_amount/deso_exchange_rate):
                openfund_balance_usd = openfund_balance_usd - sell_amount
                deso_balance_usd = deso_balance_usd + sell_amount
            
        if openfund_balance_usd<openfund_target_balance*(1-deviation/100):
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

        if print_debug:print("Focus..")
        if focus_balance_usd>focus_target_balance*(1+deviation/100):
            sell_amount=round(focus_balance_usd-focus_target_balance,2)
            print(f"Selling focus:${sell_amount}")
            selling_amount_in_deso = sell_amount/deso_exchange_rate
            print(selling_amount_in_deso)
            if place_limit_order(user_public_key,"ASK", focus_pubkey, deso_pubkey, 0,selling_amount_in_deso ):
                focus_balance_usd = focus_balance_usd - sell_amount
                deso_balance_usd = deso_balance_usd + sell_amount
            
        if focus_balance_usd<focus_target_balance*(1-deviation/100):
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
        if print_debug:print("Deso..")        
        if deso_balance_usd>deso_target_balance*(1+deviation/100):
            sell_amount=round(deso_balance_usd-deso_target_balance,2)
            print(f"Selling deso:${sell_amount}")
            if place_limit_order(user_public_key,"ASK", deso_pubkey, usdc_pubkey, 0, sell_amount):
                    deso_balance_usd = deso_balance_usd - sell_amount
                    usdc_coins = usdc_coins + sell_amount

        if deso_balance_usd<deso_target_balance*(1-deviation/100):
            buy_amount = round(deso_target_balance-deso_balance_usd,2) 
            print(f"Buying deso:${buy_amount}")
            if place_limit_order(user_public_key,"BID", deso_pubkey, usdc_pubkey, 0, buy_amount):
                    deso_balance_usd = deso_balance_usd + buy_amount
                    usdc_coins = usdc_coins - buy_amount
    
    
    print(f"\nsleep {update_interval} seconds")
    time.sleep(update_interval)
