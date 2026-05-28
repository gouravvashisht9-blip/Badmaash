import ccxt
import time
import requests
import os
import threading
import telebot
from flask import Flask

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = '8812437138'
exchange = ccxt.binance()
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Coins list
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'UNI/USDT', 'SHIB/USDT', 'PEPE/USDT']
active_trades = {}

# --- 1. DUMMY WEB SERVER (Port Error Fix) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. INTERACTION (Telegram Bot) ---
@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, f"Bot is running! Active trades: {len(active_trades)}")

def run_bot():
    bot.infinity_polling()

# --- 3. TRADING LOGIC ---
def send_msg(msg):
    try: bot.send_message(CHAT_ID, msg)
    except: pass

def get_indicators(coin):
    try:
        ohlcv = exchange.fetch_ohlcv(coin, timeframe='1h', limit=200)
        closes = [x[4] for x in ohlcv]
        curr = closes[-1]
        ema200 = sum(closes[-200:]) / 200
        return curr, ema200, True 
    except: return 0, 0, False

# --- STARTUP ---
threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=run_bot, daemon=True).start()

send_msg("Bot Started - Full Secure Interactive Mode.")

while True:
    try:
        for coin in coins:
            curr, ema, breakout = get_indicators(coin)
            # Tera trading logic yahan...
            time.sleep(2)
        time.sleep(60)
    except:
        time.sleep(60)
