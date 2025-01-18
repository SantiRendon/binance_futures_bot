from binance.client import Client
from datetime import datetime, timezone

# API keys (example mock keys)
api_key = '7de4ca57d53aac719f84f4f2f1ceee269512766e19734dca3beaec464c92a2d1'
api_secret = '15122b41c53e6293bd122333bf8f31a12e7f8b876595a290473487e38a25d3f0'

# Connect to Binance Futures testnet
client = Client(api_key, api_secret, testnet=True)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi/v1"

def list_available_pairs():
    """List all available trading pairs on Binance Futures."""
    exchange_info = client.futures_exchange_info()
    symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
    return symbols

def get_current_prices(pairs):
    """Fetch the current prices for the specified trading pairs."""
    prices = {}
    for pair in pairs:
        try:
            ticker = client.futures_symbol_ticker(symbol=pair)
            prices[pair] = float(ticker['price'])
        except Exception as e:
            print(f"Error fetching price for {pair}: {e}")
    return prices

def get_historical_prices(symbol, interval, start_time=None, end_time=None, limit=100):
    """Fetch historical price data (candlesticks) for a given trading pair."""
    try:
        if isinstance(start_time, str):
            start_time = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp() * 1000)
        if isinstance(end_time, str):
            end_time = int(datetime.strptime(end_time, "%Y-%m-%d").timestamp() * 1000)

        klines = client.futures_klines(
            symbol=symbol,
            interval=interval,
            startTime=start_time,
            endTime=end_time,
            limit=limit
        )
        return klines
    except Exception as e:
        print(f"Error fetching historical prices for {symbol}: {e}")
        return []

def execute_trade(symbol, side, quantity, price, stop_loss, take_profit):
    """Execute a long or short trade with stop loss and take profit."""
    try:
        if side not in ["BUY", "SELL"]:
            raise ValueError("Side must be either 'BUY' or 'SELL'.")
        
        # Create the order (example: market order)
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )
        
        # Set stop loss and take profit (example for a market order)
        stop_loss_order = client.futures_create_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="STOP_MARKET",
            stopPrice=stop_loss,
            quantity=quantity
        )
        
        take_profit_order = client.futures_create_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="TAKE_PROFIT_MARKET",
            stopPrice=take_profit,
            quantity=quantity
        )

        print(f"Trade executed: {side} {quantity} {symbol} at {price}")
        print(f"Stop Loss set at {stop_loss}, Take Profit set at {take_profit}")
    except Exception as e:
        print(f"Error executing trade: {e}")

if __name__ == "__main__":
    # Example usage of the functions
    available_pairs = list_available_pairs()
    print(f"Available pairs: {available_pairs}")

    # Example: Get current prices for selected pairs
    pairs_to_check = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    current_prices = get_current_prices(pairs_to_check)
    print("Current prices:")
    for pair, price in current_prices.items():
        print(f"{pair}: {price}")

    # Example: Execute a trade
    execute_trade("BTCUSDT", "BUY", 0.01, 30000, 29500, 30500)
