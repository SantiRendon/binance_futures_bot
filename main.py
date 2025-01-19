from binance.client import Client
from binance import ThreadedWebsocketManager
import threading
import time
import asyncio

# API keys (example mock keys)
api_key = '7de4ca57d53aac719f84f4f2f1ceee269512766e19734dca3beaec464c92a2d1'
api_secret = '15122b41c53e6293bd122333bf8f31a12e7f8b876595a290473487e38a25d3f0'

# Connect to Binance Futures testnet
client = Client(api_key, api_secret, testnet=True)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi/v1"

def list_available_pairs():
    """List all available trading pairs on Binance Futures."""
    try:
        exchange_info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
        return symbols
    except Exception as e:
        print(f"Error fetching available pairs: {e}")
        return []

def get_current_price(symbol):
    """Fetch the current market price for a single trading pair."""
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None

def get_current_prices(symbols):
    """Fetch the current prices for multiple trading pairs."""
    prices = {}
    for symbol in symbols:
        price = get_current_price(symbol)
        if price is not None:
            prices[symbol] = price
    return prices

def get_historical_prices(symbol, interval, start_time=None, end_time=None, limit=100):
    """Fetch historical price data (candlesticks) for a given trading pair."""
    try:
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

def calculate_stop_loss_take_profit(entry_price, stop_loss_pct, take_profit_pct, side):
    """Calculate stop loss and take profit prices based on the entry price and percentages."""
    stop_loss = (
        entry_price * (1 - stop_loss_pct / 100) if side == "BUY"
        else entry_price * (1 + stop_loss_pct / 100)
    )
    take_profit = (
        entry_price * (1 + take_profit_pct / 100) if side == "BUY"
        else entry_price * (1 - take_profit_pct / 100)
    )
    return round(stop_loss, 2), round(take_profit, 2)

def place_market_order(symbol, side, quantity):
    """Place a market order."""
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity
        )
        return order
    except Exception as e:
        print(f"Error placing market order for {symbol}: {e}")
        return None

def place_oco_order(symbol, side, quantity, stop_loss, take_profit):
    """Place an OCO order (stop loss and take profit)."""
    try:
        oco_order = client.futures_create_oco_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            quantity=quantity,
            price=take_profit,  # Take profit price
            stopPrice=stop_loss,  # Stop loss trigger price
            stopLimitPrice=stop_loss,  # Stop loss execution price
            stopLimitTimeInForce="GTC"
        )
        return oco_order
    except Exception as e:
        print(f"Error placing OCO order for {symbol}: {e}")
        return None

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
            entry_price = get_current_price(symbol)
            if entry_price is None:
                print("Error: Unable to fetch market price.")
                return

        print(f"Market order executed: {side} {quantity} {symbol} at ~{entry_price}")

        # Calculate stop loss and take profit prices
        stop_loss, take_profit = calculate_stop_loss_take_profit(entry_price, stop_loss_pct, take_profit_pct, side)

        # Place the market order
        place_market_order(symbol, side, quantity)

        # Place the OCO order for stop loss and take profit
        oco_order = place_oco_order(symbol, side, quantity, stop_loss, take_profit)
        if oco_order:
            print(f"OCO order placed with Stop Loss at {stop_loss} and Take Profit at {take_profit}")

    except Exception as e:
        print(f"Error executing trade: {e}")

# WebSocket para la estrategia de precios
def start_strategy_monitor(symbol, interval, callback):
    def handle_message(msg):
        if msg['e'] == 'kline':
            kline = msg['k']
            close_price = float(kline['c'])  # Precio de cierre de la vela
            print(f"Precio actualizado: {close_price}")
            callback(close_price)

    # Crear el WebSocket manager
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret, testnet=True)
    twm.start()

    # Suscribirse al stream de kline para recibir los precios
    twm.start_kline_socket(callback=handle_message, symbol=symbol, interval=interval)

    print(f"WebSocket de estrategia iniciado para {symbol} ({interval}).")
    return twm

# WebSocket para monitorear las órdenes abiertas
def start_order_monitor(symbol, client):
    def handle_message(msg):
        try:
            if msg['e'] == 'ORDER_TRADE_UPDATE':  # Evento de actualización de orden
                order_status = msg['o']['X']  # Estado de la orden (FILLED, NEW)
                order_side = msg['o']['S']  # Lado de la orden (BUY o SELL)
                order_id = msg['o']['i']  # ID de la orden
                symbol = msg['o']['s']  # Símbolo de la orden

                if order_status == 'FILLED':  # Si la orden está ejecutada
                    print(f"Orden ejecutada: {order_side} {symbol}, ID: {order_id}")

                    # Obtener todas las órdenes abiertas
                    open_orders = client.futures_get_open_orders(symbol=symbol)
                    for order in open_orders:
                        if order['orderId'] != order_id:  # Cancelar otras órdenes
                            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
                            print(f"Cancelada la orden opuesta: {order['orderId']}")

        except Exception as e:
            print(f"Error al manejar el mensaje: {e}")

    # Crear el WebSocket manager
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret, testnet=True)
    twm.start()

    # Obtener el key de escucha y suscribirse al stream de datos del usuario
    listen_key = client.futures_stream_get_listen_key()
    twm.start_futures_user_socket(callback=handle_message)

    print("WebSocket de órdenes iniciado. Escuchando actualizaciones...")
    return twm

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Función de estrategia (por ahora solo imprime el precio)
    def strategy_callback(price):
        print(f"Precio recibido en la estrategia: {price}")
        # Aquí puedes agregar tu lógica de estrategia (cuando la tengas)

    # Empezar el WebSocket para monitorear el precio
    strategy_thread = threading.Thread(target=start_strategy_monitor, args=("BTCUSDT", "5m", strategy_callback))
    strategy_thread.start()

    # Empezar el WebSocket para monitorear las órdenes
    order_thread = threading.Thread(target=start_order_monitor, args=("BTCUSDT", client))
    order_thread.start()

    # Mantener el hilo principal vivo
    while True:
        time.sleep(1)
