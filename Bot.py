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
# REMOVE WEBHOOK (FIX 409 ERROR)
# =========================================

bot.remove_webhook()
time.sleep(2)

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

RSI_LIMIT = 37
ADX_MIN = 20
VOLUME_SPIKE = 2.5
MIN_PRICE_CHANGE = 1.5

SCAN_DELAY = 15

last_alerts = {}

# =========================================
# TELEGRAM COMMANDS
# =========================================

@bot.message_handler(commands=['start', 'status'])
def send_status(message):

    msg = (
        "🤖 BOT STATUS REPORT\n\n"
        "✅ Scanner Active\n"
        "🚀 Explosive Coin Detection ON\n"
        "📊 Multi-Timeframe Analysis ON\n"
        "🐋 Whale Candle Detection ON\n"
        "🔥 Dynamic ATR TP/SL ON\n"
        "⚡ Auto Market Scanner Running"
    )

    bot.reply_to(message, msg)

# =========================================
# FETCH TOP COINS
# =========================================

def get_top_coins():

    try:

        markets = exchange.load_markets()

        pairs = []

        for symbol in markets:

            try:

                if (
                    symbol.endswith('/USDT')
                    and markets[symbol]['active']
                    and ':' not in symbol
                ):

                    pairs.append(symbol)

            except:
                pass

        tickers = exchange.fetch_tickers(pairs)

        ranked = sorted(
            pairs,
            key=lambda x: tickers[x]['quoteVolume']
            if tickers[x]['quoteVolume']
            else 0,
            reverse=True
        )

        return ranked[:120]

    except Exception as e:

        logging.error(f"Coin Fetch Error: {e}")

        return []

# =========================================
# MAIN ANALYSIS
# =========================================

def explosive_scan(symbol):

    global last_alerts

    try:

        # =====================================
        # 15M DATA
        # =====================================

        ohlcv = exchange.fetch_ohlcv(
            symbol,
            timeframe='15m',
            limit=220
        )

        if not ohlcv or len(ohlcv) < 50:
            return None

        closes = [x[4] for x in ohlcv]
        highs = [x[2] for x in ohlcv]
        lows = [x[3] for x in ohlcv]
        volumes = [x[5] for x in ohlcv]

        price = closes[-1]

        # =====================================
        # BTC TREND FILTER
        # =====================================

        btc_ohlcv = exchange.fetch_ohlcv(
            'BTC/USDT',
            timeframe='15m',
            limit=50
        )

        btc_closes = [x[4] for x in btc_ohlcv]

        btc_ema20 = ta.trend.EMAIndicator(
            pd.Series(btc_closes),
            window=20
        ).ema_indicator().iloc[-1]

        btc_price = btc_closes[-1]

        btc_trend_ok = btc_price > btc_ema20

        # =====================================
        # RSI
        # =====================================

        rsi = ta.momentum.RSIIndicator(
            pd.Series(closes),
            window=14
        ).rsi().iloc[-1]

        # =====================================
        # EMA
        # =====================================

        ema50 = ta.trend.EMAIndicator(
            pd.Series(closes),
            window=50
        ).ema_indicator().iloc[-1]

        ema200 = ta.trend.EMAIndicator(
            pd.Series(closes),
            window=200
        ).ema_indicator().iloc[-1]

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
        # ATR
        # =====================================

        atr = ta.volatility.AverageTrueRange(
            pd.Series(highs),
            pd.Series(lows),
            pd.Series(closes),
            window=14
        ).average_true_range().iloc[-1]

        atr_percent = (atr / price) * 100

        # =====================================
        # VOLUME SPIKE
        # =====================================

        avg_volume = sum(volumes[-20:-1]) / 19

        if avg_volume == 0:
            return None

        volume_ratio = volumes[-1] / avg_volume

        # =====================================
        # BREAKOUT
        # =====================================

        recent_high = max(highs[-20:])

        breakout = price >= recent_high * 0.995

        # =====================================
        # PRICE MOMENTUM
        # =====================================

        change_15m = (
            (price - closes[-5]) / closes[-5]
        ) * 100

        change_1h = (
            (price - closes[-20]) / closes[-20]
        ) * 100

        # =====================================
        # WHALE CANDLE
        # =====================================

        candle_size = (
            (ohlcv[-1][2] - ohlcv[-1][3])
            / price
        ) * 100

        # =====================================
        # 1H CONFIRMATION
        # =====================================

        ohlcv_1h = exchange.fetch_ohlcv(
            symbol,
            timeframe='1h',
            limit=50
        )

        closes_1h = [x[4] for x in ohlcv_1h]

        ema_1h = ta.trend.EMAIndicator(
            pd.Series(closes_1h),
            window=20
        ).ema_indicator().iloc[-1]

        trend_1h_ok = closes_1h[-1] > ema_1h

        # =====================================
        # FINAL FILTER
        # =====================================

        if (
            rsi < RSI_LIMIT
            and adx > ADX_MIN
            and volume_ratio > VOLUME_SPIKE
            and breakout
            and change_15m > MIN_PRICE_CHANGE
            and ema50 > ema200
            and btc_trend_ok
            and trend_1h_ok
            and candle_size > 2
            and change_1h < 18
        ):

            # =================================
            # ALERT COOLDOWN
            # =================================

            now = time.time()

            if (
                symbol in last_alerts
                and now - last_alerts[symbol] < 7200
            ):
                return None

            last_alerts[symbol] = now

            # =================================
            # SCORE
            # =================================

            score = 0

            if volume_ratio > 4:
                score += 3

            if adx > 25:
                score += 2

            if atr_percent > 4:
                score += 2

            if change_15m > 3:
                score += 3

            # =================================
            # SIGNAL STRENGTH
            # =================================

            if score >= 8:
                strength = "🚀 EXPLOSIVE"

            elif score >= 5:
                strength = "⚡ STRONG"

            else:
                strength = "✅ NORMAL"

            # =================================
            # DYNAMIC TP/SL
            # =================================

            tp1 = atr_percent * 1.5
            tp2 = atr_percent * 3
            tp3 = atr_percent * 5

            sl = atr_percent * 1.2

            # =================================
            # SIGNAL MESSAGE
            # =================================

            signal = f'''
🚨 EXPLOSIVE SIGNAL

🪙 Coin: {symbol}

💰 Price: {price:.6f}

📈 15m Change: {change_15m:.2f}%
📊 Volume Spike: {volume_ratio:.2f}x
🔥 ADX: {adx:.2f}
⚡ RSI: {rsi:.2f}

🚀 Strength: {strength}

🎯 TP1: +{tp1:.2f}%
🎯 TP2: +{tp2:.2f}%
🎯 TP3: +{tp3:.2f}%

🛑 SL: -{sl:.2f}%

⚠️ Use Proper Risk Management
'''

            return signal

    except ccxt.RateLimitExceeded:

        logging.warning(
            "KUCOIN RATE LIMIT HIT - COOLING DOWN"
        )

        time.sleep(90)

    except Exception as e:

        logging.error(f"{symbol} Error: {e}")

    return None

# =========================================
# MAIN LOOP
# =========================================

def analyze_market():

    while True:

        try:

            coins = get_top_coins()

            logging.info(
                f"Scanning {len(coins)} coins..."
            )

            for symbol in coins:

                try:

                    signal = explosive_scan(symbol)

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
# START THREAD
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

bot.infinity_polling(
    timeout=60,
    long_polling_timeout=60
)
