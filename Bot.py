import ccxt
import time
import requests

# --- CONFIG ---
TELEGRAM_TOKEN = '8774665494:AAFIIzynyWMpS1XeftAWfJ_-w_DZNqxV3HM'
CHAT_ID = '8812437138'
exchange = ccxt.binance()

# Coins List
coins = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'LINK/USDT', 'DOT/USDT', 
    'AVAX/USDT', 'UNI/USDT', 'SHIB/USDT', 'PEPE/USDT', 'LTC/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT', 'FET/USDT', 
    'RNDR/USDT', 'INJ/USDT', 'FIL/USDT', 'ICP/USDT', 'ATOM/USDT', 'XLM/USDT', 'HBAR/USDT', 'ETC/USDT', 'LDO/USDT', 
    'ALGO/USDT', 'VET/USDT', 'MANA/USDT', 'SAND/USDT', 'AXS/USDT', 'AAVE/USDT', 'CRV/USDT', 'MKR/USDT', 'SNX/USDT', 
    'DYDX/USDT', 'GALA/USDT', 'IMX/USDT', 'OP/USDT', 'EGLD/USDT', 'FLOW/USDT', 'EOS/USDT', 'XTZ/USDT', 'CHZ/USDT', 
    'KAVA/USDT', 'BAT/USDT', 'ENJ/USDT', 'TRX/USDT', 'CFX/USDT', 'ANKR/USDT', 'GRT/USDT', 'COMP/USDT', 'SUSHI/USDT', 
    'WLD/USDT', 'PYTH/USDT', 'TIA/USDT', 'SEI/USDT', 'SUI/USDT', 'BLUR/USDT', 'JUP/USDT', 'BONK/USDT', 'ORDI/USDT', 
    'STX/USDT', 'BCH/USDT', 'XMR/USDT', 'NEO/USDT', 'DASH/USDT', 'ZEC/USDT', 'CAKE/USDT', 'FTM/USDT', 'TAO/USDT', 
    'JASMY/USDT', 'ONDO/USDT', 'ALT/USDT', 'PENDLE/USDT', 'RAY/USDT'
]

active_trades = {}

def send_msg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
    except: pass

def get_indicators(coin):
    ohlcv = exchange.fetch_ohlcv(coin, timeframe='1h', limit=200)
    closes = [x[4] for x in ohlcv]
    curr = closes[-1]
    ema200 = sum(closes[-200:]) / 200
    vol_spike = ohlcv[-1][5] / (sum([x[5] for x in ohlcv[-6:-1]])/5)
    mean = sum(closes[-50:]) / 50
    std_dev = (sum([(x - mean) ** 2 for x in closes[-50:]]) / 50) ** 0.5
    is_breakout = curr > (mean + (2 * std_dev))
    return curr, ema200, vol_spike, is_breakout

print("God Mode 24/7 Activated...")
send_msg("Bot Started - 24/7 Continuous Mode Active.")

while True:
    try:
        # 24/7 Loop: Removed time and BTC trend restrictions
        for coin in coins:
            try:
                curr, ema, vol, breakout = get_indicators(coin)
                if curr > ema and breakout and vol > 3.0:
                    if coin not in active_trades:
                        active_trades[coin] = curr
                        send_msg(f"🚀 GOD MODE ENTRY: {coin}\nPrice: ${curr:.4f}\nTarget: 5% Profit")
                time.sleep(2) # Increased sleep to keep API load low for 24/7
            except: continue
        
        for coin in list(active_trades.keys()):
            curr = exchange.fetch_ticker(coin)['last']
            profit = (curr - active_trades[coin]) / active_trades[coin] * 100
            if profit >= 5.0 or profit <= -2.0:
                send_msg(f"✅ EXIT {coin}: {profit:.2f}% Profit/Loss")
                del active_trades[coin]
            
    except Exception as e:
        time.sleep(60)
  
