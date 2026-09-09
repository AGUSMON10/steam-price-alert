import random
import requests
import time
import os
import threading
import re
import json
from flask import Flask, jsonify
from datetime import datetime
import builtins
from zoneinfo import ZoneInfo

ZONA_ARG = ZoneInfo("America/Argentina/Buenos_Aires")

ARCHIVO_ESTADO = "bot_state.json"

# Lista de proxies (pegá los tuyos de Webshare)

PROXIES = [
    "http://olrliwpe:v769pjjmxnb1@195.40.128.37:6757",
    "http://olrliwpe:v769pjjmxnb1@192.46.189.205:6198",
    "http://olrliwpe:v769pjjmxnb1@138.226.70.245:7935",
    "http://olrliwpe:v769pjjmxnb1@82.22.73.22:7228",
    "http://olrliwpe:v769pjjmxnb1@195.40.128.230:6950",
    "http://olrliwpe:v769pjjmxnb1@166.0.40.123:7131",
    "http://olrliwpe:v769pjjmxnb1@203.100.210.175:5324",
    "http://olrliwpe:v769pjjmxnb1@31.98.15.128:5305",
    "http://olrliwpe:v769pjjmxnb1@9.142.42.134:5804",
    "http://olrliwpe:v769pjjmxnb1@103.243.147.64:6043",
]

PROXY_COOLDOWN = 600  # 10 min

PROXY_429_COOLDOWN_BASE = 90
PROXY_429_COOLDOWN_MAX = 600

PROXY_MIN_INTERVAL = 8
# Tiempo mínimo entre requests reales a Steam
GLOBAL_MIN_REQUEST_INTERVAL = 2.0
LAST_STEAM_REQUEST = 0

PROXY_STATUS = {p: 0 for p in PROXIES}
PROXY_FAILS = {p: 0 for p in PROXIES}
PROXY_429_FAILS = {p: 0 for p in PROXIES}

# Última vez que se utilizó cada proxy
PROXY_LAST_USED = {p: 0 for p in PROXIES}

# PAUSA
PROXIMA_PAUSA = time.time() + random.uniform(7200, 10800)

# Redefinir print global con flush automático
original_print = print
    
