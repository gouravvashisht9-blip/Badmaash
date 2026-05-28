import telebot
import os
import ccxt
import time
import threading
from flask import Flask

# --- Setup ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()
# Market load karna zaroori hai
exchange.load_markets()

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

# --- Calculation Logic (No extra libraries needed) ---
def get_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- Monitoring ---
def check_market():
    while True:
        for coin in coins:
            try:
                ohlcv = exchange.fetch_ohlcv(coin, '15m', limit=20)
                closes = [bar[4] for bar in ohlcv]
                rsi = get_rsi(closes)
                if rsi < 35:
                    bot.send_message(CHAT_ID, f"🚀 GOD ALERT: {coin}\nRSI: {rsi:.2f}\nPrice: {closes[-1]}")
                time.sleep(2)
            except Exception:
                continue

# --- Bot Commands ---
@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, f"God Bot Active. Monitoring {len(coins)} coins.")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        coin = message.text.split()[1].upper()
        ticker = exchange.fetch_ticker(coin)
        bot.reply_to(message, f"{coin} Price: ${ticker['last']}")
    except:
        bot.reply_to(message, "Invalid Coin.")

# --- Server & Run ---
app = Flask(__name__)
@app.route('/')
def index(): return "Bot is Alive"

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    threading.Thread(target=check_market).start()
    bot.polling(none_stop=True)
    
