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
    p.strip()
    for p in os.getenv("PROXIES", "").splitlines()
    if p.strip()
]

if not PROXIES:
    raise RuntimeError("No hay PROXIES configurados en Render.")

print(f"[PROXY] {len(PROXIES)} proxies cargados correctamente.")

def nombre_proxy(proxy):
    try:
        numero = PROXIES.index(proxy) + 1
        return f"Proxy {numero}"
    except ValueError:
        return "Proxy desconocido"

PROXY_COOLDOWN = 600  # 10 min

PROXY_429_COOLDOWN_BASE = 90
PROXY_429_COOLDOWN_MAX = 600

PROXY_MIN_INTERVAL = 10

# Tiempo mínimo entre requests reales a Steam
GLOBAL_MIN_REQUEST_INTERVAL = 3.0
LAST_STEAM_REQUEST = 0

# =========================================================
# AUTO-TUNER
# =========================================================

AUTO_TUNER_ACTIVO = True

# Cada cuánto analiza el comportamiento
AUTO_TUNER_INTERVALO = 1800  # 30 minutos

AUTO_TUNER_ULTIMA_REVISION = time.time()

# Valores permitidos
AUTO_GLOBAL_MIN = 3.0
AUTO_GLOBAL_MAX = 8.0

AUTO_PROXY_MIN = 10
AUTO_PROXY_MAX = 25

AUTO_429_BASE_MIN = 60
AUTO_429_BASE_MAX = 300

# Estadísticas de la última medición
AUTO_ULTIMOS_REQUESTS = 0
AUTO_ULTIMOS_429 = 0
AUTO_ULTIMOS_TIMEOUTS = 0

# =========================================================
# PROTECCIÓN GLOBAL CONTRA RATE LIMIT DE STEAM (HTTP 429)
# =========================================================

STEAM_429_CONSECUTIVOS = 0
STEAM_429_PAUSA_HASTA = 0

# Pausa global cuando Steam empieza a rechazar requests
STEAM_429_PAUSA_BASE = 300       # 5 minutos
STEAM_429_PAUSA_MAX = 900        # máximo 15 minutos
STEAM_429_UMBRAL = 2


def steam_rate_limit_activo():

    with lock:
        return time.time() < STEAM_429_PAUSA_HASTA


def steam_pausa_restante():

    with lock:
        return max(
            0,
            STEAM_429_PAUSA_HASTA - time.time()
        )


def registrar_429_global():

    global STEAM_429_CONSECUTIVOS
    global STEAM_429_PAUSA_HASTA

    with lock:

        STEAM_429_CONSECUTIVOS += 1

        consecutivos = STEAM_429_CONSECUTIVOS

        if consecutivos >= STEAM_429_UMBRAL:

            nivel = consecutivos - STEAM_429_UMBRAL

            pausa = min(
                STEAM_429_PAUSA_BASE * (2 ** nivel),
                STEAM_429_PAUSA_MAX
            )

            pausa += random.uniform(15, 45)

            nueva_pausa = time.time() + pausa

            # Nunca acortamos una pausa ya existente
            if nueva_pausa > STEAM_429_PAUSA_HASTA:
                STEAM_429_PAUSA_HASTA = nueva_pausa

        else:
            pausa = 0

    if consecutivos >= STEAM_429_UMBRAL:

        print(
            f"[STEAM 429 GLOBAL] "
            f"{consecutivos} 429 consecutivos | "
            f"Pausa global: {pausa:.0f}s"
        )

    else:

        print(
            f"[STEAM 429 GLOBAL] "
            f"429 consecutivo #{consecutivos}"
        )


def registrar_exito_steam_global():

    global STEAM_429_CONSECUTIVOS

    with lock:

        if STEAM_429_CONSECUTIVOS > 0:

            print(
                "[STEAM OK] Steam volvió a responder correctamente. "
                "Reiniciando contador global de 429."
            )

        STEAM_429_CONSECUTIVOS = 0

# =========================================================
# AUTO-TUNER
# =========================================================

