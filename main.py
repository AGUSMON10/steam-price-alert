import random
import requests
import time
import os
import threading
from flask import Flask, jsonify
from datetime import datetime

# =========================
# CONFIG
# =========================

PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@136.0.167.151:7154",
    "http://olrliwpe:v769pjjmxnb1@46.202.3.10:7276",
    "http://olrliwpe:v769pjjmxnb1@103.130.178.157:5821"
]

PROXY_STATUS = {p: 0 for p in PROXIES}
PROXY_COOLDOWN = 900

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Faltan variables de entorno")
    exit(1)

# =========================
# SKINS (QUERY-BASED)
# =========================

skins_a_vigilar = {
    "StatTrak Falchion Knife Autotronic Minimal Wear": 182.00,
    "StatTrak Huntsman Knife Damascus Steel Factory New": 215.00,
    "StatTrak Falchion Knife Stained Minimal Wear": 210.00,
}

# =========================
# STATE (SNIPER ENGINE)
# =========================

price_cache = {}     # {query: {price, last_update}}
cooldowns = {}       # anti spam alerts
estado = {
    "errores": 0,
    "ultima_iteracion": None
}

# =========================
# HEADERS
# =========================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }

# =========================
# PROXIES
# =========================

def obtener_proxy():
    now = time.time()
    validos = [p for p, t in PROXY_STATUS.items() if t <= now]
    return random.choice(validos) if validos else random.choice(PROXIES)

def marcar_proxy_malo(proxy):
    PROXY_STATUS[proxy] = time.time() + PROXY_COOLDOWN

# =========================
# STEAM SEARCH ENGINE
# =========================

def steam_search(query, session):
    url = "https://steamcommunity.com/market/search/render/"

    params = {
        "query": query,
        "start": 0,
        "count": 5,   # sniper mode = mínimo ruido
        "currency": 1,
        "language": "english"
    }

    for _ in range(3):
        proxy = obtener_proxy()
        proxies = {"http": proxy, "https": proxy}

        try:
            r = session.get(url, params=params, headers=get_headers(), proxies=proxies, timeout=10)

            if r.status_code == 429:
                marcar_proxy_malo(proxy)
                time.sleep(3)
                continue

            if r.status_code != 200:
                return None

            data = r.json().get("results", [])

            prices = [
                item["sell_price"] / 100
                for item in data
                if item.get("sell_price")
            ]

            return min(prices) if prices else None

        except:
            marcar_proxy_malo(proxy)
            time.sleep(2)

    return None

# =========================
# QUERY BUILDER
# =========================

def build_query(name):
    return name.replace("_", " ")

# =========================
# SNIPER LOGIC
# =========================

def should_update(query):
    last = price_cache.get(query, {}).get("last_update", 0)
    return time.time() - last > 45  # cada 45s max por item

def is_opportunity(query, price, max_price):
    old = price_cache.get(query, {}).get("price")

    if old is None:
        return False

    drop = old - price

    return (
        price <= max_price and
        (price < old * 0.95 or drop > 3)
    )

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        }, timeout=10)
    except:
        pass

def alert(query, price, max_price):
    now = time.time()

    if now - cooldowns.get(query, 0) < 30:
        return

    cooldowns[query] = now

    msg = (
        f"🎯 SNIPER DEAL\n\n"
        f"{query}\n"
        f"💵 Precio: {price:.2f} USD\n"
        f"📉 Máx: {max_price:.2f} USD"
    )

    send_telegram(msg)

# =========================
# WORKER SNIPER
# =========================

def worker(items):
    session = requests.Session()

    while True:
        for name, max_price in items.items():

            query = build_query(name)

            if not should_update(query):
                continue

            price = steam_search(query, session)

            if price is None:
                continue

            old = price_cache.get(query, {}).get("price")

            price_cache[query] = {
                "price": price,
                "last_update": time.time()
            }

            if is_opportunity(query, price, max_price):
                alert(query, price, max_price)

            time.sleep(random.uniform(2, 4))

        estado["ultima_iteracion"] = datetime.now().isoformat()
        time.sleep(10)

# =========================
# FLASK STATUS
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "items": len(skins_a_vigilar),
        "time": datetime.now().isoformat()
    })

@app.route("/status")
def status():
    return jsonify({
        "items": len(skins_a_vigilar),
        "cache": len(price_cache),
        "cooldowns": len(cooldowns),
        "ultima_iteracion": estado["ultima_iteracion"]
    })

# =========================
# START
# =========================

def start():
    t = threading.Thread(target=worker, args=(skins_a_vigilar,))
    t.start()

    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    start()
