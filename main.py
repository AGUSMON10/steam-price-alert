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
PROXY_FAILS = {p: 0 for p in PROXIES}
PROXY_BANNED = {p: False for p in PROXIES}
PROXY_LAST_CHECK = {p: 0 for p in PROXIES}
PROXY_LATENCY = {p: 0 for p in PROXIES}

PROXY_CHECK_INTERVAL = 14400  # 4 horas

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
    "Knife falchion ★ StatTrak™ | Autotronic minimal": 182.00,
    "StatTrak™ Huntsman Knife | Damascus Steel Factory": 215.00,
    "★ StatTrak™ Falchion Knife | Stained (Minimal Wear)": 150.00,
    "★ Falchion Knife | Crimson Web (Field Tested)": 150.00,
    "StatTrak™ Falchion Knife | Crimson Web Field": 211.00,
    "★ StatTrak™ Bowie Knife | Autotronic (Minimal Wear)": 170.00,
    "stattrak Paracord Knife | Blue Steel Minimal": 150.00,
    "★ StatTrak™ Falchion Knife | Lore (Minimal Wear)": 199.00,
    "★ Classic Knife | Blue Steel (Minimal Wear)": 174.00,
    "★ Bowie Knife | Blue Steel (Minimal Wear)": 165.00,
    "StatTrak™ Falchion Knife | Black Laminate Factory": 200.00,
    "★ Kukri Knife | Night Stripe (Factory New)": 154.00,
    "★ StatTrak™ Skeleton Knife | Scorched (Field Tested)": 194.00,
    "★ Falchion Knife | Ultraviolet (Minimal Wear)": 150.00,
    "★ Specialist Gloves | Crimson Web (Battle-Scarred)": 150.00,
    "★ StatTrak™ Nomad Knife | Ultraviolet Field": 165.00,
    "★ StatTrak™ Bowie Knife | Ultraviolet Field": 112.00,
    "★ StatTrak™ Bowie Knife | Lore Well": 134.00,
    "★ StatTrak™ Bowie Knife | Autotronic Well": 134.00,
    "★ StatTrak™ Bowie Knife | Damascus Steel minimal": 147.00,
    "★ StatTrak™ Bowie Knife | Lore minimal": 175.00,
    "★ StatTrak™ Paracord Knife | Damascus Steel factory": 133.00,
    "★ StatTrak™ Paracord Knife | Ultraviolet minimal": 145.00,
    "★ StatTrak™ Paracord Knife | Crimson Web minimal": 210.00,
    "★ StatTrak™ Kukri Knife | Crimson Web Fiel": 130.00,
    "★ StatTrak™ Kukri Knife | Blue Steel Minimal": 155.00,
    "★ StatTrak™ Huntsman Knife | Freehand Minimal": 120.00,
    "★ Huntsman Knife | Ultraviolet Minimal": 131.00,
    "★ StatTrak™ Huntsman Knife | Blue Steel Fiel": 182.00,
    "★ Shadow Daggers | Marble Fade Minimal": 150.00,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth Minimal": 145.00,
    "★ StatTrak™ Shadow Daggers | Tiger Tooth Factory": 151.00,
    "★ Classic Knife | Crimson Web Minimal": 231.00,
    "★ Flip Knife | Ultraviolet Fiel": 152.00,
    "★ StatTrak™ Flip Knife | Ultraviolet Fiel": 170.00,
    "★ Nomad Knife | Stained Minimal": 161.00,
    "★ StatTrak™ Nomad Knife | Damascus Steel Factory": 221.00,
    "★ StatTrak™ Survival Knife | Blue Steel Fiel": 106.00,
    "★ StatTrak™ Survival Knife | Crimson Web Fiel": 149.00,
    "★ StatTrak™ Survival Knife | Crimson Web Well": 149.00,
    "★ Survival Knife | Blue Steel Factory": 149.00,
    "★ StatTrak™ Survival Knife | Crimson Web Minimal": 174.00,
    "★ StatTrak™ Flip Knife | Ultraviolet Well": 160.00,
    "★ Flip Knife | Lore Fiel": 200.00,
    "★ StatTrak™ Falchion Knife | Lore Fiel": 150.00,
    "★ StatTrak™ Paracord Knife | Ultraviolet Well": 100.00,
    "★ StatTrak™ Paracord Knife | Blue Steel Fiel": 135.00,
    "★ StatTrak™ Bowie Knife | Lore Fiel": 138.00,
    "★ Bowie Knife | Ultraviolet Minimal": 113.00,
    "★ Ursus Knife | Blue Steel Minimal": 142.00,
    "★ StatTrak™ Ursus Knife | Ultraviolet Fiel": 142.00,
    "★ StatTrak™ Ursus Knife | Blue Steel Minimal": 149.00,
    "★ StatTrak™ Ursus Knife | Crimson Web Fiel": 215.00,
    "★ StatTrak™ Ursus Knife | Ultraviolet Minimal": 160.00,
    "★ StatTrak™ Nomad Knife | Damascus Steel Minimal": 200.00,
    "★ StatTrak™ Gut Knife | Blue Steel Minimal": 100.00,
    "★ Gut Knife | Autotronic Minimal": 149.00,
    "★ StatTrak™ Gut Knife | Autotronic Fiel": 148.00,
    "★ StatTrak™ Skeleton Knife | Urban Masked Minimal": 231.00,
    "★ Paracord Knife | Stained Factory": 134.00,
    "★ StatTrak™ Paracord Knife | Crimson Web Well": 142.00,
    "★ Survival Knife | Crimson Web Minimal": 150.00,
    "StatTrak™ AWP | Asiimov Battle": 165.00,
    "StatTrak™ AWP | Man-o'-war Minimal": 160.00,
    "StatTrak™ AWP | Neo-Noir Factory": 122.00,
    "StatTrak™ AWP | Corticera Factory": 164.00,
    "★ StatTrak™ Survival Knife | Damascus Steel Minimal": 106.00,
    "★ Falchion Knife | Lore Well": 125.00,
    "★ Falchion Knife | Blue Steel Well": 153.00,
    "★ StatTrak™ Falchion Knife | Freehand Factory": 165.00,
    "★ StatTrak™ Falchion Knife | Bright Water Factory": 145.00,
    "★ Nomad Knife | Blue Steel Well": 171.00,
    
}

