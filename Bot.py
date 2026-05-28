import os
import time
import telebot
import threading
import logging
import traceback
import requests
import ccxt
import pandas as pd

from flask import Flask

# =====================================================
# CONFIG
# =====================================================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

TIMEFRAME = '15m'
HIGHER_TIMEFRAME = '1h'

SCAN_DELAY = 5
COOLDOWN = 10800

RSI_LIMIT = 33
ADX_LIMIT = 20

# =====================================================
# TELEGRAM BOT
# =====================================================

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="Markdown"
)

# =====================================================
# REMOVE WEBHOOK
# =====================================================

try:

    bot.remove_webhook()

except Exception:

    pass

time.sleep(2)

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =====================================================
# FLASK
# =====================================================

app = Flask(__name__)

@app.route('/')
def home():

    return "BOT ACTIVE"

# =====================================================
# COMMANDS
# =====================================================

@bot.message_handler(commands=['start'])
def start_command(message):

    bot.reply_to(
        message,
        "✅ *BOT ACTIVE*\n\n🚀 AI Market Scanner Running 24/7",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def status_command(message):

    status_msg = (
        "🤖 *BOT STATUS REPORT*\n\n"
        "✅ *Scanner:* Active\n"
        "📈 *Strategy:* RSI < 33 | ADX > 20\n"
        "🐋 *Whale Detection:* Enabled\n"
        "⏳ *Scanning:* Live Market 24/7\n\n"
        "🚨 Signal milte hi alert aayega."
    )

    bot.reply_to(
        message,
        status_msg,
        parse_mode="Markdown"
    )

# =====================================================
# STARTUP MESSAGE
# =====================================================

try:

    bot.send_message(
        CHAT_ID,
        "✅ BOT STARTED SUCCESSFULLY\n📡 Market Scanner Online"
    )

    print("TELEGRAM CONNECTED")

except Exception as e:

    print(f"TELEGRAM ERROR: {e}")

# =====================================================
# KUCOIN EXCHANGE
# =====================================================

exchange = ccxt.kucoin({
    'enableRateLimit': True,
    'rateLimit': 1200,
    'timeout': 30000,
    'options': {
        'adjustForTimeDifference': True
    }
})

# =====================================================
# COINS
# =====================================================

coins = [

    'BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT',
    'ADA/USDT','DOGE/USDT','AVAX/USDT','LINK/USDT',
    'DOT/USDT','ATOM/USDT','NEAR/USDT','FIL/USDT',
    'LTC/USDT','TRX/USDT','ETC/USDT','ICP/USDT',
    'HBAR/USDT','SAND/USDT','AAVE/USDT','CRV/USDT',

    'SNX/USDT','SUSHI/USDT','GRT/USDT','CHZ/USDT',
    'RUNE/USDT','THETA/USDT','LRC/USDT','DASH/USDT',
    'ZEC/USDT','NEO/USDT','XMR/USDT','IOTA/USDT',
    'ICX/USDT','HNT/USDT','IOTX/USDT','STX/USDT',

    'ARB/USDT','OP/USDT','APT/USDT','INJ/USDT',
    'SEI/USDT','TIA/USDT','PEPE/USDT','BONK/USDT',
    'WIF/USDT','FLOKI/USDT','RNDR/USDT','JUP/USDT',

    'PYTH/USDT','STRK/USDT','BLUR/USDT','DYDX/USDT',
    'GMX/USDT','SUI/USDT','CFX/USDT','MASK/USDT',
    'HOOK/USDT','MAGIC/USDT','ACH/USDT','API3/USDT'
]

# =====================================================
# MEMORY
# =====================================================

last_alerts = {}

# =====================================================
# MARKET SENTIMENT
# =====================================================

def get_market_sentiment():

    try:

        response = requests.get(
            "https://api.alternative.me/fng/",
            timeout=10
        )

        return int(
            response.json()['data'][0]['value']
        )

    except Exception:

        return 50

# =====================================================
# RSI
# =====================================================

def calculate_rsi(prices, period=14):

    delta = pd.Series(prices).diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    value = float(rsi.iloc[-1])

    if pd.isna(value):

        return 50

    return value

# =====================================================
# EMA
# =====================================================

def calculate_ema(prices, period):

    ema = pd.Series(prices).ewm(
        span=period,
        adjust=False
    ).mean()

    return float(ema.iloc[-1])

# =====================================================
# ATR
# =====================================================

def calculate_atr(ohlcv, period=14):

    df = pd.DataFrame(
        ohlcv,
        columns=['t','o','h','l','c','v']
    )

    tr = pd.concat([

        df['h'] - df['l'],
        abs(df['h'] - df['c'].shift()),
        abs(df['l'] - df['c'].shift())

    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    value = float(atr.iloc[-1])

    if pd.isna(value):

        return 0

    return value

# =====================================================
# ADX
# =====================================================

def calculate_adx(ohlcv, period=14):

    df = pd.DataFrame(
        ohlcv,
        columns=['t','o','h','l','c','v']
    )

    plus_dm = df['h'].diff()
    minus_dm = df['l'].diff() * -1

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr = pd.concat([

        df['h'] - df['l'],
        abs(df['h'] - df['c'].shift()),
        abs(df['l'] - df['c'].shift())

    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = (
        100 *
        (plus_dm.rolling(period).mean() / atr)
    )

    minus_di = (
        100 *
        (minus_dm.rolling(period).mean() / atr)
    )

    dx = (
        abs(plus_di - minus_di) /
        abs(plus_di + minus_di)
    ) * 100

    adx = dx.rolling(period).mean()

    value = float(adx.iloc[-1])

    if pd.isna(value):

        return 0

    return value

# =====================================================
# SIGNAL FUNCTION
# =====================================================

def send_signal(
    symbol,
    price,
    rsi,
    atr,
    adx,
    sentiment,
    whale
):

    sl = price - (atr * 1.5)

    tp1 = price + (atr * 2)
    tp2 = price + (atr * 4)
    tp3 = price + (atr * 6)

    whale_text = (
        "\n🐋 Whale Volume Detected"
        if whale else ""
    )

    message = f"""

🚨 *ADVANCED AI SIGNAL*

🪙 {symbol}

💰 Entry: `{price:.5f}`

📉 RSI: `{rsi:.2f}`
📈 ADX: `{adx:.2f}`

😨 Fear & Greed: `{sentiment}`

{whale_text}

🎯 TP1: `{tp1:.5f}`
🎯 TP2: `{tp2:.5f}`
🎯 TP3: `{tp3:.5f}`

🛑 SL: `{sl:.5f}`

"""

    bot.send_message(
        CHAT_ID,
        message
    )

# =====================================================
# MAIN ENGINE
# =====================================================

def analyze_market():

    while True:

        try:

            logging.info("Scanning Market")

            sentiment = get_market_sentiment()

            # EXTREME GREED FILTER
            if sentiment >= 80:

                logging.warning(
                    "Extreme Greed Detected"
                )

                time.sleep(300)

                continue

            # BTC SAFETY FILTER
            btc = exchange.fetch_ohlcv(
                'BTC/USDT',
                TIMEFRAME,
                limit=3
            )

            btc_change = (
                btc[-1][4] - btc[-2][4]
            ) / btc[-2][4]

            if btc_change < -0.025:

                logging.warning(
                    "BTC Dump Protection Active"
                )

                time.sleep(180)

                continue

            # COINS LOOP
            for symbol in coins:

                try:

                    # COOLDOWN
                    if (
                        time.time() -
                        last_alerts.get(symbol, 0)
                    ) < COOLDOWN:

                        continue

                    # FETCH DATA
                    ohlcv = exchange.fetch_ohlcv(
                        symbol,
                        TIMEFRAME,
                        limit=150
                    )

                    htf = exchange.fetch_ohlcv(
                        symbol,
                        HIGHER_TIMEFRAME,
                        limit=150
                    )

                    if not ohlcv or not htf:

                        continue

                    closes = [x[4] for x in ohlcv]
                    volumes = [x[5] for x in ohlcv]

                    htf_closes = [x[4] for x in htf]

                    price = closes[-1]

                    # INDICATORS
                    rsi = calculate_rsi(closes)

                    atr = calculate_atr(ohlcv)

                    adx = calculate_adx(ohlcv)

                    ema50 = calculate_ema(closes, 50)
                    ema200 = calculate_ema(closes, 200)

                    htf_ema50 = calculate_ema(htf_closes, 50)
                    htf_ema200 = calculate_ema(htf_closes, 200)

                    # TREND FILTER
                    trend_ok = (

                        ema50 > ema200 and
                        htf_ema50 > htf_ema200 and
                        price > ema50

                    )

                    # VOLUME FILTER
                    avg_volume = (
                        sum(volumes[-15:-1]) / 14
                    )

                    volume_spike = (
                        volumes[-1] >
                        avg_volume * 2.5
                    )

                    whale = (
                        volumes[-1] >
                        avg_volume * 4
                    )

                    # FINAL SIGNAL
                    signal = (

                        rsi < RSI_LIMIT and
                        adx > ADX_LIMIT and
                        volume_spike and
                        trend_ok and
                        atr > 0

                    )

                    if signal:

                        send_signal(
                            symbol,
                            price,
                            rsi,
                            atr,
                            adx,
                            sentiment,
                            whale
                        )

                        last_alerts[symbol] = time.time()

                    time.sleep(SCAN_DELAY)

                except Exception:

                    logging.error(
                        traceback.format_exc()
                    )

                    time.sleep(3)

        except Exception:

            logging.error(
                traceback.format_exc()
            )

            time.sleep(20)

# =====================================================
# FLASK THREAD
# =====================================================

def run_flask():

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 10000))
    )

# =====================================================
# MAIN START
# =====================================================

if __name__ == "__main__":

    threading.Thread(
        target=run_flask,
        daemon=True
    ).start()

    threading.Thread(
        target=analyze_market,
        daemon=True
    ).start()

    print("BOT POLLING STARTED")

    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30,
        skip_pending=True
    )
