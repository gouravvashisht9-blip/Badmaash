import os
import time
import json
import logging
import ccxt
import telebot
import pandas as pd
import ta
from threading import Thread
from datetime import datetime, timezone

# =========================================
# CONFIG
# =========================================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

try:
    bot.remove_webhook()
    time.sleep(2)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
log = logging.getLogger("sniper")

# =========================================
# STRATEGY PARAMETERS
# =========================================
TIMEFRAME       = '15m'
HTF_TIMEFRAME   = '1h'        # higher timeframe trend filter
CANDLES         = 250

RSI_PERIOD      = 14
RSI_LOWER       = 35          # oversold zone
RSI_UPPER       = 45          # must be turning up into this zone

ADX_PERIOD      = 14
ADX_MIN         = 22

EMA_FAST        = 50
EMA_SLOW        = 200

VOL_LOOKBACK    = 20
VOL_MULT        = 2.0         # current vol must be 2x avg

ATR_PERIOD      = 14
SL_ATR_MULT     = 1.5
TP1_ATR_MULT    = 2.0
TP2_ATR_MULT    = 3.5

SCAN_PAUSE      = 0.4         # seconds between coins (rate-limit friendly)
LOOP_REST       = 30          # seconds between full scans
COOLDOWN_SEC    = 4 * 3600    # 4h per symbol
HEARTBEAT_SEC   = 6 * 3600    # status ping every 6h

ALERT_FILE      = "last_alerts.json"

# =========================================
# EXCHANGE
# =========================================
exchange = ccxt.kucoin({'enableRateLimit': True})

# =========================================
# COINS
# =========================================
coins = [
    "BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","DOGE/USDT",
    "ADA/USDT","AVAX/USDT","LINK/USDT","DOT/USDT","TRX/USDT","TON/USDT",
    "SHIB/USDT","PEPE/USDT","WIF/USDT","NEAR/USDT","APT/USDT","ARB/USDT",
    "OP/USDT","ATOM/USDT","INJ/USDT","SEI/USDT","SUI/USDT","FET/USDT",
    "TAO/USDT","FIL/USDT","ETC/USDT","ICP/USDT","HBAR/USDT","AAVE/USDT",
    "GALA/USDT","JUP/USDT","RUNE/USDT","TIA/USDT","PYTH/USDT","ORDI/USDT",
    "ENA/USDT","AR/USDT","KAS/USDT","EGLD/USDT","ALGO/USDT","SAND/USDT",
    "MANA/USDT","CRV/USDT","UNI/USDT","LDO/USDT","XLM/USDT","VET/USDT",
    "THETA/USDT","EOS/USDT","AXS/USDT","CHZ/USDT","DYDX/USDT","BLUR/USDT"
]

# =========================================
# PERSISTENT COOLDOWN STORAGE
# =========================================
def load_alerts():
    try:
        with open(ALERT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_alerts(data):
    try:
        with open(ALERT_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        log.error(f"Save alerts failed: {e}")

last_alerts = load_alerts()

# =========================================
# DATA + INDICATORS
# =========================================
def fetch_df(symbol, tf, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
    if not ohlcv or len(ohlcv) < 50:
        return None
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
    return df

def add_indicators(df):
    df["rsi"]   = ta.momentum.RSIIndicator(df["close"], RSI_PERIOD).rsi()
    df["ema_f"] = ta.trend.EMAIndicator(df["close"], EMA_FAST).ema_indicator()
    df["ema_s"] = ta.trend.EMAIndicator(df["close"], EMA_SLOW).ema_indicator()
    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], ADX_PERIOD)
    df["adx"]    = adx.adx()
    df["di_pos"] = adx.adx_pos()
    df["di_neg"] = adx.adx_neg()
    df["atr"]    = ta.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], ATR_PERIOD
    ).average_true_range()
    df["vol_avg"] = df["volume"].rolling(VOL_LOOKBACK).mean()
    return df

