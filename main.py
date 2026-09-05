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
    "http://olrliwpe:v769pjjmxnb1@195.40.128.37:6757",
    "http://olrliwpe:v769pjjmxnb1@192.46.189.205:6198",
    "http://olrliwpe:v769pjjmxnb1@138.226.70.245:7935",
    "http://olrliwpe:v769pjjmxnb1@82.22.73.22:7228",
    "http://olrliwpe:v769pjjmxnb1@195.40.128.230:6950",
    "http://olrliwpe:v769pjjmxnb1@104.252.62.94:5465",
    "http://olrliwpe:v769pjjmxnb1@166.0.40.123:7131",
    "http://olrliwpe:v769pjjmxnb1@203.100.210.175:5324",
    "http://olrliwpe:v769pjjmxnb1@31.98.15.128:5305",
    "http://olrliwpe:v769pjjmxnb1@9.142.42.134:5804"
]

PROXY_COOLDOWN = 600  # 10 min

PROXY_STATUS = {p: 0 for p in PROXIES}
PROXY_FAILS = {p: 0 for p in PROXIES}

# Última vez que se utilizó cada proxy
PROXY_LAST_USED = {p: 0 for p in PROXIES}

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
    "★ StatTrak™ Falchion Knife | Autotronic (Minimal Wear)": 160.00,
    "★ StatTrak™ Huntsman Knife | Damascus Steel (Factory New)": 150.00,
    "★ StatTrak™ Falchion Knife | Crimson Web (Field-Tested)": 170.00,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 146.00,
    "★ StatTrak™ Paracord Knife | Blue Steel (Minimal Wear)": 120.00,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 177.00,
    "★ Classic Knife | Blue Steel (Minimal Wear)": 169.00,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 150.00,
    "★ StatTrak™ Falchion Knife | Black Laminate (Factory New)": 150.00,
    "★ Kukri Knife | Night Stripe (Factory New)": 150.00,
    "★ StatTrak™ Skeleton Knife | Scorched (Field-Tested)": 174.00,
    "★ StatTrak™ Falchion Knife | Freehand (Minimal Wear)": 116.00,
    "★ Falchion Knife | Blue Steel (Well-Worn)": 130.00,
    "★ StatTrak™ Falchion Knife | Damascus Steel (Minimal Wear)": 148.00,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 140.00,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 200.00,
    "★ Paracord Knife | Tiger Tooth (Minimal Wear)": 160.00,
    "★ Paracord Knife | Blue Steel (Factory New)": 199.00,
    "★ Paracord Knife | Crimson Web (Minimal Wear)": 149.00,
    "M4A4 | Asiimov (Well-Worn)": 170.00,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 140.00,
    "★ StatTrak™ Ursus Knife | Crimson Web (Field-Tested)": 170.00,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 150.00,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 180.00,
    "★ Survival Knife | Crimson Web (Minimal Wear)": 131.00,
    "★ Survival Knife | Blue Steel (Factory New)": 150.00,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 440.00,
    "★ Stiletto Knife | Ultraviolet (Well-Worn)": 183.00,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 205.00,
    
}

ITEM_NAME_IDS = {
    "★ StatTrak™ Falchion Knife | Autotronic (Minimal Wear)": 176263237,
    "★ StatTrak™ Huntsman Knife | Damascus Steel (Factory New)": 175885007,
    "★ StatTrak™ Falchion Knife | Crimson Web (Field-Tested)": 49612097,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 176263307,
    "★ StatTrak™ Paracord Knife | Blue Steel (Minimal Wear)": 176097689,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 176263373,
    "★ Classic Knife | Blue Steel (Minimal Wear)": 176091953,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 139673208,
    "★ StatTrak™ Falchion Knife | Black Laminate (Factory New)": 176283223,
    "★ Kukri Knife | Night Stripe (Factory New)": 176420350,
    "★ StatTrak™ Skeleton Knife | Scorched (Field-Tested)": 176097569,
    "★ StatTrak™ Falchion Knife | Freehand (Minimal Wear)": 176263480,
    "★ Falchion Knife | Blue Steel (Well-Worn)": 49422311,
    "★ StatTrak™ Falchion Knife | Damascus Steel (Minimal Wear)": 175882043,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 175885515,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 176097644,
    "★ Paracord Knife | Tiger Tooth (Minimal Wear)": 176507016,
    "★ Paracord Knife | Blue Steel (Factory New)": 176099222,
    "★ Paracord Knife | Crimson Web (Minimal Wear)": 176097544,
    "M4A4 | Asiimov (Well-Worn)": 3455082,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 176045737,
    "★ StatTrak™ Ursus Knife | Crimson Web (Field-Tested)": 176004224,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 176519236,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 175891607,
    "★ Survival Knife | Crimson Web (Minimal Wear)": 176097789,
    "★ Survival Knife | Blue Steel (Factory New)": 176103425,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 29389708,
    "★ Stiletto Knife | Ultraviolet (Well-Worn)": 176043112,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 176047257,
}

