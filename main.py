import random
import requests
import time
import re
import os
import threading
from flask import Flask, jsonify
from datetime import datetime
import builtins
from urllib.parse import unquote

# Lista de proxies (pegá los tuyos de Webshare)

PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@136.0.167.151:7154",
    "http://olrliwpe:v769pjjmxnb1@103.130.178.157:5821",
    "http://olrliwpe:v769pjjmxnb1@192.46.203.98:6064",
    "http://olrliwpe:v769pjjmxnb1@192.53.140.59:5155"
]

# Manejo avanzado de proxies
PROXY_COOLDOWN = 900  # 15 minutos
PROXY_STATUS = {p: 0 for p in PROXIES}  # proxy: timestamp_habilitado


# Redefinir print global con flush automático
original_print = print

def flush_print(*args, **kwargs):
    kwargs['flush'] = True
    timestamp = datetime.now().strftime("%H:%M:%S")
    original_print(f"[{timestamp}]", *args, **kwargs)

builtins.print = flush_print

# Configuración desde variables de entorno
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Verificar que las variables de entorno estén configuradas
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print(
        "[ERROR] Faltan variables de entorno: TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID"
    )
    print("Configúralas en la herramienta de Secrets de Replit")
    exit(1)

# Lista de ítems con URL y precio máximo aceptado
skins_a_vigilar = {
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    182.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    130.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Stained%20%28Minimal%20Wear%29":
    145.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Bowie%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    140.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    167.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Talon%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    565.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Nomad%20Knife%20%7C%20Scorched%20%28Minimal%20Wear%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Bloodsport%20%28Minimal%20Wear%29":
    205.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Talon%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    556.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Classic%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    174.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Case%20Hardened%20%28Well-Worn%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    200.00,
    "https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Bloodsport%20%28Field-Tested%29":
    185.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Bright%20Water%20%28Factory%20New%29":
    145.00
}

notificados = {}
item_ids_cache = {}
ultimo_escaneo = None
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

# Headers realistas
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }

def obtener_proxy():
    ahora = time.time()
    disponibles = [p for p, t in PROXY_STATUS.items() if t <= ahora]

    if not disponibles:
        print("[WARN] Todos los proxies en cooldown, usando cualquiera...")
        return random.choice(PROXIES)

    return random.choice(disponibles)

def marcar_proxy_malo(proxy_url):
    PROXY_STATUS[proxy_url] = time.time() + PROXY_COOLDOWN
    print(f"[INFO] Proxy en cooldown 15 min: {proxy_url}")

