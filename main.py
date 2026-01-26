import requests
import time
import re
import os
import threading
import json
import logging
from flask import Flask, jsonify
from datetime import datetime

# ================== CONFIG LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ================== ENV ==================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    log.error("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
    exit(1)

# ================== CONFIG ==================
STATE_FILE = "estado.json"
REQUEST_TIMEOUT = 15
SCAN_INTERVAL = 120
ITEM_DELAY = 7
RATE_LIMIT_SLEEP = 240

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

skins_a_vigilar = {
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Classic%20Knife%20%7C%20Urban%20Masked%20%28Field-Tested%29":
    111.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Damascus%20Steel%20%28Factory%20New%29":
    133.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    132.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Bright%20Water%20%28Minimal%20Wear%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    137.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Flip%20Knife%20%7C%20Ultraviolet%20%28Well-Worn%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    134.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    110.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    141.00
}

# ================== STATE ==================
notificados = {}
item_ids = {}
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

# ================== STATE PERSISTENCE ==================
def cargar_estado():
    global notificados
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            notificados.update(json.load(f))
        log.info("Estado cargado desde disco")

def guardar_estado():
    with open(STATE_FILE, "w") as f:
        json.dump(notificados, f)
    log.info("Estado guardado")

# ================== UTILS ==================
def limpiar_url(url):
    return url.split("?")[0]

# ================== STEAM ==================
def obtener_item_nameid(url):
    try:
        r = requests.get(
            limpiar_url(url),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        if r.status_code == 429:
            log.warning("Rate limit Steam (item_nameid). Durmiendo...")
            time.sleep(RATE_LIMIT_SLEEP)
            return None

        if r.status_code != 200:
            log.error(f"HTTP {r.status_code} al cargar {url}")
            return None

        match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
        if match:
            return match.group(1)

        fallback = re.search(r'"item_nameid":"(\d+)"', r.text)
        if fallback:
            return fallback.group(1)

        log.warning(f"No se pudo extraer item_nameid para {url}")
    except Exception as e:
        log.exception(f"Error obteniendo item_nameid: {e}")
        estado_app["errores"] += 1

    return None


def obtener_o_cachear_item_nameid(url):
    if url not in item_ids:
        item_ids[url] = obtener_item_nameid(url)
    return item_ids[url]


def obtener_lowest_sell_price(item_nameid):
    try:
        url = (
            "https://steamcommunity.com/market/itemordershistogram"
            f"?language=english&currency=1&item_nameid={item_nameid}"
        )

        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if r.status_code == 429:
            log.warning("Rate limit Steam (histogram). Durmiendo...")
            time.sleep(RATE_LIMIT_SLEEP)
            return None

        if r.status_code != 200:
            log.error(f"HTTP {r.status_code} al consultar histogram")
            return None

        data = r.json()
        if "lowest_sell_order" in data:
            return int(data["lowest_sell_order"]) / 100
    except Exception as e:
        log.exception(f"Error consultando precio: {e}")
        estado_app["errores"] += 1

    return None

# ================== TELEGRAM ==================
def enviar_telegram(mensaje):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje},
            timeout=REQUEST_TIMEOUT,
        )

        if r.status_code == 200:
            log.info("Mensaje enviado a Telegram")
        else:
            log.error(f"Telegram error HTTP {r.status_code}")
    except Exception as e:
        log.exception(f"Error enviando Telegram: {e}")
        estado_app["errores"] += 1

# ================== SCAN ==================
def escanear():
    estado_app["ultimo_escaneo"] = datetime.now().isoformat()

    for url, precio_max in skins_a_vigilar.items():
        log.info(f"Revisando item")

        item_nameid = obtener_o_cachear_item_nameid(url)
        if not item_nameid:
            continue

        precio_actual = obtener_lowest_sell_price(item_nameid)
        if precio_actual is None:
            continue

        log.info(f"Precio actual: {precio_actual:.2f} USD")

        ultima_alerta = notificados.get(url)
        if precio_actual <= precio_max and (
            ultima_alerta is None or precio_actual < ultima_alerta
        ):
            mensaje = (
                "🛒 ¡Skin por debajo del precio objetivo!\n"
                f"{url}\n"
                f"💵 Precio: {precio_actual:.2f} USD\n"
                f"🎯 Máximo: {precio_max:.2f} USD\n"
                f"🕒 {datetime.now():%Y-%m-%d %H:%M:%S}"
            )
            enviar_telegram(mensaje)
            notificados[url] = precio_actual
            guardar_estado()

        time.sleep(ITEM_DELAY)

# ================== LOOP ==================
def monitor_loop():
    log.info("Iniciando monitoreo Steam")
    cargar_estado()

    while estado_app["activo"]:
        try:
            escanear()
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            log.exception(f"Error en loop principal: {e}")
            estado_app["errores"] += 1
            time.sleep(60)

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(
        status="ok",
        ultimo_escaneo=estado_app["ultimo_escaneo"],
        errores=estado_app["errores"],
        timestamp=datetime.now().isoformat(),
    )

@app.route("/status")
def status():
    return jsonify(
        activo=estado_app["activo"],
        items=len(skins_a_vigilar),
        notificaciones=len(notificados),
        errores=estado_app["errores"],
    )

def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080)

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    threading.Thread(target=iniciar_servidor, daemon=True).start()

    while True:
        time.sleep(3600)
