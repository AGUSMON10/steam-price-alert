import random
import requests
import time
import os
import threading
from flask import Flask, jsonify
from datetime import datetime
import builtins

# Lista de proxies (pegá los tuyos de Webshare)

PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@136.0.167.151:7154",
    "http://olrliwpe:v769pjjmxnb1@46.202.3.10:7276",
    "http://olrliwpe:v769pjjmxnb1@192.46.203.98:6064",
    "http://olrliwpe:v769pjjmxnb1@136.0.170.101:6104",
    "http://olrliwpe:v769pjjmxnb1@82.29.143.14:7728",
    "http://olrliwpe:v769pjjmxnb1@136.0.170.36:6039",
    "http://olrliwpe:v769pjjmxnb1@31.98.8.228:5906",
    "http://olrliwpe:v769pjjmxnb1@150.241.111.94:6598",
    "http://olrliwpe:v769pjjmxnb1@9.142.8.27:5684",
    "http://olrliwpe:v769pjjmxnb1@103.130.178.157:5821"
]

PROXY_COOLDOWN = 900  # 15 min
PROXY_STATUS = {p: 0 for p in PROXIES}


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
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Damascus%20Steel%20%28Factory%20New%29":
    215.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Stained%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    211.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    170.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Case%20Hardened%20%28Minimal%20Wear%29":
    170.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife":
    163.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Lore%20%28Minimal%20Wear%29":
    199.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Classic%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    174.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Case%20Hardened%20%28Well-Worn%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    200.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Kukri%20Knife%20%7C%20Night%20Stripe%20%28Factory%20New%29":
    154.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Skeleton%20Knife%20%7C%20Scorched%20%28Field-Tested%29":
    194.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Specialist%20Gloves%20%7C%20Crimson%20Web%20%28Battle-Scarred%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Nomad%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    112.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Bright%20Water%20%28Well-Worn%29":
    86.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Lore%20%28Well-Worn%29":
    134.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Autotronic%20%28Well-Worn%29":
    134.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Damascus%20Steel%20%28Minimal%20Wear%29":
    147.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Lore%20%28Minimal%20Wear%29":
    175.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Damascus%20Steel%20%28Factory%20New%29":
    133.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    145.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Crimson%20Web%20%28Minimal%20Wear%29":
    210.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    130.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Freehand%20%28Minimal%20Wear%29":
    120.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Huntsman%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    131.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    182.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Shadow%20Daggers%20%7C%20Marble%20Fade%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Shadow%20Daggers%20%7C%20Tiger%20Tooth%20%28Minimal%20Wear%29":
    145.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Shadow%20Daggers%20%7C%20Tiger%20Tooth%20%28Factory%20New%29":
    151.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Classic%20Knife%20%7C%20Crimson%20Web%20%28Minimal%20Wear%29":
    231.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    152.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Flip%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    170.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Case%20Hardened%20%28Field-Tested%29":
    194.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Nomad%20Knife%20%7C%20Stained%20%28Minimal%20Wear%29":
    161.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Nomad%20Knife%20%7C%20Damascus%20Steel%20%28Factory%20New%29":
    221.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    106.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Survival%20Knife%20%7C%20Blue%20Steel%20%28Factory%20New%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Crimson%20Web%20%28Minimal%20Wear%29":
    174.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Flip%20Knife%20%7C%20Ultraviolet%20%28Well-Worn%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Lore%20%28Field-Tested%29":
    200.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Shadow%20Daggers%20%7C%20Case%20Hardened%20%28Minimal%20Wear%29":
    135.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Lore%20%28Field-Tested%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife":
    175.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Ultraviolet%20%28Well-Worn%29":
    100.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    135.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Lore%20%28Field-Tested%29":
    138.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Bowie%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    113.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    142.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Ultraviolet%20%28Field-Tested%29":
    142.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    215.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Ultraviolet%20%28Minimal%20Wear%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Nomad%20Knife%20%7C%20Damascus%20Steel%20%28Minimal%20Wear%29":
    200.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Gut%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    100.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Gut%20Knife%20%7C%20Autotronic%20%28Minimal%20Wear%29":
    149.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Gut%20Knife%20%7C%20Autotronic%20%28Field-Tested%29":
    148.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Skeleton%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    231.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Paracord%20Knife%20%7C%20Stained%20%28Factory%20New%29":
    134.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    142.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Survival%20Knife%20%7C%20Crimson%20Web%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/StatTrak%E2%84%A2%20AWP%20%7C%20Asiimov%20%28Battle-Scarred%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/StatTrak%E2%84%A2%20AWP%20%7C%20Man-o%27-war%20%28Minimal%20Wear%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/StatTrak%E2%84%A2%20AWP%20%7C%20Neo-Noir%20%28Factory%20New%29":
    122.00,
    "https://steamcommunity.com/market/listings/730/StatTrak%E2%84%A2%20AWP%20%7C%20Corticera%20%28Factory%20New%29":
    164.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Survival%20Knife%20%7C%20Damascus%20Steel%20%28Minimal%20Wear%29":
    106.00,
    "https://steamcommunity.com/market/listings/730/StatTrak%E2%84%A2%20M4A4%20%7C%20%E9%BE%8D%E7%8E%8B%20%28Dragon%20King%29%20%28Factory%20New%29":
    135.00,
    "https://steamcommunity.com/market/listings/730/Souvenir%20M4A4%20%7C%20Hellish%20%28Minimal%20Wear%29":
    140.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Lore%20%28Well-Worn%29":
    125.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Blue%20Steel%20%28Well-Worn%29":
    153.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Freehand%20%28Factory%20New%29":
    165.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Bright%20Water%20%28Factory%20New%29":
    145.00
}

