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

def execute_trade(symbol, side, quantity, entry_price=None, stop_loss_pct=2.0, take_profit_pct=4.0):
    """
    Execute a long or short trade with OCO (One-Cancels-the-Other) for stop loss and take profit.

    Parameters:
        symbol (str): The trading pair symbol (e.g., "BTCUSDT").
        side (str): Trade direction, either "BUY" for long or "SELL" for short.
        quantity (float): Amount to trade.
        entry_price (float, optional): Price at which the trade is executed. Defaults to market price if None.
        stop_loss_pct (float): Percentage loss to trigger stop loss. Defaults to 2.0%.
        take_profit_pct (float): Percentage gain to trigger take profit. Defaults to 4.0%.
    """
    try:
        if side not in ["BUY", "SELL"]:
            raise ValueError("Side must be either 'BUY' or 'SELL'.")

        # Fetch the current market price if entry_price is not provided
        if entry_price is None:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            entry_price = float(ticker["price"])
            print(f"Market price fetched: {entry_price}")

        # Calculate stop loss and take profit prices
        stop_loss = (
            entry_price * (1 - stop_loss_pct / 100) if side == "BUY"
            else entry_price * (1 + stop_loss_pct / 100)
        )
        take_profit = (
            entry_price * (1 + take_profit_pct / 100) if side == "BUY"
            else entry_price * (1 - take_profit_pct / 100)
        )

        # Place the initial market order
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )
        print(f"Market order executed: {side} {quantity} {symbol} at ~{entry_price}")

        # Place the OCO order for stop loss and take profit
        oco_order = client.futures_create_oco_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            quantity=quantity,
            price=round(take_profit, 2),  # Take profit price
            stopPrice=round(stop_loss, 2),  # Stop loss trigger price
            stopLimitPrice=round(stop_loss, 2),  # Stop loss execution price
            stopLimitTimeInForce="GTC"
        )
        print(f"OCO order placed with Stop Loss at {round(stop_loss, 2)} and Take Profit at {round(take_profit, 2)}")

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
    execute_trade(
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.01,
    # entry_price=0000,
    stop_loss_pct=2.5,  # 2.5% pérdida
    take_profit_pct=5  # 5% ganancia
    )
