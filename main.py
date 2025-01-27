from binance.client import Client
from binance import ThreadedWebsocketManager
import threading
import time
import asyncio
import os

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

# Verifica que las claves se carguen correctamente
if not api_key or not api_secret:
    raise ValueError(
        "Las claves API_KEY y API_SECRET no están configuradas correctamente en el archivo .env."
    )


# Connect to Binance Futures testnet
client = Client(api_key, api_secret, testnet=True)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi/v1"


def list_available_pairs():
    """List all available trading pairs on Binance Futures."""
    try:
        exchange_info = client.futures_exchange_info()  # Fetch exchange info
        symbols = [
            symbol["symbol"] for symbol in exchange_info["symbols"]
        ]  # Extract symbols
        return symbols
    except Exception as e:
        print(f"Error fetching available pairs: {e}")
        return []


def get_current_price(symbol):
    """Fetch the current market price for a single trading pair."""
    try:
        ticker = client.futures_symbol_ticker(
            symbol=symbol
        )  # Fetch ticker info for the symbol
        return float(ticker["price"])  # Return the price as a float
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def get_current_prices(symbols):
    """Fetch the current prices for multiple trading pairs."""
    prices = {}
    for symbol in symbols:
        price = get_current_price(symbol)  # Fetch price for each symbol
        if price is not None:
            prices[symbol] = price  # Add the price to the dictionary
    return prices


def get_historical_prices(symbol, interval, start_time=None, end_time=None, limit=100):
    """Fetch historical price data (candlesticks) for a given trading pair."""
    try:
        klines = client.futures_klines(
            symbol=symbol,
            interval=interval,
            startTime=start_time,
            endTime=end_time,
            limit=limit,
        )
        return klines  # Return the historical price data (candlesticks)
    except Exception as e:
        print(f"Error fetching historical prices for {symbol}: {e}")
        return []


def calculate_stop_loss_take_profit(entry_price, stop_loss_pct, take_profit_pct, side):
    """Calculate stop loss and take profit prices based on the entry price and percentages."""
    stop_loss = (
        entry_price * (1 - stop_loss_pct / 100)
        if side == "BUY"  # Calculate stop loss for buy orders
        else entry_price
        * (1 + stop_loss_pct / 100)  # Calculate stop loss for sell orders
    )
    take_profit = (
        entry_price * (1 + take_profit_pct / 100)
        if side == "BUY"  # Calculate take profit for buy orders
        else entry_price
        * (1 - take_profit_pct / 100)  # Calculate take profit for sell orders
    )
    return round(stop_loss, 2), round(
        take_profit, 2
    )  # Return stop loss and take profit prices rounded to 2 decimals


def place_market_order(symbol, side, quantity):
    """Place a market order."""
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",  # Type of order
            quantity=quantity,  # Quantity of the asset to trade
        )
        return order  # Return the order details
    except Exception as e:
        print(f"Error placing market order for {symbol}: {e}")
        return None


def place_oco_order(symbol, side, quantity, stop_loss, take_profit):
    """Place an OCO order (stop loss and take profit)."""
    try:
        oco_order = client.futures_create_oco_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",  # Reverse the side for OCO orders
            quantity=quantity,
            price=take_profit,  # Take profit price
            stopPrice=stop_loss,  # Stop loss trigger price
            stopLimitPrice=stop_loss,  # Stop loss execution price
            stopLimitTimeInForce="GTC",  # Good 'Til Canceled order type
        )
        return oco_order  # Return the OCO order details
    except Exception as e:
        print(f"Error placing OCO order for {symbol}: {e}")
        return None


def execute_trade(
    symbol, side, quantity, entry_price=None, stop_loss_pct=2.0, take_profit_pct=4.0
):
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
        if side not in ["BUY", "SELL"]:  # Ensure side is valid
            raise ValueError("Side must be either 'BUY' or 'SELL'.")

        # Fetch the current market price if entry_price is not provided
        if entry_price is None:
            entry_price = get_current_price(symbol)
            if entry_price is None:
                print("Error: Unable to fetch market price.")
                return

        print(f"Market order executed: {side} {quantity} {symbol} at ~{entry_price}")

        # Calculate stop loss and take profit prices
        stop_loss, take_profit = calculate_stop_loss_take_profit(
            entry_price, stop_loss_pct, take_profit_pct, side
        )

        # Place the market order
        place_market_order(symbol, side, quantity)

        # Place the OCO order for stop loss and take profit
        oco_order = place_oco_order(symbol, side, quantity, stop_loss, take_profit)
        if oco_order:
            print(
                f"OCO order placed with Stop Loss at {stop_loss} and Take Profit at {take_profit}"
            )

    except Exception as e:
        print(f"Error executing trade: {e}")


# WebSocket for the price strategy
def start_strategy_monitor(symbol, interval, callback):
    def handle_message(msg):
        if msg["e"] == "kline":  # Check if message type is kline (candlestick data)
            kline = msg["k"]
            close_price = float(kline["c"])  # Close price of the candlestick
            print(f"Updated price: {close_price}")
            callback(close_price)

    # Create the WebSocket manager
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret, testnet=True)
    twm.start()

    # Subscribe to the kline stream for price updates
    twm.start_kline_socket(callback=handle_message, symbol=symbol, interval=interval)

    print(f"Strategy WebSocket started for {symbol} ({interval}).")
    return twm


# WebSocket for monitoring open orders
def start_order_monitor(symbol, client):
    def handle_message(msg):
        try:
            if msg["e"] == "ORDER_TRADE_UPDATE":  # Order update event
                order_status = msg["o"]["X"]  # Order status (FILLED, NEW)
                order_side = msg["o"]["S"]  # Order side (BUY or SELL)
                order_id = msg["o"]["i"]  # Order ID
                symbol = msg["o"]["s"]  # Symbol of the order

                if order_status == "FILLED":  # If the order is filled
                    print(f"Order filled: {order_side} {symbol}, ID: {order_id}")

                    # Get all open orders
                    open_orders = client.futures_get_open_orders(symbol=symbol)
                    for order in open_orders:
                        if order["orderId"] != order_id:  # Cancel other orders
                            client.futures_cancel_order(
                                symbol=symbol, orderId=order["orderId"]
                            )
                            print(f"Cancelled opposite order: {order['orderId']}")

        except Exception as e:
            print(f"Error handling message: {e}")

    # Create the WebSocket manager
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret, testnet=True)
    twm.start()

    # Get the listen key and subscribe to the user data stream
    client.futures_stream_get_listen_key()
    twm.start_futures_user_socket(callback=handle_message)

    print("Order WebSocket started. Listening for updates...")
    return twm


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Strategy function (currently just prints the price)
    def strategy_callback(price):
        print(f"Price received in strategy: {price}")
        # Add your strategy logic here (when available)

    # Start the WebSocket to monitor the price
    strategy_thread = threading.Thread(
        target=start_strategy_monitor, args=("BTCUSDT", "5m", strategy_callback)
    )
    strategy_thread.start()

    # Start the WebSocket to monitor open orders
    order_thread = threading.Thread(
        target=start_order_monitor, args=("BTCUSDT", client)
    )
    order_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)  # Mantén el bucle activo hasta que se interrumpa
    except KeyboardInterrupt:
        print("Programa detenido por el usuario con Ctrl+C.")
        # Detener los WebSockets
        strategy_thread.join()  # Espera a que termine el thread
        order_thread.join()  # Espera a que termine el thread
        print("Websockets detenidos. El programa ha finalizado.")
