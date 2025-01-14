from binance.client import Client
from datetime import datetime, timezone
import csv

# Claves API de tu cuenta mock
api_key = '7de4ca57d53aac719f84f4f2f1ceee269512766e19734dca3beaec464c92a2d1'
api_secret = '15122b41c53e6293bd122333bf8f31a12e7f8b876595a290473487e38a25d3f0'

# Connect to the Binance Futures testnet
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
    """
    Fetch historical price data (candlesticks) for a given trading pair.

    Args:
        symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
        interval (str): The interval for candlesticks (e.g., '1m', '5m', '1h', '1d').
        start_time (str or int, optional): Start time in milliseconds or human-readable format (e.g., '2023-01-01').
        end_time (str or int, optional): End time in milliseconds or human-readable format (e.g., '2023-01-31').
        limit (int, optional): Number of data points to fetch (default is 100, max is 1000).

    Returns:
        list: List of candlestick data with fields [open_time, open, high, low, close, volume, ...].
    """
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

def export_to_csv(klines, filename):
    """
    Export kline (candlestick) data to a CSV file.

    Args:
        klines (list): List of kline data from Binance.
        filename (str): Name of the CSV file to save the data.

    Explanation of the CSV columns:
        * Open Time: Start time of the candlestick (formatted as YYYY-MM-DD HH:MM:SS).
        * Open, High, Low, Close: Prices during the candlestick.
        * Volume: Volume traded during the candlestick.
        * Close Time: End time of the candlestick.
        * Quote Asset Volume: Volume in quote asset terms.
        * Number of Trades: Total trades during the candlestick.
        * Taker Buy Base Volume: Volume of taker buy trades in base asset.
        * Taker Buy Quote Volume: Volume of taker buy trades in quote asset.
        * Ignore: Reserved field (not usually relevant).
    """
    headers = [
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Volume", "Taker Buy Quote Volume", "Ignore"
    ]
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write the header row
        for kline in klines:
            # Format Open Time and Close Time as readable dates
            kline[0] = datetime.fromtimestamp(kline[0] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            kline[6] = datetime.fromtimestamp(kline[6] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow(kline)  # Write each kline as a row

if __name__ == "__main__":
    # List all available pairs
    print("Fetching available trading pairs on Binance Futures...")
    available_pairs = list_available_pairs()
    print(f"Available pairs: {available_pairs}")

    # Define the pairs to fetch prices for
    pairs_to_check = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # Change these as needed
    print(f"Fetching prices for: {pairs_to_check}")

    btc_historical = get_historical_prices(pairs_to_check[0], '5m', start_time=None, end_time=None, limit=100)
    print("======================================================")
    print(btc_historical)
    export_to_csv(btc_historical, "btc_historical_5m.csv")
    print("======================================================")
    # Get the current prices for the selected pairs
    prices = get_current_prices(pairs_to_check)
    print("Current prices:")
    for pair, price in prices.items():
        print(f"{pair}: {price}")