import random
import requests
import time
import os
import threading
import re
from flask import Flask, jsonify
from datetime import datetime
import builtins

# Lista de proxies (pegá los tuyos de Webshare)

PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@130.180.232.130:8568",
    "http://olrliwpe:v769pjjmxnb1@96.62.181.13:7225",
    "http://olrliwpe:v769pjjmxnb1@82.29.239.219:5367",
    "http://olrliwpe:v769pjjmxnb1@87.86.24.154:5805",
    "http://olrliwpe:v769pjjmxnb1@31.98.15.224:5401",
    "http://olrliwpe:v769pjjmxnb1@209.166.2.202:7863",
    "http://olrliwpe:v769pjjmxnb1@45.58.228.57:5729",
    "http://olrliwpe:v769pjjmxnb1@5.59.251.216:6255",
    "http://olrliwpe:v769pjjmxnb1@9.142.218.36:6700",
    "http://olrliwpe:v769pjjmxnb1@9.142.195.37:6205"
]

PROXY_COOLDOWN = 600  # 10 min
PROXY_STATUS = {p: 0 for p in PROXIES}
PROXY_FAILS = {p: 0 for p in PROXIES}

# Redefinir print global con flush automático
original_print = print

def normalizar(texto):

    texto = texto.lower()

    texto = texto.replace("★", "")

    texto = texto.replace("™", "")

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()

def es_item_valido(name):
    name = name.lower()

    blacklist = [
        "case",
        "key",
        "capsule",
        "graffiti",
        "soundtrack",
        "booster",
        "package",
        "sealed",
        "gift"
    ]

    for b in blacklist:
        if b in name:
            return False

    return True
    
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
    "Knife falchion ★ StatTrak™ | Autotronic minimal": 165.00,
    "StatTrak Huntsman Knife | Damascus Steel Factory": 170.00,
    "StatTrak Falchion Knife | Stained Minimal": 125.00,
    "StatTrak Falchion Knife | Crimson Web Field": 180.00,
    "StatTrak Bowie Knife | Autotronic Minimal": 145.00,
    "stattrak Paracord Knife | Blue Steel Minimal": 150.00,
    "StatTrak Falchion Knife | Lore Minimal": 190.00,
    "Classic Knife | Blue Steel Minimal": 169.00,
    "Bowie Knife | Blue Steel Minimal": 160.00,
    "StatTrak Falchion Knife | Black Laminate Factory": 175.00,
    
}

notificados = {}
ultimo_escaneo = None
skins_revisadas_total = 0
ciclo_numero = 0
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

lock = threading.Lock()

# Cache temporal de precios
price_cache = {}
CACHE_TTL = 130  # segundos

failed_counts = {}

def limpiar_cache():

    ahora = time.time()

    with lock:

        keys_a_borrar = []

        for k, v in price_cache.items():

            if ahora - v["timestamp"] > CACHE_TTL * 3:

                keys_a_borrar.append(k)

        for k in keys_a_borrar:

            del price_cache[k]

    print(f"[CACHE CLEAN] Eliminadas {len(keys_a_borrar)} entradas")

# Crear sessions optimizadas
def crear_session():

    s = requests.Session()

    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20
    )

    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s

# Una session independiente por proxy
SESSIONS = {}

for proxy in PROXIES:

    SESSIONS[proxy] = crear_session()

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
        "Referer": "https://steamcommunity.com/market/",
        "Connection": "keep-alive"
    }

def obtener_proxy():

    ahora = time.time()

    disponibles = [
        p for p, t in PROXY_STATUS.items()
        if t <= ahora
    ]

    if not disponibles:

        cooldown_activos = [
            p for p, t in PROXY_STATUS.items()
            if t > ahora
        ]

        print(
            f"[WARN] Sin proxies disponibles | "
            f"Cooldown: {len(cooldown_activos)}"
        )

        # reset global si TODOS están en cooldown
        if len(cooldown_activos) == len(PROXIES):

            print("[WARN] Todos los proxies en cooldown")

            return None

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
    