def flush_print(*args, **kwargs):
    kwargs['flush'] = True
    timestamp = datetime.now(ZONA_ARG).strftime("%H:%M:%S")
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
    "★ StatTrak™ Huntsman Knife | Damascus Steel (Factory New)": 151.00,
    "★ StatTrak™ Falchion Knife | Crimson Web (Field-Tested)": 170.00,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 139.00,
    "★ StatTrak™ Paracord Knife | Blue Steel (Minimal Wear)": 120.00,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 160.00,
    "★ Classic Knife | Blue Steel (Minimal Wear)": 156.00,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 150.00,
    "★ StatTrak™ Falchion Knife | Black Laminate (Factory New)": 150.00,
    "★ Kukri Knife | Night Stripe (Factory New)": 145.00,
    "★ StatTrak™ Skeleton Knife | Scorched (Field-Tested)": 174.00,
    "★ Falchion Knife | Blue Steel (Well-Worn)": 139.00,
    "★ StatTrak™ Falchion Knife | Damascus Steel (Minimal Wear)": 148.00,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 140.00,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 200.00,
    "★ Paracord Knife | Tiger Tooth (Minimal Wear)": 152.00,
    "★ Paracord Knife | Blue Steel (Factory New)": 185.00,
    "M4A4 | Asiimov (Well-Worn)": 170.00,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 140.00,
    "★ StatTrak™ Ursus Knife | Crimson Web (Field-Tested)": 170.00,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 150.00,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 180.00,
    "★ Survival Knife | Crimson Web (Minimal Wear)": 131.00,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 440.00,
    "★ Stiletto Knife | Ultraviolet (Well-Worn)": 183.00,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 205.00,
    "★ StatTrak™ Nomad Knife | Crimson Web (Well-Worn)": 184.00,
    "★ Falchion Knife | Crimson Web (Well-Worn)": 128.00,
    "★ Falchion Knife | Tiger Tooth (Minimal Wear)": 184.00,
    "StatTrak™ USP-S | Neo-Noir (Minimal Wear)": 135.00,
    "StatTrak™ USP-S | Printstream (Well-Worn)": 63.00,
    "StatTrak™ Desert Eagle | Ocean Drive (Minimal Wear)": 130.00,
    "StatTrak™ AWP | Man-o'-war (Field-Tested)": 139.00,
    "StatTrak™ SSG 08 | Dragonfire (Factory New)": 230.00,
    "M4A1-S | Master Piece (Minimal Wear)": 198.00,
    "StatTrak™ M4A1-S | Chantico's Fire (Minimal Wear)": 180.00,
    "StatTrak™ M4A1-S | Hyper Beast (Minimal Wear)": 200.00,
    "★ Bowie Knife | Tiger Tooth (Minimal Wear)": 172.00,
    "★ Bowie Knife | Crimson Web (Minimal Wear)": 222.00,
    "★ Survival Knife | Blue Steel (Factory New)": 147.00,
    "★ Classic Knife | Stained (Minimal Wear)": 129.00,
    "★ StatTrak™ Classic Knife | Blue Steel (Field-Tested)": 139.00,
    
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
    "★ Falchion Knife | Blue Steel (Well-Worn)": 49422311,
    "★ StatTrak™ Falchion Knife | Damascus Steel (Minimal Wear)": 175882043,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 175885515,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 176097644,
    "★ Paracord Knife | Tiger Tooth (Minimal Wear)": 176507016,
    "★ Paracord Knife | Blue Steel (Factory New)": 176099222,
    "M4A4 | Asiimov (Well-Worn)": 3455082,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 176045737,
    "★ StatTrak™ Ursus Knife | Crimson Web (Field-Tested)": 176004224,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 176519236,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 175891607,
    "★ Survival Knife | Crimson Web (Minimal Wear)": 176097789,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 29389708,
    "★ Stiletto Knife | Ultraviolet (Well-Worn)": 176043112,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 176047257,
    "★ StatTrak™ Nomad Knife | Crimson Web (Well-Worn)": 176097950,
    "★ Falchion Knife | Crimson Web (Well-Worn)": 49461583,
    "★ Falchion Knife | Tiger Tooth (Minimal Wear)": 175881471,
    "StatTrak™ USP-S | Neo-Noir (Minimal Wear)": 175880519,
    "StatTrak™ USP-S | Printstream (Well-Worn)": 176321377,
    "StatTrak™ Desert Eagle | Ocean Drive (Minimal Wear)": 176263203,
    "StatTrak™ AWP | Man-o'-war (Field-Tested)": 29285565,
    "StatTrak™ SSG 08 | Dragonfire (Factory New)": 175854470,
    "M4A1-S | Master Piece (Minimal Wear)": 14953196,
    "StatTrak™ M4A1-S | Chantico's Fire (Minimal Wear)": 149922266,
    "StatTrak™ M4A1-S | Hyper Beast (Minimal Wear)": 40194354,
    "★ Bowie Knife | Tiger Tooth (Minimal Wear)": 175881329,
    "★ Bowie Knife | Crimson Web (Minimal Wear)": 139966115,
    "★ Survival Knife | Blue Steel (Factory New)": 176103425,
    "★ Classic Knife | Stained (Minimal Wear)": 176091945,
    "★ StatTrak™ Classic Knife | Blue Steel (Field-Tested)": 176091948,
}

notificados = {}
skins_revisadas_total = 0
ciclo_numero = 0
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

lock = threading.Lock()

# Cache temporal de precios
price_cache = {}