def ejecutar_auto_tuner():

    global AUTO_TUNER_ULTIMA_REVISION
    global AUTO_ULTIMOS_REQUESTS
    global AUTO_ULTIMOS_429
    global AUTO_ULTIMOS_TIMEOUTS

    global GLOBAL_MIN_REQUEST_INTERVAL
    global PROXY_MIN_INTERVAL
    global PROXY_429_COOLDOWN_BASE

    if not AUTO_TUNER_ACTIVO:
        return

    ahora = time.time()

    # Todavía no corresponde analizar
    if ahora - AUTO_TUNER_ULTIMA_REVISION < AUTO_TUNER_INTERVALO:
        return

    AUTO_TUNER_ULTIMA_REVISION = ahora

    with lock:

        requests_actuales = stats_diarias["requests_steam"]

        total_429 = sum(
            datos["429"]
            for datos in stats_proxies.values()
        )

        total_timeouts = sum(
            datos["timeouts"]
            for datos in stats_proxies.values()
        )

    requests_periodo = (
        requests_actuales - AUTO_ULTIMOS_REQUESTS
    )

    nuevos_429 = (
        total_429 - AUTO_ULTIMOS_429
    )

    nuevos_timeouts = (
        total_timeouts - AUTO_ULTIMOS_TIMEOUTS
    )

    AUTO_ULTIMOS_REQUESTS = requests_actuales
    AUTO_ULTIMOS_429 = total_429
    AUTO_ULTIMOS_TIMEOUTS = total_timeouts

    if requests_periodo <= 0:
        print("[AUTO-TUNER] Sin suficientes requests para analizar.")
        return

    porcentaje_429 = (
        nuevos_429 / requests_periodo * 100
    )

    porcentaje_timeout = (
        nuevos_timeouts / requests_periodo * 100
    )

    print("")
    print("============== AUTO-TUNER ==============")

    print(
        f"[AUTO-TUNER] Requests últimos 30 min: "
        f"{requests_periodo}"
    )

    print(
        f"[AUTO-TUNER] Nuevos 429: "
        f"{nuevos_429} ({porcentaje_429:.2f}%)"
    )

    print(
        f"[AUTO-TUNER] Nuevos timeouts: "
        f"{nuevos_timeouts} ({porcentaje_timeout:.2f}%)"
    )

    print(
        f"[AUTO-TUNER] Intervalo global actual: "
        f"{GLOBAL_MIN_REQUEST_INTERVAL:.1f}s"
    )

    print(
        f"[AUTO-TUNER] Intervalo proxy actual: "
        f"{PROXY_MIN_INTERVAL}s"
    )

    # =====================================================
    # DEMASIADOS 429
    # =====================================================

    if porcentaje_429 >= 3:

        viejo = GLOBAL_MIN_REQUEST_INTERVAL

        GLOBAL_MIN_REQUEST_INTERVAL = min(
            GLOBAL_MIN_REQUEST_INTERVAL + 0.5,
            AUTO_GLOBAL_MAX
        )

        viejo_proxy = PROXY_MIN_INTERVAL

        PROXY_MIN_INTERVAL = min(
            PROXY_MIN_INTERVAL + 2,
            AUTO_PROXY_MAX
        )

        viejo_cooldown = PROXY_429_COOLDOWN_BASE

        PROXY_429_COOLDOWN_BASE = min(
            PROXY_429_COOLDOWN_BASE + 30,
            AUTO_429_BASE_MAX
        )

        print(
            f"[AUTO-TUNER] ⚠️ Muchos 429"
        )

        print(
            f"[AUTO-TUNER] Global: "
            f"{viejo:.1f}s → "
            f"{GLOBAL_MIN_REQUEST_INTERVAL:.1f}s"
        )

        print(
            f"[AUTO-TUNER] Proxy: "
            f"{viejo_proxy}s → "
            f"{PROXY_MIN_INTERVAL}s"
        )

        print(
            f"[AUTO-TUNER] Cooldown 429: "
            f"{viejo_cooldown}s → "
            f"{PROXY_429_COOLDOWN_BASE}s"
        )

    # =====================================================
    # ALGUNOS 429
    # =====================================================

    elif porcentaje_429 >= 1:

        viejo = GLOBAL_MIN_REQUEST_INTERVAL

        GLOBAL_MIN_REQUEST_INTERVAL = min(
            GLOBAL_MIN_REQUEST_INTERVAL + 0.25,
            AUTO_GLOBAL_MAX
        )

        print(
            f"[AUTO-TUNER] 🟡 429 moderados | "
            f"Global: {viejo:.1f}s → "
            f"{GLOBAL_MIN_REQUEST_INTERVAL:.1f}s"
        )

    # =====================================================
    # TODO BIEN
    # =====================================================

    elif nuevos_429 == 0 and nuevos_timeouts == 0:

        viejo = GLOBAL_MIN_REQUEST_INTERVAL

        GLOBAL_MIN_REQUEST_INTERVAL = max(
            GLOBAL_MIN_REQUEST_INTERVAL - 0.25,
            AUTO_GLOBAL_MIN
        )

        viejo_proxy = PROXY_MIN_INTERVAL

        PROXY_MIN_INTERVAL = max(
            PROXY_MIN_INTERVAL - 1,
            AUTO_PROXY_MIN
        )

        viejo_cooldown = PROXY_429_COOLDOWN_BASE

        PROXY_429_COOLDOWN_BASE = max(
            PROXY_429_COOLDOWN_BASE - 15,
            AUTO_429_BASE_MIN
        )

        print(
            f"[AUTO-TUNER] 🟢 Todo estable"
        )

        print(
            f"[AUTO-TUNER] Global: "
            f"{viejo:.1f}s → "
            f"{GLOBAL_MIN_REQUEST_INTERVAL:.1f}s"
        )

        print(
            f"[AUTO-TUNER] Proxy: "
            f"{viejo_proxy}s → "
            f"{PROXY_MIN_INTERVAL}s"
        )

        print(
            f"[AUTO-TUNER] Cooldown 429: "
            f"{viejo_cooldown}s → "
            f"{PROXY_429_COOLDOWN_BASE}s"
        )

    # =====================================================
    # TIMEOUTS
    # =====================================================

    if porcentaje_timeout >= 3:

        viejo = PROXY_MIN_INTERVAL

        PROXY_MIN_INTERVAL = min(
            PROXY_MIN_INTERVAL + 2,
            AUTO_PROXY_MAX
        )

        print(
            f"[AUTO-TUNER] ⚠️ Muchos timeouts | "
            f"Proxy: {viejo}s → "
            f"{PROXY_MIN_INTERVAL}s"
        )

    print("==========================================")
    print("")

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
    "★ StatTrak™ Falchion Knife | Autotronic (Minimal Wear)": 150.00,
    "★ StatTrak™ Falchion Knife | Crimson Web (Field-Tested)": 175.00,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 133.00,
    "★ StatTrak™ Paracord Knife | Blue Steel (Minimal Wear)": 115.00,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 158.00,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 138.00,
    "★ StatTrak™ Falchion Knife | Black Laminate (Factory New)": 154.00,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 140.00,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 190.00,
    "★ Paracord Knife | Blue Steel (Factory New)": 163.00,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 150.00,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 161.00,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 160.00,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 425.00,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 219.00,
    "★ StatTrak™ Nomad Knife | Crimson Web (Well-Worn)": 185.00,
    "★ Falchion Knife | Tiger Tooth (Minimal Wear)": 184.00,
    "StatTrak™ Desert Eagle | Ocean Drive (Minimal Wear)": 150.00,
    "StatTrak™ SSG 08 | Dragonfire (Factory New)": 211.00,
    "M4A1-S | Master Piece (Minimal Wear)": 205.00,
    "StatTrak™ M4A1-S | Chantico's Fire (Minimal Wear)": 170.00,
    "StatTrak™ M4A1-S | Hyper Beast (Minimal Wear)": 191.00,
    "★ Bowie Knife | Tiger Tooth (Minimal Wear)": 173.00,
    "★ Bowie Knife | Crimson Web (Minimal Wear)": 190.00,
    "★ Survival Knife | Blue Steel (Factory New)": 140.00,
    "★ StatTrak™ Classic Knife | Blue Steel (Field-Tested)": 140.00,
    "★ StatTrak™ Falchion Knife | Freehand (Factory New)": 118.00,
    "★ Falchion Knife | Blue Steel (Minimal Wear)": 155.00,
    "★ Falchion Knife | Autotronic (Factory New)": 179.00,
    "★ StatTrak™ Bowie Knife | Damascus Steel (Minimal Wear)": 119.00,
    "★ StatTrak™ Bowie Knife | Marble Fade (Factory New)": 207.00,
    "★ StatTrak™ Shadow Daggers | Freehand (Minimal Wear)": 70.00,
    "★ StatTrak™ Shadow Daggers | Fade (Factory New)": 200.00,
    "★ Shadow Daggers | Fade (Minimal Wear)": 205.00,
    "★ Nomad Knife | Stained (Minimal Wear)": 152.00,
    "★ StatTrak™ Nomad Knife | Ultraviolet (Minimal Wear)": 166.00,
    "★ Nomad Knife | Crimson Web (Minimal Wear)": 226.00,
    "★ Skeleton Knife | Stained (Minimal Wear)": 241.00,
    "★ Flip Knife | Lore (Field-Tested)": 175.00,
    "★ StatTrak™ Flip Knife | Blue Steel (Minimal Wear)": 215.00,
    
}