notificados = {}
ultimo_escaneo = None
skins_revisadas_total = 0
ciclo_numero = 0
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

lock = threading.Lock()

# Cache temporal de precios
price_cache = {}
CACHE_TTL = 35  # segundos

failed_counts = {}

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

    disponibles = [

        p for p, t in PROXY_STATUS.items()

        if (
            t <= ahora
            and not PROXY_BANNED[p]
        )
    ]

    if not disponibles:

        cooldown_activos = [
            p for p, t in PROXY_STATUS.items()
            if t > ahora
        ]

        proxies_baneados = [
            p for p, b in PROXY_BANNED.items()
            if b
        ]

        print(
            f"[WARN] Sin proxies disponibles | "
            f"Cooldown: {len(cooldown_activos)} | "
            f"Baneados: {len(proxies_baneados)}"
        )

        # TODOS cooldown
        if len(cooldown_activos) == len(PROXIES):

            print("[WARN] Reset cooldown global")

            with lock:

                for p in PROXY_STATUS:
                    PROXY_STATUS[p] = 0

            return random.choice(PROXIES)

        # TODOS baneados
        if len(proxies_baneados) == len(PROXIES):

            print("[WARN] Reset banned global")

            with lock:

                for p in PROXY_BANNED:
                    PROXY_BANNED[p] = False

            return random.choice(PROXIES)

        return None

    return min(
        disponibles,
        key=lambda p: PROXY_LATENCY.get(p, 999)
    )