# Control de skins problemáticas
SKIN_MAX_FAILS = 3
SKIN_COOLDOWN = 600  # 10 minutos

SKIN_FAILS = {skin: 0 for skin in skins_a_vigilar}
SKIN_COOLDOWN_UNTIL = {skin: 0 for skin in skins_a_vigilar}

# =========================
# TTL DINÁMICO
# =========================

CACHE_MAX_TTL = 180

ALERTA_DOBLE_DESCUENTO = 0.133
ALERTA_DOBLE_INTERVALO = 15


def calcular_ttl(precio, precio_max):

    if precio is None or precio_max <= 0:
        return random.uniform(170, 210)

    distancia = (precio - precio_max) / precio_max

    # Precio igual o por debajo del máximo
    if distancia <= 0:
        return random.uniform(75, 105)

    # Hasta 5% por encima
    elif distancia <= 0.05:
        return random.uniform(85, 120)

    # Entre 5% y 10%
    elif distancia <= 0.10:
        return random.uniform(105, 140)

    # Entre 10% y 15%
    elif distancia <= 0.15:
        return random.uniform(130, 165)

    # Entre 15% y 25%
    elif distancia <= 0.25:
        return random.uniform(155, 190)

    # Muy lejos del objetivo
    else:
        return random.uniform(175, 210)

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

# ============================================================
# ESTADÍSTICAS DIARIAS
# ============================================================

stats_diarias = {
    "requests_steam": 0,
    "requests_exitosas": 0,
    "requests_fallidas": 0,
    "cache_hits": 0,
    "alertas_enviadas": 0,
    "alertas_dobles": 0,
    "ciclos": 0,
    "tiempo_consultas": 0.0,
    "tiempo_ciclos": 0.0,
    "pausas_programadas": 0,
    "tiempo_pausas": 0.0,
}

stats_proxies = {
    proxy: {
        "requests": 0,
        "exitosas": 0,
        "fallidas": 0,
        "429": 0,
        "timeouts": 0,
        "http": 0,
        "json": 0,
        "steam": 0,
        "request": 0,
        "tiempo_total": 0.0,
        "cooldowns": 0,
    }
    for proxy in PROXIES
}

fecha_estadisticas = datetime.now(ZONA_ARG).date()