ITEM_NAME_IDS = {
    "★ StatTrak™ Falchion Knife | Autotronic (Minimal Wear)": 176263237,
    "★ StatTrak™ Falchion Knife | Crimson Web (Field-Tested)": 49612097,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 176263307,
    "★ StatTrak™ Paracord Knife | Blue Steel (Minimal Wear)": 176097689,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 176263373,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 139673208,
    "★ StatTrak™ Falchion Knife | Black Laminate (Factory New)": 176283223,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth (Minimal Wear)": 175885515,
    "★ StatTrak™ Nomad Knife | Blue Steel (Field-Tested)": 176097644,
    "★ Paracord Knife | Blue Steel (Factory New)": 176099222,
    "★ StatTrak™ Ursus Knife | Ultraviolet (Minimal Wear)": 176045737,
    "★ StatTrak™ Paracord Knife | Tiger Tooth (Minimal Wear)": 176519236,
    "★ StatTrak™ Bowie Knife | Tiger Tooth (Factory New)": 175891607,
    "★ M9 Bayonet | Ultraviolet (Field-Tested)": 29389708,
    "★ StatTrak™ Stiletto Knife | Damascus Steel (Field-Tested)": 176047257,
    "★ StatTrak™ Nomad Knife | Crimson Web (Well-Worn)": 176097950,
    "★ Falchion Knife | Tiger Tooth (Minimal Wear)": 175881471,
    "StatTrak™ Desert Eagle | Ocean Drive (Minimal Wear)": 176263203,
    "StatTrak™ SSG 08 | Dragonfire (Factory New)": 175854470,
    "M4A1-S | Master Piece (Minimal Wear)": 14953196,
    "StatTrak™ M4A1-S | Chantico's Fire (Minimal Wear)": 149922266,
    "StatTrak™ M4A1-S | Hyper Beast (Minimal Wear)": 40194354,
    "★ Bowie Knife | Tiger Tooth (Minimal Wear)": 175881329,
    "★ Bowie Knife | Crimson Web (Minimal Wear)": 139966115,
    "★ Survival Knife | Blue Steel (Factory New)": 176103425,
    "★ StatTrak™ Classic Knife | Blue Steel (Field-Tested)": 176091948,
    "★ StatTrak™ Falchion Knife | Freehand (Factory New)": 176263345,
    "★ Falchion Knife | Blue Steel (Minimal Wear)": 49461582,
    "★ Falchion Knife | Autotronic (Factory New)": 176263260,
    "★ StatTrak™ Bowie Knife | Damascus Steel (Minimal Wear)": 175880602,
    "★ StatTrak™ Bowie Knife | Marble Fade (Factory New)": 175884373,
    "★ StatTrak™ Shadow Daggers | Freehand (Minimal Wear)": 176263963,
    "★ StatTrak™ Shadow Daggers | Fade (Factory New)": 67210734,
    "★ Shadow Daggers | Fade (Minimal Wear)": 67590792,
    "★ Nomad Knife | Stained (Minimal Wear)": 176097478,
    "★ StatTrak™ Nomad Knife | Ultraviolet (Minimal Wear)": 176508659,
    "★ Nomad Knife | Crimson Web (Minimal Wear)": 176097767,
    "★ Skeleton Knife | Stained (Minimal Wear)": 176097674,
    "★ Flip Knife | Lore (Field-Tested)": 156219676,
    "★ StatTrak™ Flip Knife | Blue Steel (Minimal Wear)": 9672792,
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
        return random.uniform(150, 190)

    distancia = (precio - precio_max) / precio_max

    # Precio igual o por debajo del máximo
    if distancia <= 0:
        return random.uniform(55, 85)

    # Hasta 5% por encima
    elif distancia <= 0.05:
        return random.uniform(85, 120)

    # Entre 5% y 10%
    elif distancia <= 0.10:
        return random.uniform(95, 120)

    # Entre 10% y 15%
    elif distancia <= 0.15:
        return random.uniform(110, 145)

    # Entre 15% y 25%
    elif distancia <= 0.25:
        return random.uniform(135, 170)

    # Muy lejos del objetivo
    else:
        return random.uniform(160, 190)

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
            "notificados": notificados,
            "stats_diarias": stats_diarias,
            "stats_proxies": stats_proxies,
            "price_cache": price_cache,
            "ciclo_numero": ciclo_numero,
            "estado_app": estado_app,
            "skins_revisadas_total": skins_revisadas_total,
            "fecha_estadisticas": fecha_estadisticas.isoformat()
        }

        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)

        github_token = os.getenv("GITHUB_TOKEN")
        github_repo = os.getenv("GITHUB_REPO")

        if not github_token or not github_repo:
            print("[GITHUB] Faltan GITHUB_TOKEN o GITHUB_REPO")
            return

        url = f"https://api.github.com/repos/{github_repo}/contents/bot_state.json"

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        # Obtener SHA del archivo actual, si existe
        respuesta_actual = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        sha = None

        if respuesta_actual.status_code == 200:
            sha = respuesta_actual.json().get("sha")
        elif respuesta_actual.status_code != 404:
            print(
                f"[GITHUB] Error consultando estado: "
                f"HTTP {respuesta_actual.status_code}"
            )
            return

        with open(ARCHIVO_ESTADO, "rb") as f:
            contenido = f.read()

        import base64

        contenido_base64 = base64.b64encode(contenido).decode("utf-8")

        datos_github = {
            "message": "Actualizar bot_state.json",
            "content": contenido_base64
        }

        if sha:
            datos_github["sha"] = sha

        respuesta = requests.put(
            url,
            headers=headers,
            json=datos_github,
            timeout=20
        )

        if respuesta.status_code in (200, 201):
            print("[GITHUB] Estado guardado correctamente.")
        else:
            print(
                f"[GITHUB] Error guardando estado: "
                f"HTTP {respuesta.status_code}"
            )

    except Exception as e:
        print(f"[GITHUB] Error en guardar_estado(): {e}")