def buscar_precio(market_hash_name, session, proxy):

    ahora = time.time()

    # =========================
    # CACHE
    # =========================

    with lock:
        cache_data = price_cache.get(market_hash_name)

    if cache_data:

        if ahora - cache_data["timestamp"] < CACHE_TTL:

            print(f"[CACHE HIT] {market_hash_name}")

            return {
                "price": cache_data["price"],
                "name": cache_data["name"]
            }

    print(f"\n[DEBUG] === PRICEOVERVIEW: {market_hash_name} ===")

    url = "https://steamcommunity.com/market/priceoverview/"

    params = {
        "appid": 730,
        "currency": 1,
        "market_hash_name": market_hash_name
    }

    proxies = {
        "http": proxy,
        "https": proxy
    } if proxy else None

    try:

        r = session.get(
            url,
            params=params,
            headers=get_headers(),
            timeout=(8, 12),
            proxies=proxies
        )

        print(f"[HTTP] {proxy} -> {r.status_code}")

        # =========================
        # RATE LIMIT
        # =========================

        if r.status_code == 429:

            print(f"[RATE LIMIT PRICEOVERVIEW] {proxy}")

            with lock:

                PROXY_STATUS[proxy] = (
                    time.time() + PROXY_COOLDOWN
                )

                SESSIONS[proxy] = crear_session()

                PROXY_FAILS[proxy] = 0

            return None

        # =========================
        # OTROS ERRORES HTTP
        # =========================

        if r.status_code != 200:

            print(
                f"[HTTP ERROR] "
                f"{proxy} -> {r.status_code}"
            )

            with lock:

                PROXY_FAILS[proxy] += 1

                if PROXY_FAILS[proxy] >= 5:

                    PROXY_STATUS[proxy] = (
                        time.time() + PROXY_COOLDOWN
                    )

                    print(
                        f"[PROXY COOLDOWN] "
                        f"{proxy}"
                    )

                    PROXY_FAILS[proxy] = 0

            return None

        # =========================
        # JSON
        # =========================

        data = r.json()

        print(
            f"[PRICEOVERVIEW] "
            f"{market_hash_name} -> "
            f"{data}"
        )

        # =========================
        # STEAM SUCCESS
        # =========================

        if not data.get("success"):

            print(
                f"[STEAM] Sin datos para: "
                f"{market_hash_name}"
            )

            return {
                "price": None,
                "name": market_hash_name
            }

        lowest_price = data.get("lowest_price")

        if not lowest_price:

            print(
                f"[STEAM] Sin lowest_price: "
                f"{market_hash_name}"
            )

            return {
                "price": None,
                "name": market_hash_name
            }

        # =========================
        # CONVERTIR PRECIO
        # =========================

        precio_texto = (
            lowest_price
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

        try:

            precio = float(precio_texto)

        except ValueError:

            print(
                f"[ERROR] No pude convertir "
                f"precio: {lowest_price}"
            )

            return {
                "price": None,
                "name": market_hash_name
            }

        # =========================
        # GUARDAR CACHE
        # =========================

        with lock:

            price_cache[market_hash_name] = {
                "price": precio,
                "name": market_hash_name,
                "timestamp": ahora
            }

            PROXY_FAILS[proxy] = 0

        print(
            f"[PRICE] "
            f"{market_hash_name} -> "
            f"${precio:.2f}"
        )

        return {
            "price": precio,
            "name": market_hash_name
        }

    except Exception as e:

        print(
            f"[DEBUG] ERROR PRICEOVERVIEW: "
            f"{type(e).__name__}: {e}"
        )

        with lock:

            PROXY_FAILS[proxy] += 1

            if PROXY_FAILS[proxy] >= 5:

                PROXY_STATUS[proxy] = (
                    time.time() + PROXY_COOLDOWN
                )

                print(
                    f"[PROXY COOLDOWN] "
                    f"{proxy}"
                )

                PROXY_FAILS[proxy] = 0

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

    num_workers = 1

    grupos = [[] for _ in range(num_workers)]

    for i, item in enumerate(lista):

        grupos[i % num_workers].append(item)

    return grupos

def worker(grupo_skins, worker_id):

    print(f"[DEBUG] Worker {worker_id} arrancó")

    global skins_revisadas_total

    while estado_app["activo"]:

        inicio_ciclo = time.time()

        for skin_name, precio_max in grupo_skins:

            resultado = None

            for intento in range(1):

                proxy = obtener_proxy()

                if proxy is None:

                    time.sleep(2)

                    continue

                with lock:
                    session = SESSIONS[proxy]

                resultado = buscar_precio(
                    skin_name,
                    session,
                    proxy
                )

                if resultado is not None:

                    break

                print(
                    f"[RETRY] "
                    f"{skin_name} | "
                    f"Intento {intento + 1}"
                )

                time.sleep(random.uniform(1, 2))

            if resultado is None:
                continue

            with lock:
                skins_revisadas_total += 1

            precio_actual = resultado["price"]
            nombre_real = resultado["name"]

            ultima_alerta = notificados.get(skin_name)

            if precio_actual <= precio_max and (
                ultima_alerta is None
                or precio_actual < ultima_alerta
            ):

                steam_url = (
                    "steam://openurl/https://steamcommunity.com/market/listings/730/"
                    + requests.utils.quote(nombre_real, safe='')
                )

                enviar_telegram(
                    f"🛒 Skin en oferta\n"
                    f"{skin_name}\n"
                    f"{steam_url}\n"
                    f"💵 {precio_actual:.2f} USD\n"
                    f"📉 Max {precio_max:.2f} USD"
                )

                notificados[skin_name] = precio_actual

            time.sleep(random.uniform(3, 6))

        estado_app["ultimo_escaneo"] = datetime.now().isoformat()

        if worker_id == 0:

            global ciclo_numero

            ciclo_numero += 1

            duracion = round(time.time() - inicio_ciclo, 2)

            ahora = time.time()

            proxies_activos = len([
                p for p, t in PROXY_STATUS.items()
                if t <= ahora
            ])

            proxies_cooldown = len([
                p for p, t in PROXY_STATUS.items()
                if t > ahora
            ])

            print("\n================ RESUMEN CICLO ================")

            print(f"[INFO] Ciclo número: {ciclo_numero}")

            print(f"[INFO] Skins totales vigiladas: {len(skins_a_vigilar)}")

            print(f"[INFO] Skins revisadas: {skins_revisadas_total}")

            print(f"[INFO] Proxies activos: {proxies_activos}")

            print(f"[INFO] Proxies cooldown: {proxies_cooldown}")

            print(f"[INFO] Cache size: {len(price_cache)}")

            limpiar_cache()

            print(f"[INFO] Duración ciclo: {duracion} segundos")

            skins_a_eliminar = []

            for skin, fails in failed_counts.items():

                if fails >= 50:

                    print("\n[INFO] Skin desactivada por demasiados fallos:")
                    print(skin)

                    skins_a_eliminar.append(skin)

            # eliminar skins problemáticas
            for skin_name in skins_a_eliminar:

                if skin_name in skins_a_vigilar:

                    del skins_a_vigilar[skin_name]

                    print(f"[INFO] Eliminada del monitoreo: {skin_name}")

            print()

            print("================================================\n")

            skins_revisadas_total = 0

        time.sleep(random.uniform(15, 30))

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
