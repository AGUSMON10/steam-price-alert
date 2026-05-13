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
    "https://steamcommunity.com/market/listings/730/G18800420DC083003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    182.00,
    "https://steamcommunity.com/market/listings/730/G18FD03209B033003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory0":
    215.00,
    "https://steamcommunity.com/market/listings/730/G188004202B3003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    150.00,
    "https://steamcommunity.com/market/listings/730/G188004200C3003?appid=730&category_730_Exterior=tag_WearCategory2":
    150.00,
    "https://steamcommunity.com/market/listings/730/G188004200C3003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory2":
    211.00,
    "https://steamcommunity.com/market/listings/730/G18820420DA083003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    170.00,
    "https://steamcommunity.com/market/listings/730/G188604202C3003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    170.00,
    "https://steamcommunity.com/market/listings/730/G18800420D2083003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    199.00,
    "https://steamcommunity.com/market/listings/730/G188504202A3003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory1":
    150.00,
    "https://steamcommunity.com/market/listings/730/G18800420C3043003?appid=730&category_730_Quality=tag_strange&category_730_Exterior=tag_WearCategory0":
    145.00
}

notificados = {}
ultimo_escaneo = None
skins_revisadas_total = 0
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
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://steamcommunity.com/market/",
        "Connection": "keep-alive"
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
    print(f"[COOLDOWN] Proxy bloqueado 15 min: {proxy_url}")

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

def obtener_lowest_sell_price(url_item, session):

    print(f"[DEBUG] Consultando listing: {url_item}")

    for intento in range(4):

        proxy_url = obtener_proxy()
        proxy_dict = {"http": proxy_url, "https": proxy_url}

        try:
            
            time.sleep(random.uniform(1.5, 4.5))

            r = session.get(
                url_item,
                headers=get_headers(),
                proxies=proxy_dict,
                timeout=20
            )

            print(f"[DEBUG] Status: {r.status_code}")
            print(f"[DEBUG] Proxy usado: {proxy_url}")

            if r.status_code == 429:
                print("[WARN] 429 detectado")
                marcar_proxy_malo(proxy_url)
                continue

            if r.status_code == 403:
                print("[WARN] 403 Forbidden")
                marcar_proxy_malo(proxy_url)
                continue

            if r.status_code == 502:
                print("[WARN] 502 Bad Gateway")
                marcar_proxy_malo(proxy_url)
                continue

            if r.status_code != 200:
                continue

            html = r.text

            # Buscar el precio más barato visible
            match = re.search(
                r'market_listing_price market_listing_price_with_fee">\s*\$?([\d,.]+)',
                html
            )

            if not match:

                match = re.search(
                    r'"lowest_price":"\$?([\d,.]+)"',
                    html
                )

            if not match:
                print("[WARN] No se encontró precio")
                print(html[:3000])
                continue

            precio_raw = "$" + match.group(1)

            print(f"[DEBUG] Precio raw: {precio_raw}")

            precio = re.sub(r"[^\d.,]", "", precio_raw)

            if "," in precio and "." in precio:
                precio = precio.replace(",", "")
            else:
                precio = precio.replace(",", ".")

            precio = float(precio)

            print(f"[DEBUG] Precio final: {precio}")

            return precio

        except Exception as e:
            print(f"[ERROR] Listing exception: {e}")
            marcar_proxy_malo(proxy_url)

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

    cantidad_proxies = min(len(PROXIES), len(lista))

    grupos = [[] for _ in range(cantidad_proxies)]

    for i, item in enumerate(lista):
        grupos[i % cantidad_proxies].append(item)

    return grupos

def worker(grupo_skins, worker_id):

    global skins_revisadas_total
    
    session = requests.Session()
    session.headers.update(get_headers())

    while estado_app["activo"]:
        inicio_ciclo = time.time()
        
        for url, precio_max in grupo_skins:

            precio_actual = obtener_lowest_sell_price(url, session)
            print(f"[CHECK] {obtener_nombre_skin(url)} -> {precio_actual}$ / objetivo {precio_max}$")

            if precio_actual is None:
                continue

            skins_revisadas_total += 1

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

                time.sleep(15)

                enviar_telegram("🔔 RECORDATORIO 🔔\n\n" + mensaje)

                notificados[url] = precio_actual

            time.sleep(random.randint(15, 30))

        time.sleep(5)

        estado_app["ultimo_escaneo"] = datetime.now().isoformat()

        if worker_id == 0:
            print(f"[INFO] Total skins: {len(skins_a_vigilar)}")
            print(f"[INFO] Proxies activos: {len(PROXIES)}")

            proxies_bloqueados = sum(
                1 for t in PROXY_STATUS.values()
                if t > time.time()
            )

            print(f"[INFO] Proxies cooldown: {proxies_bloqueados}")
            
            print(f"[INFO] Skins notificadas: {len(notificados)}")
            print(f"[INFO] Skins revisadas: {skins_revisadas_total}")
            skins_revisadas_total = 0

            duracion = round(time.time() - inicio_ciclo, 1)

            print(f"[INFO] Duración ciclo: {duracion} segundos")
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
            args=(grupos[i], i),
            daemon=True
        )
        t.start()
        threads.append(t)

    servidor_thread = threading.Thread(
        target=iniciar_servidor,
        daemon=True
    )
    servidor_thread.start()

    for t in threads:
        t.join()

    servidor_thread.join()
