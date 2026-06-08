import os
import ccxt
import time
import logging
import telebot
import pandas as pd
import ta

from threading import Thread

# =========================================
# TELEGRAM CONFIG
# =========================================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

# =========================================
# FIX 409 ERROR
# =========================================

try:
    bot.remove_webhook()
    time.sleep(2)
except:
    pass

# =========================================
# LOGGING
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =========================================
# KUCOIN EXCHANGE
# =========================================

exchange = ccxt.kucoin({
    'enableRateLimit': True,
    'rateLimit': 2000,
})

# =========================================
# SETTINGS
# =========================================

RSI_LIMIT = 33
ADX_MIN = 20

SCAN_DELAY = 15

last_alerts = {}

# =========================================
# COINS LIST
# =========================================

coins = [

    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "DOT/USDT",
    "MATIC/USDT",
    "TRX/USDT",
    "TON/USDT",
    "SHIB/USDT",
    "PEPE/USDT",
    "WIF/USDT",
    "NEAR/USDT",
    "APT/USDT",
    "ARB/USDT",
    "OP/USDT",
    "ATOM/USDT",
    "INJ/USDT",
    "SEI/USDT",
    "SUI/USDT",
    "FET/USDT",
    "TAO/USDT",
    "FIL/USDT",
    "ETC/USDT",
    "ICP/USDT",
    "HBAR/USDT",
    "AAVE/USDT",
    "GALA/USDT",
    "JUP/USDT",
    "RUNE/USDT",
    "TIA/USDT",
    "PYTH/USDT",
    "ORDI/USDT",
    "ENA/USDT",
    "AR/USDT",
    "FLOW/USDT",
    "KAS/USDT",
    "EGLD/USDT",
    "ALGO/USDT",
    "SAND/USDT",
    "MANA/USDT",
    "CRV/USDT",
    "UNI/USDT",
    "LDO/USDT",
    "XLM/USDT",
    "VET/USDT",
    "THETA/USDT",
    "EOS/USDT",
    "AXS/USDT",
    "CHZ/USDT",
    "FTM/USDT",
    "DYDX/USDT",
    "BLUR/USDT"

]

# =========================================
# TELEGRAM COMMANDS
# =========================================

@bot.message_handler(commands=['start', 'status'])
def send_status(message):

    msg = (
        "🤖 BOT STATUS REPORT\n\n"
        "✅ Scanner Active\n"
        "📈 Strategy: RSI < 33 + ADX > 20\n"
        "⚡ Stable Sniper Mode Running\n"
        "🔥 Top Coins Monitoring Active"
    )

    bot.reply_to(message, msg)

# =========================================
# ANALYSIS FUNCTION
# =========================================

def analyze_coin(symbol):

    global last_alerts

    try:

        ohlcv = exchange.fetch_ohlcv(
            symbol,
            timeframe='15m',
            limit=120
        )

        if not ohlcv or len(ohlcv) < 50:
            return None

        closes = [x[4] for x in ohlcv]
        highs = [x[2] for x in ohlcv]
        lows = [x[3] for x in ohlcv]
        volumes = [x[5] for x in ohlcv]

        price = closes[-1]

        # =====================================
        # RSI
        # =====================================

        rsi = ta.momentum.RSIIndicator(
            pd.Series(closes),
            window=14
        ).rsi().iloc[-1]

        # =====================================
        # EMA TREND
        # =====================================

        ema50 = ta.trend.EMAIndicator(
            pd.Series(closes),
            window=50
        ).ema_indicator().iloc[-1]

        ema200 = ta.trend.EMAIndicator(
            pd.Series(closes),
            window=200
        ).ema_indicator().iloc[-1]

        trend_ok = ema50 > ema200

        # =====================================
        # ADX
        # =====================================

        adx = ta.trend.ADXIndicator(
            pd.Series(highs),
            pd.Series(lows),
            pd.Series(closes),
            window=14
        ).adx().iloc[-1]

        # =====================================
        # VOLUME SPIKE
        # =====================================

        avg_volume = sum(volumes[-20:-1]) / 19

        if avg_volume == 0:
            return None

        volume_ratio = volumes[-1] / avg_volume

        # =====================================
        # FINAL SIGNAL CONDITIONS
        # =====================================

        if (
            rsi < RSI_LIMIT
            and adx > ADX_MIN
            and trend_ok
            and volume_ratio > 1.5
        ):

            now = time.time()

            # =================================
            # ALERT COOLDOWN
            # =================================

            if (
                symbol in last_alerts
                and now - last_alerts[symbol] < 7200
            ):
                return None

            last_alerts[symbol] = now

            # =================================
            # SIGNAL MESSAGE
            # =================================

            signal = f'''
🚨 SNIPER SIGNAL

🪙 Coin: {symbol}

💰 Price: {price:.6f}

📊 RSI: {rsi:.2f}
🔥 ADX: {adx:.2f}
📈 Volume Spike: {volume_ratio:.2f}x

🎯 Strategy:
RSI Oversold Bounce
Trend Confirmation
Momentum Strength

⚠️ Manage Risk Properly
'''

            return signal

    except ccxt.RateLimitExceeded:

        logging.warning(
            "KUCOIN RATE LIMIT HIT"
        )

        time.sleep(90)

    except Exception as e:

        logging.error(
            f"{symbol} Error: {e}"
        )

    return None

# =========================================
# MARKET SCANNER LOOP
# =========================================

def analyze_market():

    while True:

        try:

            logging.info(
                f"Scanning {len(coins)} coins..."
            )

            for symbol in coins:

                try:

                    signal = analyze_coin(symbol)

                    if signal:

                        bot.send_message(
                            CHAT_ID,
                            signal
                        )

                        logging.info(
                            f"Signal Sent: {symbol}"
                        )

                    time.sleep(SCAN_DELAY)

                except Exception as e:

                    logging.error(
                        f"{symbol} Scan Error: {e}"
                    )

                    continue

        except Exception as e:

            logging.error(
                f"Main Loop Error: {e}"
            )

            time.sleep(60)

# =========================================
# START MARKET THREAD
# =========================================

market_thread = Thread(
    target=analyze_market
)

market_thread.daemon = True

market_thread.start()

# =========================================
# START BOT
# =========================================

print("BOT RUNNING...")

while True:

    try:

        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60,
            skip_pending=True
        )

    except Exception as e:

        logging.error(
            f"Polling Error: {e}"
        )

        time.sleep(15)
