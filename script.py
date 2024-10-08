import logging
import alpaca_trade_api as tradeapi
import time
import numpy as np

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)

# Alpaca API configuration
API_KEY = 'PKK46FOQILEK4ALAF8IU'
API_SECRET = 'e7WOD5V3MweUClo3jhxS4Fg6xndbfqm0r6pET1cY'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# Global variables
last_price = None
current_position = 0  # Track how many shares of GOOGL we own
upward_changes = 0  # Track consecutive upward price changes
downward_change = False  # Track if there's been a downward change

def get_account_info():
    """Get the account buying power and balance."""
    try:
        account = api.get_account()
        buying_power = float(account.cash)
        regt_buying_power = float(account.regt_buying_power)  # Regular Buying Power
        cash = float(account.cash)  # Cash balance
        logging.info(f"Account buying power: ${regt_buying_power:.2f}")
        logging.info(f"Account cash balance: ${cash:.2f}")
        return regt_buying_power, cash
    except tradeapi.rest.APIError as e:
        logging.error(f"Error getting account info: {e}")
        return None, None

def sell_all_googl():
    """Sell all owned GOOGL stock."""
    try:
        positions = api.list_positions()
        for pos in positions:
            if pos.symbol == 'GOOGL':
                qty_to_sell = pos.qty
                api.submit_order(
                    symbol='GOOGL',
                    qty=qty_to_sell,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                logging.info(f"Sold {qty_to_sell} shares of GOOGL.")
                return
    except tradeapi.rest.APIError as e:
        logging.error(f"Error placing sell order: {e}")

def buy_googl():
    """Buy GOOGL stock with available buying power."""
    regt_buying_power, cash = get_account_info()  # Get real-time buying power and cash

    if regt_buying_power is None or cash <= 0:
        logging.warning("No available buying power or cash.")
        return

    try:
        # Get the latest price of GOOGL
        googl_price = api.get_latest_trade('GOOGL').price
        num_shares_to_buy = regt_buying_power / googl_price  # Use all buying power

        # Make sure we only buy whole shares
        num_shares_to_buy = int(np.floor(num_shares_to_buy))
        logging.info(f"Buying {num_shares_to_buy} shares of GOOGL at ${googl_price:.2f}")

        if num_shares_to_buy > 0:
            api.submit_order(
                symbol='GOOGL',
                qty=num_shares_to_buy,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            logging.info(f"Bought {num_shares_to_buy} shares of GOOGL.")
        else:
            logging.warning("Not enough buying power to buy even 1 share of GOOGL.")
    except tradeapi.rest.APIError as e:
        logging.error(f"Error placing buy order: {e}")

def run_trading_strategy():
    """Main trading strategy execution."""
    global last_price, current_position, upward_changes, downward_change

    regt_buying_power, _ = get_account_info()

    if regt_buying_power is None:
        return

    try:
        # Get the most recent trade for GOOGL
        current_trade = api.get_latest_trade('GOOGL')
        current_price = current_trade.price
        logging.info(f"Current GOOGL price: ${current_price:.2f}")

        # If the price is going up
        if last_price is None or current_price > last_price:
            if current_position == 0:  # Only buy if we don't currently own shares
                upward_changes += 1
                logging.info(f"Price has gone up, consecutive upward changes: {upward_changes}")
                
                # Only buy after 5 consecutive upward price changes
                if upward_changes == 5:
                    logging.info("Five consecutive upward price changes, buying with all buying power.")
                    buy_googl()
                    current_position = 1  # We now own GOOGL shares
                    upward_changes = 0  # Reset upward change counter
            else:
                logging.info("Price is increasing, holding position.")

        # If the price is going down
        elif last_price is not None and current_price < last_price:
            logging.info(f"Price has decreased, resetting consecutive upward changes.")
            downward_change = True  # Set the downward change flag
            upward_changes = 0  # Reset upward changes
            if current_position > 0:  # If we own shares, sell them
                logging.info("Selling all shares as price is decreasing.")
                sell_all_googl()
                current_position = 0  # We no longer own any shares

        # If the price is stable
        elif last_price is not None and current_price == last_price and current_position > 0:
            logging.info("GOOGL price is stable, holding position.")

        # Update last price with the current price
        last_price = current_price

    except tradeapi.rest.APIError as e:
        logging.error(f"Error in trading strategy: {e}")

def start_trading():
    """Start trading with initial position check (sell all if we own GOOGL)."""
    logging.info("Starting Alpaca trading bot...")

    # First, sell all current GOOGL stock if any
    sell_all_googl()

    # Wait a few seconds for the sell order to complete (adjust based on market conditions)
    time.sleep(0.5)

    # Start the trading strategy
    while True:
        run_trading_strategy()
        time.sleep(0.5)  # Sleep after every loop iteration

if __name__ == "__main__":
    start_trading()
