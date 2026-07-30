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
PROXY_IN_USE = {p: False for p in PROXIES}

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
    "Kukri Knife | Night Stripe Factory": 140.00,
    "StatTrak Skeleton Knife | Scorched Field": 174.00,
    "Falchion Knife | Ultraviolet Minimal": 150.00,
    "StatTrak Nomad Knife | Ultraviolet Field": 150.00,
    "StatTrak Bowie Knife | Lore Well": 125.00,
    "StatTrak Bowie Knife | Autotronic Well": 130.00,
    "StatTrak Bowie Knife | Damascus Steel minimal": 130.00,
    "StatTrak Bowie Knife | Lore minimal": 175.00,
    "StatTrak Paracord Knife | Damascus Steel factory": 109.00,
    "StatTrak Paracord Knife | Ultraviolet minimal": 150.00,
    "StatTrak Paracord Knife | Crimson Web minimal": 196.00,
    "StatTrak Kukri Knife | Crimson Web Field": 130.00,
    "StatTrak Kukri Knife | Blue Steel Minimal": 130.00,
    "Huntsman Knife | Ultraviolet Minimal": 132.00,
    "StatTrak Huntsman Knife | Blue Steel Field": 182.00,
    "Shadow Daggers | Marble Fade Minimal": 150.00,
    "StatTrak Shadow Daggers | Tiger Tooth Minimal": 138.00,
    "StatTrak Shadow Daggers | Tiger Tooth Factory": 115.00,
    "Classic Knife | Crimson Web Minimal": 231.00,
    "StatTrak Flip Knife | Ultraviolet Field": 165.00,
    "Nomad Knife | Stained Minimal": 161.00,
    "StatTrak Nomad Knife | Damascus Steel Factory": 215.00,
    "StatTrak Survival Knife | Crimson Web Field": 149.00,
    "StatTrak Survival Knife | Crimson Web Well": 120.00,
    "Survival Knife | Blue Steel Factory": 155.00,
    "StatTrak Survival Knife | Crimson Web Minimal": 176.00,
    "StatTrak Flip Knife | Ultraviolet Well": 160.00,
    "Flip Knife | Lore Field": 200.00,
    "StatTrak Bowie Knife | Black Laminate Factory": 170.00,
    "StatTrak Paracord Knife | Blue Steel Field": 125.00,
    "StatTrak Bowie Knife | Lore Field": 130.00,
    "Bowie Knife | Ultraviolet Minimal": 110.00,
    "Ursus Knife | Blue Steel Minimal": 135.00,
    "StatTrak Ursus Knife | Ultraviolet Field": 120.00,
    "StatTrak Ursus Knife | Blue Steel Minimal": 149.00,
    "StatTrak Ursus Knife | Crimson Web Field": 205.00,
    "StatTrak Ursus Knife | Ultraviolet Minimal": 150.00,
    "StatTrak Nomad Knife | Damascus Steel Minimal": 185.00,
    "Gut Knife | Autotronic Minimal": 149.00,
    "StatTrak Gut Knife | Autotronic Field": 135.00,
    "StatTrak Skeleton Knife | Urban Masked Minimal": 210.00,
    "Paracord Knife | Stained Factory": 134.00,
    "StatTrak Paracord Knife | Crimson Web Well": 135.00,
    "Survival Knife | Crimson Web Minimal": 150.00,
    "StatTrak AWP | Asiimov Battle": 165.00,
    "StatTrak AWP | Corticera Factory": 164.00,
    "Falchion Knife | Blue Steel Well": 154.00,
    "StatTrak Falchion Knife | Bright Water Factory": 125.00,
    "Nomad Knife | Blue Steel Well": 171.00,
    "StatTrak Falchion Knife | Damascus Steel field": 140.00,
    "StatTrak Falchion Knife | Freehand factory": 150.00,
    "StatTrak Falchion Knife | Damascus Steel factory": 170.00,
    
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
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }

