import telebot
import os
import ccxt
import time

# --- Setup ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()

# Tumhari 80 coins ki list (Yahan apne coins check kar lena)
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT', 'AVAX/USDT'] 

# --- Commands ---
@bot.message_handler(commands=['start', 'status'])
def status(message):
    bot.reply_to(message, f"Bot is running! Full Secure Interactive Mode.\nTracking {len(coins)} coins.\nActive trades: 0")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        parts = message.text.split()
        if len(parts) > 1:
            coin = parts[1].upper()
            ticker = exchange.fetch_ticker(coin)
            bot.reply_to(message, f"{coin} Price: ${ticker['last']}")
        else:
            bot.reply_to(message, "Please specify a coin, e.g., /price BTC/USDT")
    except Exception as e:
        bot.reply_to(message, "Error: Invalid coin or check format.")

# --- Main Logic ---
def run_bot():
    print("Bot Started - Full Secure Interactive Mode.")
    # Yahan tumhara main trading loop aayega
    while True:
        try:
            # Yahan tumhara logic chalta rahega
            time.sleep(10)
        except Exception as e:
            print(f"Error in loop: {e}")
            time.sleep(10)

if __name__ == '__main__':
    # Flask dummy server for Render
    import threading
    from flask import Flask
    app = Flask(__name__)
    @app.route('/')
    def index(): return "Bot is Alive"
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    
    # Bot start
    bot.polling(none_stop=True)
    