notificados = {}
ultimo_escaneo = None
skins_revisadas_total = 0
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

lock = threading.Lock()


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
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json,text/javascript,*/*;q=0.1",
        "Referer": "https://steamcommunity.com/market/"
    }

def obtener_proxy():
    ahora = time.time()

    disponibles = [p for p, t in PROXY_STATUS.items() if t <= ahora]

    print(f"[DEBUG] Proxies disponibles: {len(disponibles)}")

    if not disponibles:
        if len(PROXY_STATUS) == len(PROXIES):
            print("[WARN] Reset de cooldown global de proxies")
            for p in PROXY_STATUS:
                PROXY_STATUS[p] = 0
            return random.choice(PROXIES)

        print("[WARN] Todos los proxies en cooldown")
        return None

    return random.choice(disponibles)

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


def obtener_nombre_skin(url):
    # toma el texto después de /730/
    return url.split("/730/")[-1].replace("%20", " ").replace("%E2%98%85", "").strip()

def obtener_id_item(url):
    return url.split("/730/")[-1].replace("★", "").strip()
    
def buscar_precio(nombre, session, proxy):
    print(f"\n[DEBUG] === BUSCANDO: {nombre} ===")

    url = "https://steamcommunity.com/market/search/render/"

    params = {
        "query": nombre,
        "start": 0,
        "count": 10,
        "currency": 1,
        "language": "english",
        "norender": 1
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        r = session.get(
            url,
            params=params,
            headers=get_headers(),
            timeout=10,
            proxies=proxies
        )

        print(f"[DEBUG] Status code: {r.status_code}")

        if r.status_code != 200:
            return None

        data = r.json()
        results = data.get("results", [])

        if not results:
            print("[DEBUG] Sin resultados")
            return None

        query = nombre.lower()

        for item in results:

            name = item.get("name", "").lower()
            price = item.get("sell_price")

            print(f"[DEBUG] ITEM NAME: {item.get('name')}")
            print(f"[DEBUG] ITEM PRICE RAW: {price}")

            if not price:
                continue

            final_price = price / 100
            print(f"[DEBUG] PRECIO SELECCIONADO: {final_price} USD")

            # filtro básico para evitar basura
            if query.split("%")[0] in name or name in query:
                return final_price

        # si no matchea bien, devuelve el primero válido igual
        for item in results:
            price = item.get("sell_price")
            if price:
                return price / 100

        return None

    except Exception as e:
        print(f"[DEBUG] ERROR: {e}")
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

    # 1 grupo por worker fijo (10 workers máximo recomendado)
    num_workers = min(8, len(lista))

    grupos = [[] for _ in range(num_workers)]

    for i, item in enumerate(lista):
        grupos[i % num_workers].append(item)

    return grupos

def worker(grupo_skins, worker_id):
    print(f"[DEBUG] Worker {worker_id} arrancó")
    print(f"[DEBUG] Items recibidos: {len(grupo_skins)}")
    
    session = requests.Session()
    global skins_revisadas_total

    while estado_app["activo"]:
        inicio_ciclo = time.time()

        for url, precio_max in grupo_skins:

            proxy = obtener_proxy()

            if proxy is None:
                time.sleep(2)
                continue

            item_id = obtener_id_item(url)
            precio_actual = buscar_precio(item_id, session, proxy)

            with lock:
                skins_revisadas_total += 1

            if precio_actual is None:
                time.sleep(2)
                continue

            ultima_alerta = notificados.get(url)

            if precio_actual <= precio_max and (
                ultima_alerta is None or precio_actual < ultima_alerta
            ):
                mensaje = (
                    f"🛒 Skin en oferta\n"
                    f"{url}\n"
                    f"💵 {precio_actual:.2f} USD\n"
                    f"📉 Max {precio_max:.2f} USD"
                )

                enviar_telegram(mensaje)
                notificados[url] = precio_actual

            time.sleep(random.uniform(4, 7))

        estado_app["ultimo_escaneo"] = datetime.now().isoformat()

        if worker_id == 0:
            with lock:
                total = skins_revisadas_total
                skins_revisadas_total = 0

            duracion = round(time.time() - inicio_ciclo, 1)

            print(f"[INFO] Skins revisadas (ciclo): {total}")
            print(f"[INFO] Duración ciclo: {duracion}s")
            print(f"[INFO] Notificados: {len(notificados)}")

        time.sleep(random.uniform(20, 40))
            
# 🔁 Ejecutar el servidor Flask en hilo separado
def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)

if __name__ == "__main__":

    grupos = dividir_skins_en_grupos()

    print("=== DEBUG SYSTEM ===")
    print("Skins:", len(skins_a_vigilar))
    print("Proxies:", len(PROXIES))
    print("Grupos:", len(dividir_skins_en_grupos()))
    print("====================")

    threads = []

    for i, grupo in enumerate(grupos):
        t = threading.Thread(target=worker, args=(grupo, i))
        t.start()
        threads.append(t)

    servidor_thread = threading.Thread(target=iniciar_servidor)
    servidor_thread.start()

    for t in threads:
        t.join()

    servidor_thread.join()