def cargar_estado():
    global notificados
    global stats_diarias
    global stats_proxies
    global price_cache
    global ciclo_numero
    global estado_app
    global skins_revisadas_total

    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_repo = os.getenv("GITHUB_REPO")

        if not github_token or not github_repo:
            print("[GITHUB] Faltan GITHUB_TOKEN o GITHUB_REPO")
            print("[INFO] Se inicia desde cero.")
            return

        url = f"https://api.github.com/repos/{github_repo}/contents/bot_state.json"

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        respuesta = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if respuesta.status_code == 404:
            print("[GITHUB] No existe bot_state.json todavía.")
            print("[INFO] Se inicia desde cero.")
            return

        if respuesta.status_code != 200:
            print(
                f"[GITHUB] Error descargando estado: "
                f"HTTP {respuesta.status_code}"
            )
            print("[INFO] Se inicia desde cero.")
            return

        datos_github = respuesta.json()

        import base64

        contenido = base64.b64decode(
            datos_github["content"]
        ).decode("utf-8")

        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            f.write(contenido)

        with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
            estado = json.load(f)

        notificados = estado.get("notificados", {})
        stats_diarias = estado.get("stats_diarias", stats_diarias)
        stats_proxies_guardadas = estado.get("stats_proxies", {})

        stats_proxies = {}

        for proxy in PROXIES:

            datos = stats_proxies_guardadas.get(proxy, {})

            stats_proxies[proxy] = {
                "requests": datos.get("requests", 0),
                "exitosas": datos.get("exitosas", 0),
                "fallidas": datos.get("fallidas", 0),
                "429": datos.get("429", 0),
                "timeouts": datos.get("timeouts", 0),
                "http": datos.get("http", 0),
                "json": datos.get("json", 0),
                "steam": datos.get("steam", 0),
                "request": datos.get("request", 0),
                "tiempo_total": datos.get("tiempo_total", 0.0),
                "cooldowns": datos.get("cooldowns", 0),
            }

        price_cache = estado.get("price_cache", {})
        
        ciclo_numero = estado.get("ciclo_numero", 0)
        estado_app = estado.get("estado_app")

        if not isinstance(estado_app, dict):
            estado_app = {
                "activo": True,
                "errores": 0,
                "ultimo_escaneo": None
            }
        skins_revisadas_total = estado.get(
            "skins_revisadas_total",
            0
        )

        print("[GITHUB] Estado descargado correctamente.")
        print(
            f"[GITHUB] Cache recuperada: "
            f"{len(price_cache)} skins"
        )

    except Exception as e:
        print(f"[GITHUB] Error en cargar_estado(): {e}")
        print("[INFO] Se inicia desde cero.")