# =========================================
# SIGNAL LOGIC
# =========================================
def analyze(symbol):
    # Higher timeframe trend
    htf = fetch_df(symbol, HTF_TIMEFRAME, 250)
    if htf is None:
        return None
    htf = add_indicators(htf)
    htf_bullish = htf["ema_f"].iloc[-1] > htf["ema_s"].iloc[-1] \
                  and htf["close"].iloc[-1] > htf["ema_f"].iloc[-1]
    if not htf_bullish:
        return None

    # Entry timeframe
    df = fetch_df(symbol, TIMEFRAME, CANDLES)
    if df is None:
        return None
    df = add_indicators(df)

    last  = df.iloc[-1]
    prev  = df.iloc[-2]

    price       = last["close"]
    rsi_now     = last["rsi"]
    rsi_prev    = prev["rsi"]
    adx_now     = last["adx"]
    di_pos      = last["di_pos"]
    di_neg      = last["di_neg"]
    ema_f       = last["ema_f"]
    ema_s       = last["ema_s"]
    atr         = last["atr"]
    vol_ratio   = last["volume"] / last["vol_avg"] if last["vol_avg"] else 0

    # Conditions
    trend_ok    = ema_f > ema_s and price > ema_s
    rsi_ok      = (rsi_prev < RSI_LOWER) and (RSI_LOWER <= rsi_now <= RSI_UPPER)
    adx_ok      = adx_now > ADX_MIN and di_pos > di_neg
    vol_ok      = vol_ratio > VOL_MULT
    candle_ok   = last["close"] > last["open"]   # bullish close

    if not (trend_ok and rsi_ok and adx_ok and vol_ok and candle_ok):
        return None

    # Cooldown
    now = time.time()
    last_t = last_alerts.get(symbol, 0)
    if now - last_t < COOLDOWN_SEC:
        return None
    last_alerts[symbol] = now
    save_alerts(last_alerts)

    # Risk levels
    sl  = price - SL_ATR_MULT  * atr
    tp1 = price + TP1_ATR_MULT * atr
    tp2 = price + TP2_ATR_MULT * atr
    rr  = (tp1 - price) / (price - sl) if price > sl else 0

    msg = (
        "🎯 *SNIPER LONG SIGNAL*\n\n"
        f"🪙 *{symbol}*  ({TIMEFRAME})\n"
        f"💰 Entry: `{price:.6f}`\n\n"
        f"🛑 SL:   `{sl:.6f}`  ({SL_ATR_MULT}x ATR)\n"
        f"🎯 TP1: `{tp1:.6f}`  ({TP1_ATR_MULT}x ATR)\n"
        f"🎯 TP2: `{tp2:.6f}`  ({TP2_ATR_MULT}x ATR)\n"
        f"⚖️ R:R (TP1): `{rr:.2f}`\n\n"
        f"📊 RSI: {rsi_prev:.1f} → {rsi_now:.1f} (turning up)\n"
        f"🔥 ADX: {adx_now:.1f}  | DI+ {di_pos:.1f} > DI- {di_neg:.1f}\n"
        f"📈 Vol: {vol_ratio:.2f}x avg\n"
        f"🧭 HTF (1h): bullish ✅\n\n"
        "⚠️ Risk max 1–2% per trade."
    )
    return msg

# =========================================
# TELEGRAM COMMANDS
# =========================================
@bot.message_handler(commands=['start','status'])
def cmd_status(m):
    bot.reply_to(m,
        "🤖 *Sniper Bot Online*\n\n"
        f"✅ Scanning {len(coins)} pairs\n"
        f"🕒 TF: {TIMEFRAME} | HTF filter: {HTF_TIMEFRAME}\n"
        f"📐 RSI bounce + ADX{ADX_MIN}+ + Vol {VOL_MULT}x + ATR risk\n"
        f"⏳ Cooldown: {COOLDOWN_SEC//3600}h per coin",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['ping'])
def cmd_ping(m):
    bot.reply_to(m, "pong ✅")

# =========================================
# SCANNER LOOP + HEARTBEAT
# =========================================
def scanner():
    last_beat = 0
    while True:
        start = time.time()
        log.info(f"Scan start: {len(coins)} symbols")
        for sym in coins:
            try:
                signal = analyze(sym)
                if signal:
                    try:
                        bot.send_message(CHAT_ID, signal, parse_mode="Markdown")
                        log.info(f"SIGNAL → {sym}")
                    except Exception as e:
                        log.error(f"Send fail {sym}: {e}")
            except ccxt.RateLimitExceeded:
                log.warning("Rate limit hit — backing off 60s")
                time.sleep(60)
            except Exception as e:
                log.error(f"{sym} analyze error: {e}")
            time.sleep(SCAN_PAUSE)

        elapsed = time.time() - start
        log.info(f"Scan done in {elapsed:.1f}s")

        # Heartbeat
        if time.time() - last_beat > HEARTBEAT_SEC:
            try:
                bot.send_message(
                    CHAT_ID,
                    f"💓 Heartbeat — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
                    f"Last scan: {elapsed:.0f}s | Pairs: {len(coins)}"
                )
                last_beat = time.time()
            except Exception:
                pass

        time.sleep(LOOP_REST)

Thread(target=scanner, daemon=True).start()

# =========================================
# POLLING
# =========================================
log.info("Bot polling started")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
    except Exception as e:
        log.error(f"Polling error: {e}")
        time.sleep(15)
        
