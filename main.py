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

# Configuración
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 8080)) # Dinámico para Render

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("[ERROR] Faltan variables de entorno.")
    exit(1)

skins_a_vigilar = {
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Classic%20Knife%20%7C%20Urban%20Masked%20%28Field-Tested%29":
    111.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Damascus%20Steel%20%28Factory%20New%29":
    133.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Falchion%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    132.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Flip%20Knife%20%7C%20Bright%20Water%20%28Minimal%20Wear%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    160.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    137.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Bowie%20Knife%20%7C%20Blue%20Steel%20%28Field-Tested%29":
    150.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Flip%20Knife%20%7C%20Ultraviolet%20%28Well-Worn%29":
    155.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Paracord%20Knife%20%7C%20Crimson%20Web%20%28Well-Worn%29":
    134.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Kukri%20Knife%20%7C%20Urban%20Masked%20%28Minimal%20Wear%29":
    110.00,
    "https://steamcommunity.com/market/listings/730/%E2%98%85%20StatTrak%E2%84%A2%20Ursus%20Knife%20%7C%20Blue%20Steel%20%28Minimal%20Wear%29":
    141.00
}

# --- CACHÉ DE IDS ---
# Esto evita que Steam te banee por pedir la misma página mil veces
cache_nameids = {} 
notificados = {}
estado_app = {"activo": True, "errores": 0, "ultimo_escaneo": None}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "ok", "ultimo_escaneo": estado_app["ultimo_escaneo"]})

def obtener_item_nameid(url_item):
    # Si ya lo conocemos, no molestamos a Steam
    if url_item in cache_nameids:
        return cache_nameids[url_item]

    try:
        r = requests.get(url_item.split("?")[0], headers=HEADERS, timeout=10)
        if r.status_code == 429:
            print("[WARN] Rate limit en Steam. Esperando...")
            time.sleep(60)
            return None
        
        match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", r.text)
        nameid = match.group(1) if match else None
        
        if nameid:
            cache_nameids[url_item] = nameid # Guardar en caché
            return nameid
    except Exception as e:
        print(f"[ERROR] En nameid: {e}")
    return None

def obtener_lowest_sell_price(item_nameid):
    try:
        url = f"https://steamcommunity.com/market/itemordershistogram?language=english&currency=1&item_nameid={item_nameid}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "lowest_sell_order" in data:
                return int(data["lowest_sell_order"]) / 100
    except Exception as e:
        print(f"[ERROR] En precio: {e}")
    return None

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}, timeout=10)
    except:
        print("[ERROR] Telegram falló")

def escanear():
    estado_app["ultimo_escaneo"] = datetime.now().isoformat()
    for url, precio_max in skins_a_vigilar.items():
        nameid = obtener_item_nameid(url)
        if not nameid: continue

        precio_actual = obtener_lowest_sell_price(nameid)
        if precio_actual and precio_actual <= precio_max:
            # Solo notificar si el precio bajó respecto a la última vez que avisamos
            if url not in notificados or precio_actual < notificados[url]:
                enviar_telegram(f"🎯 ¡OFERTA!\n{url}\nPrecio: ${precio_actual}\nMáximo: ${precio_max}")
                notificados[url] = precio_actual
        
        time.sleep(3) # Pausa amigable entre items

def monitor_loop():
    while estado_app["activo"]:
        try:
            escanear()
            time.sleep(180) # Aumentado un poco para mayor seguridad
        except Exception as e:
            estado_app["errores"] += 1
            time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