def obtener_proxy(worker_id, proxy_actual=None):

    ahora = time.time()

    with lock:

        # Proxy fijo del worker
        proxy_fijo = PROXIES[worker_id % len(PROXIES)]

        # Si el proxy fijo está disponible, usar siempre ese
        if (
            PROXY_STATUS[proxy_fijo] <= ahora
            and not PROXY_IN_USE[proxy_fijo]
        ):
            PROXY_IN_USE[proxy_fijo] = True
            return proxy_fijo

        # Si ya tenía otro proxy y sigue disponible, seguir usándolo
        if (
            proxy_actual
            and PROXY_STATUS[proxy_actual] <= ahora
            and PROXY_IN_USE[proxy_actual]
        ):
            return proxy_actual

        # Liberar el anterior
        if proxy_actual:
            PROXY_IN_USE[proxy_actual] = False

        disponibles = [
            p for p in PROXIES
            if (
                PROXY_STATUS[p] <= ahora
                and not PROXY_IN_USE[p]
            )
        ]

        if not disponibles:
            print("[WARN] No hay proxies libres")
            return None

        proxy = random.choice(disponibles)

        PROXY_IN_USE[proxy] = True

        print(
            f"[PROXY NUEVO] "
            f"{threading.current_thread().name} -> {proxy}"
        )

        return proxy

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
            timeout=(8, 12),
            proxies=proxies
        )

        print(f"[HTTP] {proxy} -> {r.status_code}")

        if r.status_code == 429:

            print("=" * 70)
            print("[RATE LIMIT]")
            print("Proxy:", proxy)
            print("URL:", r.url)
            print("Status:", r.status_code)
            print("Headers:")
            print(dict(r.headers))
            print("=" * 70)

            with lock:

                PROXY_STATUS[proxy] = time.time() + PROXY_COOLDOWN
                PROXY_IN_USE[proxy] = False
                SESSIONS[proxy] = crear_session()
                PROXY_FAILS[proxy] = 0

            return None

        if r.status_code != 200:
            print("=" * 70)
            print("[HTTP ERROR]")
            print("Proxy:", proxy)
            print("Status:", r.status_code)
            print("URL:", r.url)
            print("Body:")
            print(r.text[:500])
            print("=" * 70)

            with lock:

                PROXY_FAILS[proxy] += 1

                if PROXY_FAILS[proxy] >= 5:

                    PROXY_STATUS[proxy] = (
                        time.time() + PROXY_COOLDOWN
                    )

                    PROXY_IN_USE[proxy] = False

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
        best_market_price = "N/A"

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
                    "name": best_name,
                    "timestamp": ahora
                }

        return {
            "price": best_price,
            "name": best_name
        }

    except Exception as e:

        import traceback

        print("=" * 70)
        print("[EXCEPTION]")
        print("Proxy:", proxy)
        print("Tipo:", type(e).__name__)
        print("Mensaje:", str(e))
        traceback.print_exc()
        print("=" * 70)

        with lock:

            PROXY_FAILS[proxy] += 1

            if PROXY_FAILS[proxy] >= 5:

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

    num_workers = min(4, len(lista))

    grupos = [[] for _ in range(num_workers)]

    for i, item in enumerate(lista):

        grupos[i % num_workers].append(item)

    return grupos

def worker(grupo_skins, worker_id):

    print(f"[DEBUG] Worker {worker_id} arrancó")
    
    proxy_actual = None

    global skins_revisadas_total

    while estado_app["activo"]:

        inicio_ciclo = time.time()

        for skin_name, precio_max in grupo_skins:

            resultado = None

            for intento in range(2):

                proxy_actual = obtener_proxy(worker_id, proxy_actual)

                proxy = proxy_actual

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

            time.sleep(random.uniform(8, 13))

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

def probar_proxies():

    print("\n========== TEST PROXIES ==========\n")

    for proxy in PROXIES:

        try:

            r = requests.get(
                "https://steamcommunity.com",
                proxies={
                    "http": proxy,
                    "https": proxy
                },
                headers=get_headers(),
                timeout=10
            )

            print(proxy)
            print("Status:", r.status_code)
            print()

        except Exception as e:

            print(proxy)
            print(type(e).__name__, e)
            print()

    print("=================================\n")

if __name__ == "__main__":

    probar_proxies()

    grupos = dividir_skins_en_grupos()

    print("=== DEBUG SYSTEM ===")
    print("Skins:", len(skins_a_vigilar))
    print("Proxies:", len(PROXIES))
    print("Grupos:", len(dividir_skins_en_grupos()))
    print("====================")

    threads = []

    for i, grupo in enumerate(grupos):
        t = threading.Thread(
            target=worker,
            args=(grupo, i),
            name=f"Worker-{i}"
        )
        t.start()
        threads.append(t)

    servidor_thread = threading.Thread(target=iniciar_servidor)
    servidor_thread.start()

    for t in threads:
        t.join()

    servidor_thread.join()
