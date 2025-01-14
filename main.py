from binance.client import Client
from datetime import datetime

# Claves API de tu cuenta mock
api_key = '7de4ca57d53aac719f84f4f2f1ceee269512766e19734dca3beaec464c92a2d1'
api_secret = '15122b41c53e6293bd122333bf8f31a12e7f8b876595a290473487e38a25d3f0'

# Connect to the Binance Futures testnet
client = Client(api_key, api_secret, testnet=True)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi/v1"

# Cambiar a testnet
exchange.set_sandbox_mode(True)

# Verificar conexión obteniendo el balance
try:
    balance = exchange.fetch_balance()
    print("Conexión exitosa. Balance de la cuenta mock:")
    print(balance)
except Exception as e:
    print("Error al conectar:", e)

# Obtener el precio actual de BTC/USDT en futuros
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"Precio actual BTC/USDT: {ticker['last']}")
except Exception as e:
    print("Error al obtener el precio:", e)

# Colocar una orden de mercado (compra o venta)
try:
    symbol = 'BTC/USDT'
    order = exchange.create_market_order(
        symbol=symbol,
        side='sell',  # 'buy' para LONG, 'sell' para SHORT
        amount=0.01,  # Cantidad de BTC
    )
    print("Orden ejecutada:", order)
except Exception as e:
    print("Error al realizar la orden:", e)