notificados = {}
skins_revisadas_total = 0
ciclo_numero = 0
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

lock = threading.Lock()

# Cache temporal de precios
price_cache = {}

# Tiempo mínimo y máximo antes de volver a consultar cada skin
CACHE_MIN_TTL = 240   # 4 minutos
CACHE_MAX_TTL = 330   # 5 minutos y medio

# =========================
# ESTADÍSTICAS
# =========================

stats = {
    "requests_steam": 0,
    "requests_exitosas": 0,
    "requests_fallidas": 0,
    "cache_hits": 0,
    "alertas_enviadas": 0,
    "tiempo_consultas": 0.0
}

def limpiar_cache():

    ahora = time.time()

    with lock:

        keys_a_borrar = []

        for k, v in price_cache.items():

            # Eliminamos caches demasiado viejas.
            # El TTL real de actualización está dado por next_refresh.
            if ahora - v["timestamp"] > CACHE_MAX_TTL * 3:

                keys_a_borrar.append(k)

        for k in keys_a_borrar:

            del price_cache[k]

    print(
        f"[CACHE CLEAN] "
        f"Eliminadas {len(keys_a_borrar)} entradas"
    )

def cache_valida(skin_name):
    ahora = time.time()

    with lock:
        cache_data = price_cache.get(skin_name)

    if cache_data is None:
        return False

    return ahora < cache_data.get("next_refresh", 0)

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