def limpiar_cache():

    # Si Steam está aplicando rate limit,
    # NO eliminamos datos anteriores.
    if steam_rate_limit_activo():

        print(
            "[CACHE CLEAN] Steam está en rate limit. "
            "Se conserva todo el cache."
        )

        return

    ahora = time.time()

    # Conservamos cache viejo durante 30 minutos.
    CACHE_LIMPIEZA_SEGUNDOS = 1800

    with lock:

        keys_a_borrar = []

        for k, v in price_cache.items():

            timestamp = v.get("timestamp", ahora)

            if ahora - timestamp > CACHE_LIMPIEZA_SEGUNDOS:

                keys_a_borrar.append(k)

        for k in keys_a_borrar:

            del price_cache[k]

    if keys_a_borrar:

        print(
            f"[CACHE CLEAN] "
            f"Eliminadas {len(keys_a_borrar)} entradas antiguas"
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

PROXY_STATUS = {proxy: 0 for proxy in PROXIES}
PROXY_LAST_USED = {proxy: 0 for proxy in PROXIES}
PROXY_FAILS = {proxy: 0 for proxy in PROXIES}
PROXY_429_FAILS = {proxy: 0 for proxy in PROXIES}

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
                f"[PROXY] {nombre_proxy(proxy_elegido)} | "
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

    ahora = time.time()

    proxies_cooldown = sum(
        1
        for t in PROXY_STATUS.values()
        if t > ahora
    )

    skins_cooldown = sum(
        1
        for t in SKIN_COOLDOWN_UNTIL.values()
        if t > ahora
    )

    return jsonify({

        "activo": estado_app["activo"],

        "ultimo_escaneo":
            estado_app["ultimo_escaneo"],

        "errores_totales":
            estado_app["errores"],

        "items_vigilados":
            len(skins_a_vigilar),

        "notificaciones_enviadas":
            len(notificados),

        "proxies_totales":
            len(PROXIES),

        "proxies_cooldown":
            proxies_cooldown,

        "skins_cooldown":
            skins_cooldown,

        "steam_rate_limit":
            steam_rate_limit_activo(),

        "steam_429_consecutivos":
            STEAM_429_CONSECUTIVOS,

        "steam_pausa_restante_segundos":
            round(steam_pausa_restante(), 1),

        "cache":
            len(price_cache),

        "timestamp":
            datetime.now(ZONA_ARG).isoformat()
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

        # Verificar primero si Steam está pausado
        if steam_rate_limit_activo():

            restante = steam_pausa_restante()

            print(
                f"[STEAM PAUSA] "
                f"Se cancela request antes de enviarlo | "
                f"Restante: {restante:.0f}s"
            )

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "steam_global_pause"
            }

        inicio_request = time.time()

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

        # Volver a comprobar por si Steam entró en pausa
        # mientras estábamos esperando

        if steam_rate_limit_activo():

            restante = steam_pausa_restante()

            print(
                f"[STEAM PAUSA] "
                f"Se cancela request antes de enviarlo | "
                f"Restante: {restante:.0f}s"
            )

            return {
                "price": None,
                "name": market_hash_name,
                "from_cache": False,
                "error": "steam_global_pause"
            }

        with lock:
            LAST_STEAM_REQUEST = time.time()

            stats["requests_steam"] += 1
            stats_diarias["requests_steam"] += 1
            stats_proxies[proxy]["requests"] += 1


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

            registrar_429_global()
            restante_global = steam_pausa_restante()

            if restante_global > 0:

                print(
                    f"[429] "
                    f"Steam activó protección global | "
                    f"Pausa restante: "
                    f"{restante_global:.0f}s"
                )
            print(
                    f"[429] {market_hash_name} | "
                    f"Proxy: {nombre_proxy(proxy)} | "
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
                f"{nombre_proxy(proxy)} -> {r.status_code}"
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

        registrar_exito_steam_global()

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
        jitter_cache = random.uniform(0, 25)

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
            f"Proxy: {nombre_proxy(proxy)}"
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
                   f"[PROXY COOLDOWN] {nombre_proxy(proxy)} | "
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
                    f"[PROXY COOLDOWN] {nombre_proxy(proxy)} | "
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

def enviar_resumen_diario(reiniciar=True):
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

        elif porcentaje >= 99 and datos["429"] == 0 and fallidas == 0:

            estado = "🟢 EXCELENTE"

        elif porcentaje >= 95:

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

        if reiniciar:

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

# ============================================================
# COMANDOS DE TELEGRAM
# ============================================================

def comando_estado():
    ahora = datetime.now(ZONA_ARG)

    estado = "ACTIVO" if estado_app.get("activo", False) else "DETENIDO"

    ultimo_escaneo = estado_app.get("ultimo_escaneo")

    if ultimo_escaneo:
        ultimo_escaneo_texto = str(ultimo_escaneo)
    else:
        ultimo_escaneo_texto = "Sin datos"

    proxies_en_cooldown = sum(
        1
        for proxy in PROXIES
        if PROXY_STATUS.get(proxy, 0) > time.time()
    )

    mensaje = (
        "🤖 ESTADO DEL BOT\n\n"
        f"Estado: {estado}\n"
        f"Hora: {ahora.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Skins vigiladas: {len(skins_a_vigilar)}\n"
        f"Skins en caché: {len(price_cache)}\n"
        f"Ciclo actual: {ciclo_numero}\n"
        f"Último escaneo: {ultimo_escaneo_texto}\n"
        f"Proxies configurados: {len(PROXIES)}\n"
        f"Proxies en cooldown: {proxies_en_cooldown}\n"
        f"Fallos consecutivos de Steam: {STEAM_429_CONSECUTIVOS}\n"
        f"Pausa global de Steam: "
        f"{int(steam_pausa_restante())} segundos"
    )

    enviar_telegram(mensaje)


def comando_resumen():
    enviar_resumen_diario(reiniciar=False)


def comando_proxies():
    ahora = time.time()

    mensaje = "🌐 ESTADO DE LOS PROXIES\n\n"

    for i, proxy in enumerate(PROXIES, start=1):

        datos = stats_proxies.get(proxy, {})

        requests_total = datos.get("requests", 0)
        exitosas = datos.get("exitosas", 0)
        fallidas = datos.get("fallidas", 0)
        errores_429 = datos.get("429", 0)
        timeouts = datos.get("timeouts", 0)

        cooldown_hasta = PROXY_STATUS.get(proxy, 0)

        if cooldown_hasta > ahora:
            estado = (
                f"🔴 COOLdown "
                f"{int(cooldown_hasta - ahora)}s"
            )
        else:
            estado = "🟢 DISPONIBLE"

        mensaje += (
            f"Proxy {i}\n"
            f"Estado: {estado}\n"
            f"Requests: {requests_total}\n"
            f"Exitosas: {exitosas}\n"
            f"Fallidas: {fallidas}\n"
            f"429: {errores_429}\n"
            f"Timeouts: {timeouts}\n\n"
        )

    enviar_telegram(mensaje)

def comando_top():
    try:
        ranking = []

        for skin, precio_maximo in skins_a_vigilar.items():

            datos = price_cache.get(skin)

            # Si todavía no tenemos precio para esta skin, la salteamos
            if not datos:
                continue

            precio_actual = datos.get("price")

            if precio_actual is None:
                continue

            try:
                precio_actual = float(precio_actual)
                precio_maximo = float(precio_maximo)
            except (ValueError, TypeError):
                continue

            # Diferencia porcentual respecto al objetivo
            diferencia_porcentaje = (
                (precio_actual - precio_maximo)
                / precio_maximo
            ) * 100

            # Solo mostrar skins que estén como máximo 10% por encima
            if diferencia_porcentaje <= 10:
                ranking.append({
                    "skin": skin,
                    "precio": precio_actual,
                    "maximo": precio_maximo,
                    "diferencia": diferencia_porcentaje
                })

        # Ordenar: primero las que están más cerca o ya debajo del objetivo
        ranking.sort(key=lambda x: x["diferencia"])

        # Mostrar solamente las 10 mejores
        ranking = ranking[:10]

        if not ranking:
            enviar_telegram(
                "🏆 TOP\n\n"
                "No hay skins dentro del 10% de su objetivo "
                "con precio disponible en caché."
            )
            return

        mensaje = "🏆 TOP 10 — MÁS CERCA DEL OBJETIVO\n\n"

        for i, item in enumerate(ranking, start=1):

            skin = item["skin"]
            precio = item["precio"]
            maximo = item["maximo"]
            diferencia = item["diferencia"]

            if diferencia <= 0:
                estado = f"🔥 {abs(diferencia):.1f}% DEBAJO"
            else:
                estado = f"📊 {diferencia:.1f}% arriba"

            mensaje += (
                f"{i}. {skin}\n"
                f"   💰 ${precio:.2f} / 🎯 ${maximo:.2f}\n"
                f"   {estado}\n\n"
            )

        mensaje += (
            "ℹ️ Se muestran las 10 skins más cercanas "
            "al objetivo dentro del 10%.\n"
            "📦 Datos tomados del caché actual del bot."
        )

        enviar_telegram(mensaje)

    except Exception as e:
        print(f"[TELEGRAM] Error en comando_top: {e}")

        enviar_telegram(
            "❌ Error al generar el TOP."
        )


def comando_ayuda():
    mensaje = (
        "📋 COMANDOS DISPONIBLES\n\n"
        "/estado - Estado general del bot\n"
        "/resumen - Resumen acumulado del día\n"
        "/proxies - Estado detallado de los proxies\n"
        "/top - Top 10 skins más cerca del objetivo\n"
        "/ayuda - Mostrar esta ayuda"
    )

    enviar_telegram(mensaje)

def telegram_listener():

    print("[TELEGRAM] Receptor de comandos iniciado.")

    offset = 0

    while True:

        try:

            url = (
                f"https://api.telegram.org/bot"
                f"{TELEGRAM_BOT_TOKEN}/getUpdates"
            )

            params = {
                "timeout": 25,
                "offset": offset
            }

            respuesta = requests.get(
                url,
                params=params,
                timeout=35
            )

            datos = respuesta.json()

            if not datos.get("ok"):
                time.sleep(5)
                continue

            for update in datos.get("result", []):

                offset = update["update_id"] + 1

                mensaje = update.get("message")

                if not mensaje:
                    continue

                chat_id = mensaje["chat"]["id"]

                # Solo aceptar comandos desde nuestro chat
                if str(chat_id) != str(TELEGRAM_CHAT_ID):
                    continue

                texto = mensaje.get("text", "").strip()

                if not texto:
                    continue

                comando = texto.split()[0].lower()

                # Permite /estado y también /estado@nombre_del_bot
                comando = comando.split("@")[0]

                print(f"[TELEGRAM] Comando recibido: {comando}")

                if comando == "/estado":
                    comando_estado()

                elif comando == "/resumen":
                    comando_resumen()

                elif comando == "/proxies":
                    comando_proxies()

                elif comando == "/top":
                    comando_top()

                elif comando == "/ayuda":
                    comando_ayuda()

        except Exception as e:

            print(f"[TELEGRAM] Error en receptor: {e}")

            time.sleep(5)

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
            
            # ====================================================
            # PAUSA GLOBAL POR RATE LIMIT DE STEAM
            # ====================================================

            if steam_rate_limit_activo():

                restante = steam_pausa_restante()

                print(
                    f"[STEAM PAUSA] "
                    f"Rate limit activo | "
                    f"Restante: {restante:.0f}s"
                )

                time.sleep(max(1, restante))
                continue

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

                if error in (
                    "timeout",
                    "http",
                    "request",
                    "json",
                    "steam",
                    "no_price"
                ):
                    registrar_error_skin(
                        skin_name,
                        error
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

                    print(
                        f"[RETRY] {skin_name} | "
                        f"429 detectado → se cancela el retry "
                        f"y se respeta la pausa global de Steam"
                    )

                    break

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

                alerta_enviada = enviar_telegram(
                    f"🛒 Skin en oferta\n"
                    f"{skin_name}\n"
                    f"{steam_url}\n"
                    f"💵 {precio_actual:.2f} USD\n"
                    f"📉 Máx {precio_max:.2f} USD\n"
                    f"💰 Ahorrás {ahorro:.2f} USD "
                    f"({descuento * 100:.1f}%)"
                )

                if alerta_enviada:

                    with lock:
                        stats["alertas_enviadas"] += 1
                        stats_diarias["alertas_enviadas"] += 1

                else:

                    print(
                        f"[ALERTA ERROR] "
                        f"No se pudo enviar Telegram | {skin_name}"
                    )

                    continue

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

                    segunda_alerta_enviada = enviar_telegram(
                        f"🚨🚨 OFERTA MUY BUENA 🚨🚨\n"
                        f"{skin_name}\n"
                        f"{steam_url}\n"
                        f"💵 {precio_actual:.2f} USD\n"
                        f"📉 Máx {precio_max:.2f} USD\n"
                        f"💰 Ahorrás {ahorro:.2f} USD "
                        f"({descuento * 100:.1f}%)"
                    )

                    if segunda_alerta_enviada:

                        with lock:
                            stats["alertas_enviadas"] += 1
                            stats_diarias["alertas_enviadas"] += 1
                            stats_diarias["alertas_dobles"] += 1

                    else:

                        print(
                            f"[ALERTA DOBLE ERROR] "
                            f"No se pudo enviar Telegram | {skin_name}"
                        )

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
            
            print(
                f"[INFO] Steam 429 consecutivos: "
                f"{STEAM_429_CONSECUTIVOS}"
            )

            if steam_rate_limit_activo():

                print(
                    f"[INFO] Steam pausa global restante: "
                    f"{steam_pausa_restante():.0f}s"
                )

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

            ejecutar_auto_tuner()

            print("================================================\n")

            skins_revisadas_total = 0

            with lock:
                stats["requests_steam"] = 0
                stats["requests_exitosas"] = 0
                stats["requests_fallidas"] = 0
                stats["cache_hits"] = 0
                stats["alertas_enviadas"] = 0
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

    # =====================================================
    # RECUPERAR ESTADO DESDE GITHUB
    # =====================================================

    print("==============================================")
    print("[STARTUP] Recuperando estado guardado...")
    print("==============================================")

    cargar_estado()

    print("==============================================")
    print("[STARTUP] Estado recuperado.")
    print(f"[STARTUP] Cache: {len(price_cache)} skins")
    print(f"[STARTUP] Notificados: {len(notificados)}")
    print(f"[STARTUP] Ciclo anterior: {ciclo_numero}")
    print("==============================================")

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

    telegram_thread = threading.Thread(
        target=telegram_listener,
        daemon=True
    )
    telegram_thread.start()

    for t in threads:
        t.join()
    servidor_thread.join()