# Crear app Flask para UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    """Endpoint para UptimeRobot"""
    return jsonify({
        "status": "ok",
        "mensaje": "Steam Alert Bot está activo",
        "ultimo_escaneo": estado_app["ultimo_escaneo"],
        "errores": estado_app["errores"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Endpoint detallado de estado"""
    return jsonify({
        "activo": estado_app["activo"],
        "ultimo_escaneo": estado_app["ultimo_escaneo"],
        "errores_totales": estado_app["errores"],
        "items_vigilados": len(skins_a_vigilar),
        "notificaciones_enviadas": len(notificados)
    })


def limpiar_url(url):
    return url.split("?")[0]

def obtener_nombre_skin(url):
    parte = url.split("/730/")[-1]
    nombre = unquote(parte)
    return nombre

def obtener_item_nameid(url_item, session):
    url_item = limpiar_url(url_item)

    for intento in range(4):

        proxy_url = obtener_proxy()
        proxy_dict = {"http": proxy_url, "https": proxy_url}
        print(f"[PROXY] Usando: {proxy_url}")

        try:

            r = session.get(
                url_item,
                headers=get_headers(),
                proxies=proxy_dict,
                timeout=7
            )

            if r.status_code == 429:
                print(f"429 detectado — proxy en cooldown: {proxy_url}")
                marcar_proxy_malo(proxy_url)
                time.sleep(10)
                continue

            if r.status_code == 200:
                match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
                if match:
                    return match.group(1)

                print("[WARN] Probando fallback item_nameid...")
                fallback = re.search(
                    r'ItemActivityTicker.Start\( \{"sessionid":.+?"item_nameid":"(\d+)"',
                    r.text
                )
                if fallback:
                    return fallback.group(1)

            else:
                print(f"[ERROR] HTTP {r.status_code}")

        except Exception:
            print("Proxy malo:", proxy_url)
            marcar_proxy_malo(proxy_url)
            time.sleep(5)

    return None


def obtener_lowest_sell_price(item_nameid, session):
    url = f"https://steamcommunity.com/market/itemordershistogram?language=english&currency=1&item_nameid={item_nameid}"

    for intento in range(4):

        proxy_url = obtener_proxy()
        proxy_dict = {"http": proxy_url, "https": proxy_url}
        print(f"[PROXY] Usando: {proxy_url}")

        try:

            r = session.get(
                url,
                headers=get_headers(),
                proxies=proxy_dict,
                timeout=7
            )

            if r.status_code == 429:
                print(f"429 Steam — proxy en cooldown: {proxy_url}")
                marcar_proxy_malo(proxy_url)
                time.sleep(10)
                continue

            if r.status_code == 200:
                data = r.json()
                lowest = data.get("lowest_sell_order")

                if lowest and str(lowest).isdigit():
                    return int(lowest) / 100

            else:
                print(f"[ERROR] HTTP {r.status_code}")

        except Exception:
            print("Proxy malo:", proxy_url)
            marcar_proxy_malo(proxy_url)
            time.sleep(5)

    return None

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        response = requests.post(url, data=data, timeout=15)
        if response.status_code == 200:
            print("[INFO] Mensaje enviado a Telegram exitosamente")
        else:
            print(
                f"[ERROR] Error al enviar mensaje a Telegram: {response.status_code}"
            )
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el mensaje a Telegram: {e}")
        estado_app["errores"] += 1

def dividir_skins_en_grupos():
    lista = list(skins_a_vigilar.items())
    cantidad_proxies = len(PROXIES)

    grupos = [[] for _ in range(cantidad_proxies)]

    for i, item in enumerate(lista):
        grupos[i % cantidad_proxies].append(item)

    return grupos

def worker(grupo_skins):
    session = requests.Session()

    while estado_app["activo"]:
        for url, precio_max in grupo_skins:

            nombre_skin = obtener_nombre_skin(url)
            print(f"[INFO] Revisando: {nombre_skin}")

            if url not in item_ids_cache:
                item_ids_cache[url] = obtener_item_nameid(url, session)

            item_nameid = item_ids_cache.get(url)

            if not item_nameid:
                continue

            precio_actual = obtener_lowest_sell_price(item_nameid, session)

            if precio_actual is None:
                continue

            print(f"[PRICE] {precio_actual:.2f} USD | Max: {precio_max:.2f}")

            ultima_alerta = notificados.get(url)

            if precio_actual <= precio_max and (
                ultima_alerta is None or precio_actual < ultima_alerta
            ):
                mensaje = (
                    f"🛒 ¡Skin en oferta!\n"
                    f"{url}\n"
                    f"💵 Precio actual: {precio_actual:.2f} USD\n"
                    f"📉 Tu máximo: {precio_max:.2f} USD"
                )
                enviar_telegram(mensaje)
                notificados[url] = precio_actual

            time.sleep(random.randint(7, 11))

        time.sleep(random.randint(50, 80))
        print("[STATUS] Ciclo completo\n")


# 🔁 Ejecutar el servidor Flask en hilo separado
def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":

    grupos = dividir_skins_en_grupos()

    threads = []

    for i in range(len(grupos)):
        t = threading.Thread(
            target=worker,
            args=(grupos[i],)
        )
        t.start()
        threads.append(t)

    servidor_thread = threading.Thread(target=iniciar_servidor)
    servidor_thread.start()

    for t in threads:
        t.join()

    servidor_thread.join()
