import random
import requests
import time
import re
import os
import threading
from flask import Flask, jsonify
from datetime import datetime

import builtins

# Redefinir print global con flush automático
original_print = print
def flush_print(*args, **kwargs):
    kwargs['flush'] = True
    return original_print(*args, **kwargs)

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
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife#":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Crimson%20Web%20%28Field-Tested%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Lore%20%28Well-Worn%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Huntsman%20Knife%20%7C%20Bright%20Water%20%28Factory%20New%29":
    126.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Huntsman%20Knife%20%7C%20Black%20Laminate%20%28Factory%20New%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    170.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Freehand%20%28Factory%20New%29":
    152.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    125.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Falchion%20Knife%20%7C%20Freehand%20%28Minimal%20Wear%29":
    140.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    155.00
}

notificados = {}
item_ids_cache = {}
ultimo_escaneo = None
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

# Headers realistas
HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

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


def obtener_item_nameid(url_item):
    try:
        url_item = limpiar_url(url_item)
        r = requests.get(url_item, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            print(f"[WARN] Steam devolvió HTTP 429 para {url_item}. Esperando 5 minutos...")
            time.sleep(300)
            return None
        if r.status_code == 200:
            match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
            if match:
                return match.group(1)
            else:
                print(f"[WARN] No se encontró item_nameid con patrón normal. Probando fallback...")
                fallback = re.search(
                    r'ItemActivityTicker.Start\( \{"sessionid":.+?"item_nameid":"(\d+)"',
                    r.text)
                if fallback:
                    return fallback.group(1)
        else:
            print(f"[ERROR] HTTP {r.status_code} al obtener página de {url_item}")
    except Exception as e:
        print(f"[ERROR] Excepción al obtener item_nameid de {url_item}: {e}")
        estado_app["errores"] += 1
    return None


def obtener_lowest_sell_price(item_nameid):
    try:
        url = f"https://steamcommunity.com/market/itemordershistogram?language=english&currency=1&item_nameid={item_nameid}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            print(f"[WARN] Steam devolvió HTTP 429 al pedir el histograma. Esperando 5 minutos...")
            time.sleep(300)
            return None
        if r.status_code == 200:
            data = r.json()
            if "lowest_sell_order" in data:
                return int(data["lowest_sell_order"]) / 100
    except Exception as e:
        print(f"[ERROR] Falló la consulta del precio: {e}")
        estado_app["errores"] += 1
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


def escanear():
    global ultimo_escaneo
    estado_app["ultimo_escaneo"] = datetime.now().isoformat()

    for url, precio_max in skins_a_vigilar.items():
        print(f"[INFO] Revisando: {url}")
        if url not in item_ids_cache:
    item_ids_cache[url] = obtener_item_nameid(url)

item_nameid = item_ids_cache.get(url)

if not item_nameid:
    print(f"[ERROR] No se pudo obtener item_nameid para: {url}")
    continue

        precio_actual = obtener_lowest_sell_price(item_nameid)
        if precio_actual is None:
            print(f"[INFO] No hay datos de venta para: {url}")
        else:
            print(f"[INFO] Precio de venta más bajo: {precio_actual:.2f} USD")
            ultima_alerta = notificados.get(url)
            if precio_actual <= precio_max and (ultima_alerta is None or
                                                precio_actual < ultima_alerta):
                mensaje = (
                    f"🛒 ¡Skin en venta por debajo del precio objetivo!\n"
                    f"{url}\n"
                    f"💵 Precio actual: {precio_actual:.2f} USD\n"
                    f"📉 Tu máximo: {precio_max:.2f} USD\n"
                    f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                enviar_telegram(mensaje)
                notificados[url] = precio_actual
        time.sleep(random.randint(40, 90)


def monitor_loop():
    """Bucle principal de monitoreo"""
    print("[INFO] Iniciando monitoreo de precios de Steam...")
    while estado_app["activo"]:
        try:
            print("\n🔄 Escaneando precios de venta en Steam...\n")
            escanear()
            print(f"[INFO] Esperando 300 segundos antes del próximo escaneo...")
            time.sleep(random.randint(600, 900)

        except KeyboardInterrupt:
            print("[INFO] Deteniendo monitoreo...")
            estado_app["activo"] = False
            break
        except Exception as e:
            print(f"[ERROR] Error en el bucle principal: {e}")
            estado_app["errores"] += 1
            time.sleep(180)  # Esperar menos tiempo en caso de error


# 🔁 Ejecutar el servidor Flask en hilo separado
def iniciar_servidor():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Iniciar el hilo de monitoreo
    monitor_thread = threading.Thread(target=monitor_loop)
    monitor_thread.start()

    # Iniciar el servidor web en otro hilo
    servidor_thread = threading.Thread(target=iniciar_servidor)
    servidor_thread.start()

    # Esperar ambos hilos (nunca termina)
    monitor_thread.join()
    servidor_thread.join()
