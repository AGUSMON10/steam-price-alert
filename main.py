import random
import requests
import time
import re
import os
import threading
from flask import Flask, jsonify
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import builtins

# ------------------- CONFIG -------------------
PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@31.59.20.176:6754",
    "http://olrliwpe:v769pjjmxnb1@23.95.150.145:6114",
    "http://olrliwpe:v769pjjmxnb1@64.137.96.74:6641",
    "http://olrliwpe:v769pjjmxnb1@142.111.67.146:5611",
    "http://olrliwpe:v769pjjmxnb1@23.229.19.94:8689",
    "http://olrliwpe:v769pjjmxnb1@198.105.121.200:6462",
    "http://olrliwpe:v769pjjmxnb1@216.10.27.159:6837",
    "http://olrliwpe:v769pjjmxnb1@45.38.107.97:6014",
    "http://olrliwpe:v769pjjmxnb1@198.23.239.134:6540",
    "http://olrliwpe:v769pjjmxnb1@107.172.163.27:6543"
]

BAD_PROXIES = set()
sessions_por_proxy = {}
lock = Lock()
session_global = requests.Session()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("[ERROR] Faltan variables de entorno: TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID")
    exit(1)

skins_a_vigilar = {
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife#": 155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Lore%20%28Well-Worn%29": 150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Autotronic%20%28Well-Worn%29": 155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Bright%20Water%20%28Factory%20New%29": 126.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Huntsman%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29": 160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Survival%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29": 100.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29": 155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Freehand%20%28Minimal%20Wear%29": 140.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Freehand%20%28Factory%20New%29": 160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29": 150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29": 170.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29": 155.00
}

notificados = {}
item_ids_cache = {}
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

# ------------------- UTIL -------------------
def flush_print(*args, **kwargs):
    kwargs['flush'] = True
    return print(*args, **kwargs)
builtins.print = flush_print

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}

def get_proxy():
    disponibles = [p for p in PROXIES if p not in BAD_PROXIES]
    if not disponibles:
        disponibles = PROXIES
    proxy = random.choice(disponibles)
    return {"http": proxy, "https": proxy}

def get_session(proxy):
    clave = proxy["http"]
    if clave not in sessions_por_proxy:
        s = requests.Session()
        s.proxies.update(proxy)
        sessions_por_proxy[clave] = s
    return sessions_por_proxy[clave]

def limpiar_url(url):
    return url.split("?")[0]

# ------------------- FUNCIONES STEAM -------------------
def obtener_item_nameid(url_item):
    url_item = limpiar_url(url_item)
    for intento in range(4):
        proxy = get_proxy()
        try:
            session = get_session(proxy)
            r = session.get(url_item, headers=get_headers(), timeout=6)

            if r.status_code == 429:
                print("429 detectado — cambiando proxy...")
                time.sleep(10)
                continue

            if r.status_code == 200:
                match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
                if match:
                    return match.group(1)
                fallback = re.search(r'ItemActivityTicker.Start\( \{"sessionid":.+?"item_nameid":"(\d+)"', r.text)
                if fallback:
                    return fallback.group(1)
            else:
                print(f"[ERROR] HTTP {r.status_code}")
        except Exception:
            print("Proxy malo:", proxy)
            BAD_PROXIES.add(proxy["http"])
            time.sleep(5)
    return None

def obtener_lowest_sell_price(item_nameid):
    url = f"https://steamcommunity.com/market/itemordershistogram?language=english&currency=1&item_nameid={item_nameid}"
    for intento in range(4):
        proxy = get_proxy()
        try:
            session = get_session(proxy)
            r = session.get(url, headers=get_headers(), timeout=6)

            if r.status_code == 429:
                print("429 Steam — cambiando proxy...")
                time.sleep(10)
                continue

            if r.status_code == 200:
                data = r.json()
                if "lowest_sell_order" in data:
                    return int(data["lowest_sell_order"]) / 100
            else:
                print(f"[ERROR] HTTP {r.status_code}")
        except Exception:
            print("Proxy malo:", proxy)
            BAD_PROXIES.add(proxy["http"])
            time.sleep(5)
    return None

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        response = session_global.post(url, data=data, timeout=15)
        if response.status_code == 200:
            print("[INFO] Mensaje enviado a Telegram")
        else:
            print(f"[ERROR] Telegram: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")
        estado_app["errores"] += 1

def revisar_item(item):
    try:
        url, precio_max = item
        print(f"[INFO] Revisando: {url}")

        if url not in item_ids_cache:
            item_ids_cache[url] = obtener_item_nameid(url)
        item_nameid = item_ids_cache.get(url)
        if not item_nameid:
            return

        precio_actual = obtener_lowest_sell_price(item_nameid)
        if precio_actual is None:
            return

        ultima_alerta = notificados.get(url)
        if precio_actual <= precio_max and (ultima_alerta is None or precio_actual < ultima_alerta):
            mensaje = f"🔥 Oferta detectada\n{url}\n💵 {precio_actual:.2f} USD"
            enviar_telegram(mensaje)
            with lock:
                notificados[url] = precio_actual
    except Exception as e:
        print(f"[ERROR] {e}")

def escanear():
    estado_app["ultimo_escaneo"] = datetime.now().isoformat()
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(revisar_item, skins_a_vigilar.items())

# ------------------- FLASK -------------------
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "mensaje": "Steam Alert Bot activo",
        "ultimo_escaneo": estado_app["ultimo_escaneo"],
        "errores": estado_app["errores"],
        "timestamp": datetime.now().isoformat()
    })

@app.route("/status")
def status():
    return jsonify({
        "activo": estado_app["activo"],
        "ultimo_escaneo": estado_app["ultimo_escaneo"],
        "errores_totales": estado_app["errores"],
        "items_vigilados": len(skins_a_vigilar),
        "notificaciones_enviadas": len(notificados)
    })

# ------------------- LOOP PRINCIPAL -------------------
def monitor_loop():
    print("[INFO] Iniciando monitoreo...")
    while estado_app["activo"]:
        try:
            escanear()
            time.sleep(random.randint(600, 900))
        except KeyboardInterrupt:
            print("[INFO] Deteniendo...")
            estado_app["activo"] = False
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            estado_app["errores"] += 1
            time.sleep(150)

def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    monitor_thread = threading.Thread(target=monitor_loop)
    monitor_thread.start()
    servidor_thread = threading.Thread(target=iniciar_servidor)
    servidor_thread.start()
    monitor_thread.join()
    servidor_thread.join()