def guardar_estado():
    try:
        estado = {
            "fecha_estadisticas": fecha_estadisticas.isoformat(),
            "stats_diarias": stats_diarias,
            "stats_proxies": list(stats_proxies.values()),
            "price_cache": price_cache,
            "notificados": notificados,
        }

        archivo_temporal = ARCHIVO_ESTADO + ".tmp"

        with open(archivo_temporal, "w", encoding="utf-8") as f:
            json.dump(
                estado,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(archivo_temporal, ARCHIVO_ESTADO)

    except Exception as e:
        print(f"[ERROR] No se pudo guardar el estado: {e}")


def cargar_estado():
    global fecha_estadisticas

    if not os.path.exists(ARCHIVO_ESTADO):
        print("[INFO] No existe estado guardado. Se inicia desde cero.")
        return

    try:
        with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
            estado = json.load(f)

        # =========================
        # FECHA
        # =========================

        fecha_guardada = estado.get("fecha_estadisticas")

        if fecha_guardada:
            fecha_estadisticas = datetime.fromisoformat(
                fecha_guardada
            ).date()

        # =========================
        # STATS DIARIAS
        # =========================

        stats_guardadas = estado.get("stats_diarias", {})

        for key in stats_diarias:
            if key in stats_guardadas:
                stats_diarias[key] = stats_guardadas[key]

        # =========================
        # STATS POR PROXY
        # =========================

        stats_proxies_guardadas = estado.get(
            "stats_proxies",
            []
        )

        proxies_actuales = list(stats_proxies.keys())

        for i, datos in enumerate(stats_proxies_guardadas):

            if i >= len(proxies_actuales):
                break

            proxy = proxies_actuales[i]

            for key in stats_proxies[proxy]:

                if key in datos:
                    stats_proxies[proxy][key] = datos[key]

        # =========================
        # CACHE
        # =========================

        cache_guardada = estado.get(
            "price_cache",
            {}
        )

        price_cache.clear()

        for skin, datos in cache_guardada.items():

            if not isinstance(datos, dict):
                continue

            if "price" not in datos:
                continue

            price_cache[skin] = datos

        # =========================
        # NOTIFICADOS
        # =========================

        notificados_guardados = estado.get(
            "notificados",
            {}
        )

        notificados.clear()

        for skin, precio in notificados_guardados.items():
            notificados[skin] = precio

        print(
            f"[INFO] Estado recuperado correctamente | "
            f"Cache: {len(price_cache)} | "
            f"Notificados: {len(notificados)} | "
            f"Fecha: {fecha_estadisticas.strftime('%d/%m/%Y')}"
        )

    except Exception as e:
        print(
            f"[ERROR] No se pudo cargar el estado: {e}"
        )
        print(
            "[INFO] El bot continuará con los valores actuales."
        )

# Cargar estado guardado al iniciar el bot
cargar_estado()

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

    if keys_a_borrar:
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

def skin_en_cooldown(skin_name):
    ahora = time.time()
    cooldown_hasta = SKIN_COOLDOWN_UNTIL.get(skin_name, 0)

    if ahora < cooldown_hasta:
        return True

    return False
    
def registrar_error_skin(skin_name, error):

    with lock:

        SKIN_FAILS[skin_name] = (
            SKIN_FAILS.get(skin_name, 0) + 1
        )

        fallos = SKIN_FAILS[skin_name]

        print(
            f"[SKIN ERROR] {skin_name} | "
            f"Motivo: {error} | "
            f"Fallos consecutivos: "
            f"{fallos}/{SKIN_MAX_FAILS}"
        )

        if fallos >= SKIN_MAX_FAILS:
            SKIN_COOLDOWN_UNTIL[skin_name] = time.time() + SKIN_COOLDOWN

            print(
                f"[SKIN COOLDOWN] {skin_name} | "
                f"Motivo: {fallos} fallos consecutivos | "
                f"Cooldown: {SKIN_COOLDOWN // 60} minutos"
            )

            SKIN_FAILS[skin_name] = 0
            
def registrar_exito_skin(skin_name):

    with lock:

        if SKIN_FAILS.get(skin_name, 0) > 0:

            print(
                f"[SKIN OK] {skin_name} | "
                f"Fallos consecutivos reseteados"
            )

        SKIN_FAILS[skin_name] = 0

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

            if tiempo_sin_uso < PROXY_MIN_INTERVAL:
                continue

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
                proximo - ahora + random.uniform(1, 3)
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
        "timestamp": datetime.now(ZONA_ARG).isoformat()
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

    global LAST_STEAM_REQUEST

    ahora = time.time()

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
            stats_diarias["requests_steam"] += 1
            stats_proxies[proxy]["requests"] += 1

        # ==========================================
        # ESPACIAR REQUESTS A STEAM
        # ==========================================

        ahora = time.time()

        with lock:
            tiempo_desde_ultimo_request = (
                ahora - LAST_STEAM_REQUEST
            )

        if tiempo_desde_ultimo_request < GLOBAL_MIN_REQUEST_INTERVAL:

            espera = (
                GLOBAL_MIN_REQUEST_INTERVAL
                - tiempo_desde_ultimo_request
                + random.uniform(0.2, 0.8)
            )

            time.sleep(espera)

        with lock:
            LAST_STEAM_REQUEST = time.time()


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
            stats_diarias["tiempo_consultas"] += duracion_request
            stats_proxies[proxy]["tiempo_total"] += duracion_request

        # =========================
        # HTTP 429
        # =========================

        if r.status_code == 429:

            with lock:

                PROXY_FAILS[proxy] += 1
                PROXY_429_FAILS[proxy] += 1

                fallos_429 = PROXY_429_FAILS[proxy]

                cooldown = min(
                    PROXY_429_COOLDOWN_BASE * (2 ** (fallos_429 - 1)),
                    PROXY_429_COOLDOWN_MAX
                )

                PROXY_STATUS[proxy] = time.time() + cooldown

                stats["requests_fallidas"] += 1
                stats_diarias["requests_fallidas"] += 1

                stats_proxies[proxy]["fallidas"] += 1
                stats_proxies[proxy]["429"] += 1
                stats_proxies[proxy]["cooldowns"] += 1

            print(
                f"[429] {market_hash_name} | "
                f"Proxy: {proxy} | "
                f"429 consecutivos: {fallos_429} | "
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
                stats_diarias["requests_fallidas"] += 1
                stats_proxies[proxy]["fallidas"] += 1
                stats_proxies[proxy]["http"] += 1

                # Error HTTP = proxy sospechoso.
                # No lo mandamos directamente a 10 min;
                # dejamos que el score lo penalice.
                if PROXY_FAILS[proxy] >= 3:

                    PROXY_STATUS[proxy] = (
                        time.time() + 60
                    )

                    stats_proxies[proxy]["cooldowns"] += 1
                    PROXY_FAILS[proxy] = 0

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
                stats_diarias["requests_fallidas"] += 1
                stats_proxies[proxy]["fallidas"] += 1
                stats_proxies[proxy]["json"] += 1

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
                stats_diarias["requests_fallidas"] += 1
                stats_proxies[proxy]["fallidas"] += 1
                stats_proxies[proxy]["steam"] += 1

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
            stats_diarias["requests_exitosas"] += 1
            stats_proxies[proxy]["exitosas"] += 1

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

        precio_max = skins_a_vigilar.get(
            market_hash_name,
            precio
        )

        ttl = calcular_ttl(
            precio,
            precio_max
        )

        # Jitter adicional para evitar que muchas skins
        # vuelvan a consultarse al mismo tiempo.
        jitter_cache = random.uniform(0, 30)

        proximo_refresh = ahora + ttl + jitter_cache

        print(
            f"[PRIORIDAD] "
            f"{market_hash_name} | "
            f"Precio: ${precio:.2f} | "
            f"Máx: ${precio_max:.2f} | "
            f"Próxima consulta: {ttl + jitter_cache:.0f}s"
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
            PROXY_429_FAILS[proxy] = 0
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

                stats_proxies[proxy]["cooldowns"] += 1

                print(
                    f"[PROXY COOLDOWN] {proxy} | "
                    f"3 timeouts"
                )

                PROXY_FAILS[proxy] = 0

            stats["requests_fallidas"] += 1
            stats_diarias["requests_fallidas"] += 1
            stats_proxies[proxy]["fallidas"] += 1
            stats_proxies[proxy]["timeouts"] += 1

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

                stats_proxies[proxy]["cooldowns"] += 1

                print(
                    f"[PROXY COOLDOWN] {proxy} | "
                    f"5 errores consecutivos"
                )

                PROXY_FAILS[proxy] = 0

            stats["requests_fallidas"] += 1
            stats_diarias["requests_fallidas"] += 1
            stats_proxies[proxy]["fallidas"] += 1
            stats_proxies[proxy]["request"] += 1

        return {
            "price": None,
            "name": market_hash_name,
            "from_cache": False,
            "error": "request"
        }
        
def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
        }

        response = requests.post(
            url,
            data=data,
            timeout=15
        )

        if response.status_code == 200:

            print(
                "[INFO] Mensaje enviado a Telegram exitosamente"
            )

            return True

        else:

            print(
                f"[ERROR] Error al enviar mensaje a Telegram: "
                f"{response.status_code}"
            )

            print(
                f"[DEBUG TELEGRAM] "
                f"{response.text[:500]}"
            )

            estado_app["errores"] += 1

            return False

    except Exception as e:

        print(
            f"[ERROR] No se pudo enviar el mensaje a Telegram: "
            f"{type(e).__name__}: {e}"
        )

        estado_app["errores"] += 1

        return False

def enviar_resumen_diario():
    global stats_diarias
    global fecha_estadisticas

    ahora = datetime.now(ZONA_ARG)

    requests_total = stats_diarias["requests_steam"]
    requests_exitosas = stats_diarias["requests_exitosas"]
    requests_fallidas = stats_diarias["requests_fallidas"]
    cache_hits = stats_diarias["cache_hits"]

    porcentaje_exitos = (
        requests_exitosas / requests_total * 100
        if requests_total > 0 else 0
    )

    porcentaje_fallos = (
        requests_fallidas / requests_total * 100
        if requests_total > 0 else 0
    )

    tiempo_promedio_request = (
        stats_diarias["tiempo_consultas"] / requests_total
        if requests_total > 0 else 0
    )

    ciclos = stats_diarias["ciclos"]

    tiempo_promedio_ciclo = (
        stats_diarias["tiempo_ciclos"] / ciclos
        if ciclos > 0 else 0
    )

    proxies_cooldown = sum(
        1 for t in PROXY_STATUS.values()
        if t > time.time()
    )

    skins_cooldown = sum(
        1 for t in SKIN_COOLDOWN_UNTIL.values()
        if t > time.time()
    )

    mensaje = (
        f"📊 RESUMEN DIARIO\n\n"
        f"📅 {fecha_estadisticas.strftime('%d/%m/%Y')}\n\n"

        f"🔎 SKINS\n"
        f"• Vigiladas: {len(skins_a_vigilar)}\n"
        f"• Ciclos realizados: {ciclos}\n\n"

        f"🌐 REQUESTS STEAM\n"
        f"• Totales: {requests_total}\n"
        f"• Exitosas: {requests_exitosas} ({porcentaje_exitos:.1f}%)\n"
        f"• Fallidas: {requests_fallidas} ({porcentaje_fallos:.1f}%)\n"
        f"• Cache hits: {cache_hits}\n\n"

        f"🚨 ALERTAS\n"
        f"• Alertas enviadas: {stats_diarias['alertas_enviadas']}\n"
        f"• Alertas dobles: {stats_diarias['alertas_dobles']}\n\n"

        f"🛡️ PROXIES\n"
        f"• Total: {len(PROXIES)}\n"
        f"• En cooldown ahora: {proxies_cooldown}\n\n"

        f"📡 RENDIMIENTO POR PROXY\n\n"
    )

    for i, proxy in enumerate(PROXIES, start=1):
        datos = stats_proxies[proxy]

        total = datos["requests"]
        exitosas = datos["exitosas"]
        fallidas = datos["fallidas"]

        porcentaje = (
            exitosas / total * 100
            if total > 0 else 0
        )

        promedio = (
            datos["tiempo_total"] / total
            if total > 0 else 0
        )

        if total == 0:
            estado = "⚪ SIN DATOS"
        elif porcentaje >= 99 and promedio < 1.0:
            estado = "🟢 EXCELENTE"
        elif porcentaje >= 95 and promedio < 1.5:
            estado = "🟡 NORMAL"
        else:
            estado = "🔴 PROBLEMÁTICO"

        mensaje += (
            f"Proxy {i}\n"
            f"• Requests: {total}\n"
            f"• Exitosas: {exitosas} ({porcentaje:.1f}%)\n"
            f"• Fallidas: {fallidas}\n"
            f"• 429: {datos['429']}\n"
            f"• Timeouts: {datos['timeouts']}\n"
            f"• HTTP: {datos['http']}\n"
            f"• JSON: {datos['json']}\n"
            f"• Steam: {datos['steam']}\n"
            f"• Request: {datos['request']}\n"
            f"• Promedio: {promedio:.2f}s\n"
            f"• Cooldowns: {datos['cooldowns']}\n"
            f"• Estado: {estado}\n\n"
        )

        minutos_pausa = stats_diarias["tiempo_pausas"] / 60

    mensaje += (
        f"⚠️ SKINS PROBLEMÁTICAS\n"
        f"• En cooldown ahora: {skins_cooldown}\n\n"

        f"⏸️ PAUSAS PROGRAMADAS\n"
        f"• Cantidad: {stats_diarias['pausas_programadas']}\n"
        f"• Tiempo total: {minutos_pausa:.1f} minutos\n\n"

        f"⏱️ RENDIMIENTO GENERAL\n"
        f"• Promedio request: {tiempo_promedio_request:.2f}s\n"
        f"• Promedio ciclo: {tiempo_promedio_ciclo:.2f}s\n"
    )

    enviado = enviar_telegram(mensaje)

    if enviado:

        print("[INFO] Resumen diario enviado a Telegram")

        for key in stats_diarias:
            stats_diarias[key] = 0

        for proxy in PROXIES:
            stats_proxies[proxy] = {
                "requests": 0,
                "exitosas": 0,
                "fallidas": 0,
                "429": 0,
                "timeouts": 0,
                "http": 0,
                "json": 0,
                "steam": 0,
                "request": 0,
                "tiempo_total": 0.0,
                "cooldowns": 0,
            }

        fecha_estadisticas = ahora.date()

        guardar_estado()

    else:

        print(
            "[ERROR] El resumen diario NO fue enviado. "
            "Las estadísticas NO se reiniciarán."
        )

def dividir_skins_en_grupos():
    return [list(skins_a_vigilar.items())]

def worker(grupo_skins, worker_id):

    print(f"[DEBUG] Worker {worker_id} arrancó")

    global skins_revisadas_total
    global ciclo_numero
    global PROXIMA_PAUSA

    while estado_app["activo"]:

        # ====================================================
        # CAMBIO DE DÍA → ENVIAR RESUMEN DEL DÍA ANTERIOR
        # ====================================================

        if worker_id == 0:

            fecha_actual = datetime.now(ZONA_ARG).date()

            if fecha_actual != fecha_estadisticas:
                try:
                    enviar_resumen_diario()
                except Exception as e:
                    print(
                        f"[ERROR] Falló el resumen diario: "
                        f"{type(e).__name__}: {e}"
                    )
                    estado_app["errores"] += 1

        inicio_ciclo = time.time()

        skins_ordenadas = sorted(
            grupo_skins,
            key=lambda item: price_cache.get(
                item[0],
                {}
            ).get("next_refresh", 0)
        )

        for skin_name, precio_max in skins_ordenadas:

            # Si la skin está temporalmente bloqueada por errores,
            # no hacemos ninguna consulta a Steam.
            if skin_en_cooldown(skin_name):
                restante = SKIN_COOLDOWN_UNTIL[skin_name] - time.time()

                print(
                    f"[SKIN SKIP] {skin_name} | "
                    f"Cooldown restante: {max(0, restante):.0f}s"
                )

                with lock:
                    skins_revisadas_total += 1

                continue

            # Avisar cuando vuelve a estar disponible después del cooldown
            if SKIN_COOLDOWN_UNTIL.get(skin_name, 0) > 0:
                print(
                    f"[SKIN RETRY] {skin_name} | "
                    f"Finalizó cooldown"
                )

                SKIN_COOLDOWN_UNTIL[skin_name] = 0

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
                    stats_diarias["cache_hits"] += 1

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

                # Solo consideramos problemáticos los errores
                # que realmente pueden estar relacionados con
                # la consulta de esta skin.
                #
                # 429 queda fuera porque lo maneja el sistema de proxies.

                if error in ("timeout", "http", "request", "json", "steam", "no_price"):
                    registrar_error_skin(skin_name, error)

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

                    espera = random.uniform(8, 12)

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

            # Consulta válida: resetear errores consecutivos
            registrar_exito_skin(skin_name)

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

                ahorro = precio_max - precio_actual
                descuento = ahorro / precio_max

                # =========================
                # PRIMERA ALERTA
                # =========================

                enviar_telegram(
                    f"🛒 Skin en oferta\n"
                    f"{skin_name}\n"
                    f"{steam_url}\n"
                    f"💵 {precio_actual:.2f} USD\n"
                    f"📉 Máx {precio_max:.2f} USD\n"
                    f"💰 Ahorrás {ahorro:.2f} USD "
                    f"({descuento * 100:.1f}%)"
                )

                with lock:
                    stats["alertas_enviadas"] += 1
                    stats_diarias["alertas_enviadas"] += 1

                # =========================
                # SEGUNDA ALERTA
                # =========================

                if descuento >= ALERTA_DOBLE_DESCUENTO:
                    print(
                        f"[ALERTA DOBLE] "
                        f"{skin_name} | "
                        f"Descuento: {descuento * 100:.1f}% | "
                        f"Esperando {ALERTA_DOBLE_INTERVALO}s"
                    )

                    time.sleep(ALERTA_DOBLE_INTERVALO)

                    enviar_telegram(
                        f"🚨🚨 OFERTA MUY BUENA 🚨🚨\n"
                        f"{skin_name}\n"
                        f"{steam_url}\n"
                        f"💵 {precio_actual:.2f} USD\n"
                        f"📉 Máx {precio_max:.2f} USD\n"
                        f"💰 Ahorrás {ahorro:.2f} USD "
                        f"({descuento * 100:.1f}%)"
                    )

                    with lock:
                        stats["alertas_enviadas"] += 1
                        stats_diarias["alertas_enviadas"] += 1
                        stats_diarias["alertas_dobles"] += 1

                notificados[skin_name] = precio_actual

                guardar_estado()

            if not resultado.get("from_cache", False):
                time.sleep(random.uniform(1, 2))

        estado_app["ultimo_escaneo"] = datetime.now(ZONA_ARG).isoformat()

        if worker_id == 0:

            ciclo_numero += 1
            stats_diarias["ciclos"] += 1

            duracion = round(time.time() - inicio_ciclo, 2)
            with lock:
                stats_diarias["tiempo_ciclos"] += duracion

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

            skins_cooldown = sum(
                1
                for t in SKIN_COOLDOWN_UNTIL.values()
                if t > ahora
            )

            print(f"[INFO] Skins en cooldown: {skins_cooldown}")

            print(f"[INFO] Cache size: {len(price_cache)}")

            print(f"[INFO] Duración ciclo: {duracion} segundos")


            if skins_cooldown > 0:

                print("[INFO] Skins problemáticas:")

                for skin, cooldown_hasta in SKIN_COOLDOWN_UNTIL.items():

                    if cooldown_hasta > ahora:

                        restante = cooldown_hasta - ahora

                        print(
                            f"       - {skin} | "
                            f"Cooldown restante: {restante:.0f}s"
                        )

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

        guardar_estado()

        if time.time() >= PROXIMA_PAUSA:
            inicio_pausa = time.time()

            pausa = random.uniform(600, 1200)

            print(
                f"[PAUSA] Pausa periódica de {pausa / 60:.1f} minutos"
            )

            time.sleep(pausa)

            tiempo_pausa_real = time.time() - inicio_pausa

            stats_diarias["pausas_programadas"] += 1
            stats_diarias["tiempo_pausas"] += tiempo_pausa_real

            PROXIMA_PAUSA = time.time() + random.uniform(7200, 10800)

            guardar_estado()

        else:
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