# Header fijo para todas las consultas
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def get_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json,text/javascript,*/*;q=0.1",
        "Referer": "https://steamcommunity.com/market/",
        "Connection": "keep-alive"
    }

def obtener_proxy():
    """
    Selecciona el mejor proxy disponible según:
    1. Tiempo desde el último uso
    2. Cantidad de fallos
    3. Cooldown activo
    4. Disponibilidad inmediata

    Si hay varios proxies disponibles, elige el que lleva
    más tiempo sin utilizarse.

    Si todos están temporalmente ocupados, espera solamente
    hasta que el mejor proxy vuelva a estar disponible.
    """

    while estado_app["activo"]:
        ahora = time.time()
        disponibles = []

        for proxy in PROXIES:

            # 1. Ignorar proxies en cooldown
            if ahora < PROXY_STATUS[proxy]:
                continue

            # 2. Tiempo desde el último uso
            tiempo_sin_uso = ahora - PROXY_LAST_USED[proxy]

            # 3. Penalización por fallos
            fallos = PROXY_FAILS[proxy]
            penalizacion = fallos * 30

            # 4. Score de prioridad
            score = tiempo_sin_uso - penalizacion

            disponibles.append(
                (score, proxy, tiempo_sin_uso)
            )

        # =====================================================
        # HAY PROXIES DISPONIBLES
        # =====================================================

        if disponibles:

            # Mayor score = mejor proxy
            disponibles.sort(
                key=lambda x: x[0],
                reverse=True
            )

            score, proxy_elegido, tiempo_sin_uso = disponibles[0]

            PROXY_LAST_USED[proxy_elegido] = ahora

            print(
                f"[PROXY] {proxy_elegido} | "
                f"Sin uso: {tiempo_sin_uso:.1f}s | "
                f"Fallos: {PROXY_FAILS[proxy_elegido]} | "
                f"Score: {score:.1f}"
            )

            return proxy_elegido

        # =====================================================
        # NINGÚN PROXY DISPONIBLE
        # =====================================================

        tiempos_disponibilidad = [
            PROXY_STATUS[p]
            for p in PROXIES
            if PROXY_STATUS[p] > ahora
        ]

        if tiempos_disponibilidad:

            proximo = min(tiempos_disponibilidad)

            espera = max(
                0.1,
                proximo - ahora
            )

            print(
                f"[PROXY] Todos temporalmente ocupados. "
                f"Esperando {espera:.1f}s..."
            )

            time.sleep(espera)

        else:
            time.sleep(0.5)

    return None
    
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

    if cache_data is not None:

        if ahora < cache_data.get("next_refresh", 0):

            stats["cache_hits"] += 1

            print(
                f"[CACHE HIT] {market_hash_name}"
            )

            return {
                "price": cache_data["price"],
                "buy_price": cache_data.get("buy_price"),
                "name": cache_data["name"],
                "from_cache": True
            }

    # =========================
    # ITEM NAME ID
    # =========================

    item_nameid = ITEM_NAME_IDS.get(market_hash_name)

    if not item_nameid:

        print(
            f"[ERROR] No tengo item_nameid para "
            f"{market_hash_name}"
        )

        return {
            "price": None,
            "name": market_hash_name,
            "from_cache": False,
            "error": "item_nameid"
        }

    # =========================
    # PROXY
    # =========================

    proxies = {
        "http": proxy,
        "https": proxy
    } if proxy else None

    # =========================
    # PARAMETROS STEAM
    # =========================

    params = {
        "country": "US",
        "language": "english",
        "currency": 1,
        "item_nameid": str(item_nameid),
        "two_factor": 0,
        "norender": 1
    }

    try:

        # =========================
        # REQUEST
        # =========================

        inicio_request = time.time()

        with lock:
            stats["requests_steam"] += 1

        r = session.get(
            "https://steamcommunity.com/market/itemordershistogram",
            params=params,
            headers=get_headers(),
            timeout=(10, 20),
            proxies=proxies
        )

        duracion_request = time.time() - inicio_request

        with lock:
            stats["tiempo_consultas"] += duracion_request

        # =========================
        # HTTP 429
        # =========================

        if r.status_code == 429:

            with lock:

                PROXY_FAILS[proxy] += 1

                fallos = PROXY_FAILS[proxy]

                cooldown = min(
                    30 * (2 ** (fallos - 1)),
                    PROXY_COOLDOWN
                )

                PROXY_STATUS[proxy] = (
                    time.time() + cooldown
                )

                stats["requests_fallidas"] += 1

            print(
                f"[429] {market_hash_name} | "
                f"Proxy: {proxy} | "
                f"Cooldown: {cooldown}s"
            )

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "429"
            }

        # =========================
        # OTROS ERRORES HTTP
        # =========================

        if r.status_code != 200:

            print(
                f"[HTTP ERROR HISTOGRAM] "
                f"{proxy} -> {r.status_code}"
            )

            print(
                f"[DEBUG URL] {r.url}"
            )

            print(
                f"[DEBUG RESPONSE] "
                f"{r.text[:500]}"
            )

            with lock:
                PROXY_FAILS[proxy] += 1
                stats["requests_fallidas"] += 1

                # Error HTTP = proxy sospechoso.
                # No lo mandamos directamente a 10 min;
                # dejamos que el score lo penalice.
                if PROXY_FAILS[proxy] >= 3:

                    PROXY_STATUS[proxy] = (
                        time.time() + 60
                    )

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "http"
            }

        # =========================
        # JSON
        # =========================

        try:

            data = r.json()

        except Exception as e:

            print(
                f"[ERROR] Steam no devolvió JSON: {e}"
            )

            print(
                f"[DEBUG] Respuesta: "
                f"{r.text[:500]}"
            )

            with lock:
                PROXY_FAILS[proxy] += 1
                stats["requests_fallidas"] += 1

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "json"
            }

        # =========================
        # STEAM SUCCESS FALSE
        # =========================

        if not data.get("success"):

            with lock:
                stats["requests_fallidas"] += 1

            print(
                f"[HISTOGRAM] Steam respondió "
                f"success=False"
            )

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "steam"
            }

        with lock:
            stats["requests_exitosas"] += 1

        # =========================
        # PRECIOS
        # =========================

        sell_price_raw = data.get("sell_order_price")
        buy_price_raw = data.get("buy_order_price")

        precio = None
        buy_price = None

        # =========================
        # SELL
        # =========================

        if sell_price_raw:

            try:

                sell_clean = re.sub(
                    r"[^0-9.]",
                    "",
                    sell_price_raw
                )

                precio = float(sell_clean)

            except (ValueError, TypeError):

                print(
                    f"[ERROR] No pude interpretar "
                    f"sell_order_price: {sell_price_raw}"
                )

        # =========================
        # BUY
        # =========================

        if buy_price_raw:

            try:

                buy_clean = re.sub(
                    r"[^0-9.]",
                    "",
                    buy_price_raw
                )

                buy_price = float(buy_clean)

            except (ValueError, TypeError):

                print(
                    f"[ERROR] No pude interpretar "
                    f"buy_order_price: {buy_price_raw}"
                )

        # =========================
        # VALIDAR SELL
        # =========================

        if precio is None or precio <= 0:

            print(
                f"[HISTOGRAM] "
                f"No se encontró SELL válido para "
                f"{market_hash_name}"
            )

            return {
                "price": None,
                "buy_price": buy_price,
                "name": market_hash_name,
                "from_cache": False,
                "error": "no_price"
            }

        # =========================
        # LOG
        # =========================

        if buy_price is not None:

            print(
                f"[PRICE] "
                f"{market_hash_name} -> "
                f"SELL ${precio:.2f} | "
                f"BUY ${buy_price:.2f}"
            )

        else:

            print(
                f"[PRICE] "
                f"{market_hash_name} -> "
                f"SELL ${precio:.2f}"
            )

        # =========================
        # CACHE
        # =========================

        ahora = time.time()

        proximo_refresh = (
            ahora +
            random.uniform(
                CACHE_MIN_TTL,
                CACHE_MAX_TTL
            )
        )

        with lock:

            price_cache[market_hash_name] = {
                "price": precio,
                "buy_price": buy_price,
                "name": market_hash_name,
                "timestamp": ahora,
                "next_refresh": proximo_refresh
            }

            # Request exitoso:
            # el proxy vuelve a tener máxima confianza.
            PROXY_FAILS[proxy] = 0
            PROXY_STATUS[proxy] = 0

        return {
            "price": precio,
            "buy_price": buy_price,
            "name": market_hash_name,
            "from_cache": False
        }

    # =========================
    # TIMEOUT
    # =========================

    except requests.exceptions.ReadTimeout:

        print(
            f"[TIMEOUT] {market_hash_name} | "
            f"Proxy: {proxy}"
        )

        with lock:

            PROXY_FAILS[proxy] += 1

            fallos = PROXY_FAILS[proxy]

            # 1 timeout:
            # penalización solamente.

            # 2 timeouts:
            # penalización mayor.

            # 3 timeouts:
            # cooldown completo.

            if fallos >= 3:

                PROXY_STATUS[proxy] = (
                    time.time() + PROXY_COOLDOWN
                )

                print(
                    f"[PROXY COOLDOWN] {proxy} | "
                    f"3 timeouts"
                )

                PROXY_FAILS[proxy] = 0

            stats["requests_fallidas"] += 1

        return {
            "price": None,
            "name": market_hash_name,
            "from_cache": False,
            "error": "timeout"
        }

    # =========================
    # OTROS ERRORES REQUEST
    # =========================

    except requests.exceptions.RequestException as e:

        print(
            f"[REQUEST ERROR] "
            f"{type(e).__name__}: {e}"
        )

        with lock:

            PROXY_FAILS[proxy] += 1

            fallos = PROXY_FAILS[proxy]

            if fallos >= 5:

                PROXY_STATUS[proxy] = (
                    time.time() + PROXY_COOLDOWN
                )

                print(
                    f"[PROXY COOLDOWN] {proxy} | "
                    f"5 errores consecutivos"
                )

                PROXY_FAILS[proxy] = 0

            stats["requests_fallidas"] += 1

        return {
            "price": None,
            "name": market_hash_name,
            "from_cache": False,
            "error": "request"
        }
        
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
    return [list(skins_a_vigilar.items())]

def worker(grupo_skins, worker_id):

    print(f"[DEBUG] Worker {worker_id} arrancó")

    global skins_revisadas_total

    while estado_app["activo"]:

        inicio_ciclo = time.time()

        skins_ordenadas = sorted(
            grupo_skins,
            key=lambda item: price_cache.get(
                item[0],
                {}
            ).get("next_refresh", 0)
        )

        for skin_name, precio_max in skins_ordenadas:

            resultado = None

            MAX_INTENTOS = 2

            for intento in range(MAX_INTENTOS):

                # =========================
                # CACHE ANTES DE PEDIR PROXY
                # =========================

                if cache_valida(skin_name):

                    with lock:
                        cache_data = price_cache.get(skin_name)

                    stats["cache_hits"] += 1

                    resultado = {
                        "price": cache_data["price"],
                        "buy_price": cache_data.get("buy_price"),
                        "name": cache_data["name"],
                        "from_cache": True
                    }

                    print(f"[CACHE HIT] {skin_name}")

                    break

                # =========================
                # NO HAY CACHE → PROXY
                # =========================

                proxy = obtener_proxy()

                if proxy is None:

                    print(
                        f"[WARN] No hay proxy disponible para "
                        f"{skin_name}"
                    )

                    time.sleep(15)

                    continue

                with lock:
                    session = SESSIONS[proxy]

                resultado = buscar_precio(
                    skin_name,
                    session,
                    proxy
                )

                # =========================
                # REQUEST EXITOSO
                # =========================

                if resultado is not None and resultado["price"] is not None:

                    break

                # =========================
                # REQUEST FALLIDO
                # =========================

                error = (
                    resultado.get("error", "desconocido")
                    if resultado
                    else "desconocido"
                )

                print(
                    f"[RETRY] "
                    f"{skin_name} | "
                    f"Error: {error} | "
                    f"Intento {intento + 1}/{MAX_INTENTOS}"
                )

                # No tiene sentido esperar si ya no
                # quedan intentos.
                if intento + 1 >= MAX_INTENTOS:
                    break

                # =========================
                # ESPERA SEGÚN ERROR
                # =========================

                if error == "429":

                    espera = random.uniform(2, 4)

                elif error == "timeout":

                    espera = random.uniform(1, 3)

                elif error in ("http", "request"):

                    espera = random.uniform(2, 5)

                elif error in ("json", "steam"):

                    espera = random.uniform(2, 4)

                else:

                    espera = random.uniform(3, 6)

                print(
                    f"[RETRY] "
                    f"{skin_name} | "
                    f"Esperando {espera:.1f}s "
                    f"antes de nuevo intento"
                )

                time.sleep(espera)

            with lock:
                skins_revisadas_total += 1

            if resultado is None or resultado["price"] is None:
                continue

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
                
                with lock:
                    stats["alertas_enviadas"] += 1

            if not resultado.get("from_cache", False):
                time.sleep(random.uniform(5, 8))

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

            print(f"[INFO] Requests a Steam: {stats['requests_steam']}")

            print(f"[INFO] Requests exitosas: {stats['requests_exitosas']}")

            print(f"[INFO] Requests fallidas: {stats['requests_fallidas']}")

            print(f"[INFO] Cache hits: {stats['cache_hits']}")

            print(f"[INFO] Alertas enviadas: {stats['alertas_enviadas']}")

            print(f"[INFO] Proxies activos: {proxies_activos}")

            print(f"[INFO] Proxies cooldown: {proxies_cooldown}")

            print(f"[INFO] Cache size: {len(price_cache)}")

            print(f"[INFO] Duración ciclo: {duracion} segundos")

            if stats["requests_steam"] > 0:

                promedio = (
                    stats["tiempo_consultas"] /
                    stats["requests_steam"]
                )

                print(
                    f"[INFO] Tiempo promedio/request: "
                    f"{promedio:.2f}s"
                )

            limpiar_cache()

            print("================================================\n")

            skins_revisadas_total = 0

            with lock:
                stats["requests_steam"] = 0
                stats["requests_exitosas"] = 0
                stats["requests_fallidas"] = 0
                stats["cache_hits"] = 0
                stats["tiempo_consultas"] = 0.0

        time.sleep(random.uniform(6, 12))

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