def verificar_proxy(proxy):

    print(f"[PROXY CHECK] Verificando {proxy}")

    proxies = {
        "http": proxy,
        "https": proxy
    }

    test_url = (
        "https://steamcommunity.com/market/search/render/"
        "?query=awp"
        "&start=0"
        "&count=1"
        "&search_descriptions=0"
        "&sort_column=popular"
        "&sort_dir=desc"
        "&appid=730"
        "&norender=1"
    )

    try:

        inicio = time.time()

        r = requests.get(
            test_url,
            headers=get_headers(),
            timeout=(5, 8),
            proxies=proxies
        )

        latency = round(time.time() - inicio, 2)

        with lock:
            PROXY_LATENCY[proxy] = latency

        if r.status_code != 200:

            print(f"[PROXY BAD STATUS] {proxy} -> {r.status_code}")

            with lock:
                PROXY_BANNED[proxy] = True

            ip_check = requests.get(
                "https://api.ipify.org",
                proxies=proxies,
                timeout=(4, 6)
            )

            print(f"[PROXY IP] {proxy} -> {ip_check.text}")

            return False

        content_type = r.headers.get("Content-Type", "")

        if "application/json" not in content_type:

            print(f"[PROXY INVALID CONTENT] {proxy}")

            with lock:
                PROXY_BANNED[proxy] = True

            return False

        data = r.json()

        if "results" not in data:

            print(f"[PROXY INVALID JSON] {proxy}")

            with lock:
                PROXY_BANNED[proxy] = True

            return False

        if latency > 5:

            print(f"[PROXY LENTO] {proxy} ({latency}s)")

        print(f"[PROXY OK] {proxy} ({latency}s)")

        with lock:

            PROXY_BANNED[proxy] = False

            PROXY_LAST_CHECK[proxy] = time.time()

        return True

    except Exception as e:

        print(f"[PROXY ERROR] {proxy} -> {e}")

        with lock:
            PROXY_BANNED[proxy] = True

        return False

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

            return cache_data["price"]

        print(f"\n[DEBUG] === BUSCANDO EXACTO: {market_hash_name} ===")

    url = "https://steamcommunity.com/market/search/render/"

    query = normalizar(market_hash_name)

    params = {
        "query": query,
        "start": 0,
        "count": 30,
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
            timeout=(5, 8),
            proxies=proxies
        )

        if r.status_code != 200:

            with lock:

                PROXY_FAILS[proxy] += 1

                if PROXY_FAILS[proxy] >= 3:

                    PROXY_STATUS[proxy] = (
                        time.time() + PROXY_COOLDOWN
                    )

                    print(f"[PROXY COOLDOWN] {proxy}")

                    PROXY_FAILS[proxy] = 0

            return None

        with lock:
            PROXY_FAILS[proxy] = 0

        data = r.json()

        results = data.get("results", [])

        best_price = None
        best_score = -1
        best_name = None

        for item in results:

            name_raw = item.get("name", "")

            name = normalizar(name_raw)

            price_raw = item.get("sell_price")

            price_text = item.get("sell_price_text", "")

            if not price_raw:
                continue

            # filtro basura
            if not es_item_valido(name):
                continue

            price = price_raw / 100

            score = 0

            query_words = set(query.split())
            name_words = set(name.split())

            coincidencias = len(query_words & name_words)

            score = coincidencias * 20

            # bonus importantes
            if "knife" in query and "knife" in name:
                score += 20

            if "stattrak" in query and "stattrak" in name:
                score += 20

            # bonus wear
            wears = [
                "factory",
                "minimal",
                "field",
                "well",
                "battle"
            ]

            for wear in wears:
                if wear in query and wear in name:
                    score += 15

            # castigo basura
            if "case" in name:
                score -= 999

            if score > best_score:
                best_score = score
                best_price = price
                best_name = name_raw
                best_market_price = price_text

        print(
            f"[DEBUG] MATCH FINAL: "
            f"{best_name} | "
            f"${best_price} | "
            f"market {best_market_price} | "
            f"score {best_score}"
        )
        
        if best_score == -1:
            failed_counts[market_hash_name] = failed_counts.get(market_hash_name, 0) + 1

        elif best_score >= 60:
            failed_counts[market_hash_name] = 0

        # =========================
        # GUARDAR CACHE
        # =========================
        if best_price is not None:

            with lock:

                price_cache[market_hash_name] = {
                    "price": best_price,
                    "timestamp": ahora
                }

        return best_price

    except Exception as e:

        print(f"[DEBUG] ERROR: {e}")

        with lock:

            PROXY_FAILS[proxy] += 1

            if PROXY_FAILS[proxy] >= 3:

                PROXY_STATUS[proxy] = (
                    time.time() + PROXY_COOLDOWN
                )

                print(f"[PROXY COOLDOWN] {proxy}")

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

    num_workers = min(5, len(lista))

    grupos = [[] for _ in range(num_workers)]

    for i, item in enumerate(lista):

        grupos[i % num_workers].append(item)

    return grupos

def worker(grupo_skins, worker_id):

    print(f"[DEBUG] Worker {worker_id} arrancó")

    session = requests.Session()

    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    global skins_revisadas_total

    while estado_app["activo"]:

        inicio_ciclo = time.time()

        for skin_name, precio_max in grupo_skins:

            proxy = obtener_proxy()

            if proxy is None:
                time.sleep(2)
                continue

            precio_actual = buscar_precio(
                skin_name,
                session,
                proxy
            )

            with lock:
                skins_revisadas_total += 1

            if precio_actual is None:
                continue

            ultima_alerta = notificados.get(skin_name)

            if precio_actual <= precio_max and (
                ultima_alerta is None
                or precio_actual < ultima_alerta
            ):

                steam_url = (
                    "https://steamcommunity.com/market/listings/730/"
                    + requests.utils.quote(skin_name)
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

            proxies_banned = len([
                p for p, b in PROXY_BANNED.items()
                if b
            ])

            print("\n================ RESUMEN CICLO ================")

            print(f"[INFO] Ciclo número: {ciclo_numero}")

            print(f"[INFO] Skins totales vigiladas: {len(skins_a_vigilar)}")

            print(f"[INFO] Skins revisadas: {skins_revisadas_total}")

            print(f"[INFO] Proxies activos: {proxies_activos}")

            print(f"[INFO] Proxies cooldown: {proxies_cooldown}")

            print(f"[INFO] Cache size: {len(price_cache)}")

            print(f"[INFO] Duración ciclo: {duracion} segundos")

            skins_a_eliminar = []

            for skin, fails in failed_counts.items():

                if fails >= 20:

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

        time.sleep(random.uniform(20, 40))

def monitor_proxies():

    while True:

        print("\n[PROXY MONITOR] Iniciando chequeo global...\n")

        for proxy in PROXIES:

            ultimo = PROXY_LAST_CHECK.get(proxy, 0)

            if time.time() - ultimo >= PROXY_CHECK_INTERVAL:

                verificar_proxy(proxy)

                time.sleep(3)

        print("\n[PROXY MONITOR] Fin chequeo global\n")

        time.sleep(300)
            
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

    proxy_thread = threading.Thread(target=monitor_proxies)
    proxy_thread.daemon = True
    proxy_thread.start()

    for t in threads:
        t.join()

    servidor_thread.join()
