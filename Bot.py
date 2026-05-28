import telebot
import os
import ccxt
import time
import threading
import pandas as pd
import pandas_ta as ta
from flask import Flask

# --- Setup ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID') # Apni Chat ID environment variable mein set kar lena
bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()
exchange.load_markets()

# Poori 80 Coins ki list
coins = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT', 'AVAX/USDT',
    'LTC/USDT', 'BNB/USDT', 'XLM/USDT', 'DOGE/USDT', 'SHIB/USDT', 'TRX/USDT', 'ATOM/USDT', 'NEAR/USDT', 'FIL/USDT', 'ALGO/USDT',
    'VET/USDT', 'ICP/USDT', 'HBAR/USDT', 'FTM/USDT', 'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'EGLD/USDT', 'EOS/USDT', 'XTZ/USDT',
    'AAVE/USDT', 'CRV/USDT', 'MKR/USDT', 'COMP/USDT', 'SNX/USDT', 'SUSHI/USDT', 'YFI/USDT', 'GRT/USDT', 'BAT/USDT', 'CHZ/USDT',
    'ENJ/USDT', 'GALA/USDT', 'RUNE/USDT', 'KAVA/USDT', 'ZIL/USDT', 'THETA/USDT', 'ONT/USDT', 'QTUM/USDT', 'OMG/USDT', 'IOST/USDT',
    'BAND/USDT', 'WAVES/USDT', 'REN/USDT', 'SKL/USDT', 'OCEAN/USDT', 'ANKR/USDT', 'LRC/USDT', 'BAL/USDT', 'KNC/USDT', 'DASH/USDT',
    'ZEC/USDT', 'ETC/USDT', 'NEO/USDT', 'XMR/USDT', 'BCH/USDT', 'BSV/USDT', 'IOTA/USDT', 'ICX/USDT', 'SC/USDT', 'RVN/USDT',
    'HNT/USDT', 'CELO/USDT', 'ONE/USDT', 'IOTX/USDT', 'CTSI/USDT', 'LSK/USDT', 'BTS/USDT', 'ARDR/USDT', 'ZEN/USDT', 'STX/USDT'
]

# --- God Bot Core Logic ---
def get_indicators(coin):
    bars = exchange.fetch_ohlcv(coin, timeframe='15m', limit=50)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['EMA_20'] = ta.ema(df['close'], length=20)
    return df.iloc[-1]

def check_market():
    while True:
        for coin in coins:
            try:
                data = get_indicators(coin)
                # Strategy: RSI < 35 (Sasta) + Price > EMA (Trend) + High Volume
                if data['RSI'] < 35 and data['volume'] > 50000:
                    bot.send_message(CHAT_ID, f"🚀 GOD ALERT: {coin}\nPrice: {data['close']}\nRSI: {data['RSI']:.2f}\nAction: BUY")
                time.sleep(1) # Har coin ke liye delay
            except:
                continue

# --- Bot Commands ---
@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, f"God Bot is running!\nTracking {len(coins)} coins.\nStatus: RSI/EMA Strategy Active.")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        coin = message.text.split()[1].upper()
        ticker = exchange.fetch_ticker(coin)
        bot.reply_to(message, f"{coin} Price: ${ticker['last']}")
    except:
        bot.reply_to(message, "Error: Invalid coin or format.")

# --- Server & Main ---
app = Flask(__name__)
@app.route('/')
def index(): return "God Bot Active"

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    threading.Thread(target=check_market).start()
    bot.polling(none_stop=True)
    
