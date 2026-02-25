import random
import requests
import time
import re
import os
import threading
from flask import Flask, jsonify
from datetime import datetime

# ==============================
# 🔐 TUS 4 STATIC RESIDENTIAL
# ==============================

STATIC_PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@136.0.167.151:7154",
    "http://olrliwpe:v769pjjmxnb1@103.130.178.157:5821",
    "http://olrliwpe:v769pjjmxnb1@192.46.203.98:6064",
    "http://olrliwpe:v769pjjmxnb1@192.53.140.59:5155"
]

# ==============================
# 🔔 TELEGRAM
# ==============================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Faltan variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
    exit(1)

# ==============================
# 🎮 SKINS A VIGILAR (12)
# ==============================

skins_a_vigilar = {
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    175.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Bright%20Water%20%28Factory%20New%29":
    125.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Tiger%20Tooth%20%28Minimal%20Wear%29":
    180.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Autotronic%20%28Well-Worn%29":
    123.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    131.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Huntsman%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    158.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Nomad%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    166.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Damascus%20Steel%20%28Field-Tested%29":
    132.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    175.00
}

# ==============================
# 🧠 VARIABLES INTERNAS
# ==============================

notificados = {}
item_ids_cache = {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
]

# ==============================
# 🔧 CREAR SESSION POR IP
# ==============================

def crear_session(proxy_url):
    s = requests.Session()
    s.proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    })
    return s

# ==============================
# 🔍 OBTENER item_nameid
# ==============================

def obtener_item_nameid(url_item, session):

    for _ in range(3):
        try:
            r = session.get(url_item, timeout=7)

            if r.status_code == 200:
                match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
                if match:
                    return match.group(1)

        except:
            time.sleep(2)

    return None

# ==============================
# 💰 OBTENER PRECIO ACTUAL
# ==============================

def obtener_lowest_sell_price(item_nameid, session):

    url = f"https://steamcommunity.com/market/itemordershistogram?language=english&currency=1&item_nameid={item_nameid}"

    for _ in range(3):
        try:
            r = session.get(url, timeout=7)

            if r.status_code == 200:
                data = r.json()
                if "lowest_sell_order" in data:
                    return int(data["lowest_sell_order"]) / 100

        except:
            time.sleep(2)

    return None

# ==============================
# 📲 TELEGRAM
# ==============================

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        requests.post(url, data=data, timeout=10)
    except:
        pass

# ==============================
# 📦 DIVIDIR 12 SKINS EN 4 GRUPOS
# ==============================

skins_items = list(skins_a_vigilar.items())

grupos = [
    skins_items[0:3],
    skins_items[3:6],
    skins_items[6:9],
    skins_items[9:12],
]

# ==============================
# 🧵 WORKER POR IP
# ==============================

def worker(grupo_skins, proxy_url):

    session = crear_session(proxy_url)

    while True:
        for url, precio_max in grupo_skins:

            if url not in item_ids_cache:
                item_ids_cache[url] = obtener_item_nameid(url, session)

            item_nameid = item_ids_cache.get(url)
            if not item_nameid:
                continue

            precio_actual = obtener_lowest_sell_price(item_nameid, session)
            if not precio_actual:
                continue

            ultima_alerta = notificados.get(url)

            if precio_actual <= precio_max and (
                ultima_alerta is None or precio_actual < ultima_alerta
            ):
                mensaje = (
                    f"🛒 Skin por debajo del objetivo!\n"
                    f"{url}\n"
                    f"💵 {precio_actual:.2f} USD"
                )
                enviar_telegram(mensaje)
                notificados[url] = precio_actual

            time.sleep(random.uniform(4, 6))  # 3 skins → ~15s ciclo

# ==============================
# 🌐 SERVIDOR (OPCIONAL)
# ==============================

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "ok"})

def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080)

# ==============================
# 🚀 MAIN
# ==============================

if __name__ == "__main__":

    for i in range(4):
        threading.Thread(
            target=worker,
            args=(grupos[i], STATIC_PROXIES[i]),
            daemon=True
        ).start()

    threading.Thread(target=iniciar_servidor).start()

    while True:
        time.sleep(60)
