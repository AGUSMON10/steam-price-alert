"""Consulta de precios externos de SkinSniper para Steam Market Radar.

La extensión oficial usa GET /extension/lookup?name=<market_hash_name>.
Los precios devueltos por la API están expresados en milliUSD (1500 = USD 1.50).
Este módulo solo realiza una consulta por oportunidad y no consulta Steam.
"""

from __future__ import annotations

import requests
from urllib.parse import urljoin

API_URL = "https://api.skinsniper.com"
SITE_URL = "https://skinsniper.com"
TIMEOUT_SECONDS = 12
USER_AGENT = "SteamMarketRadar/1.0 (SkinSniper price comparison)"


def _precio_usd(valor):
    """Convierte milliUSD a USD; devuelve None si el dato no es válido."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if valor <= 0:
        return None
    return float(valor) / 1000.0


def _limpiar_texto(valor, max_len=120):
    if not isinstance(valor, str):
        return ""
    return " ".join(valor.replace("\n", " ").split())[:max_len]


def consultar_precios_skinsniper(nombre_skin, precio_steam=None, cantidad=5):
    """Devuelve el texto del segundo Telegram o None si no hay datos útiles."""
    nombre_skin = _limpiar_texto(nombre_skin, 200)
    if not nombre_skin:
        print("[SKINSNIPER] Nombre de skin vacío; se omite consulta.")
        return None

    try:
        response = requests.get(
            f"{API_URL}/extension/lookup",
            params={"name": nombre_skin},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        print(f"[SKINSNIPER] Error de conexión: {type(exc).__name__}: {exc}")
        return None

    if response.status_code != 200:
        print(
            f"[SKINSNIPER] HTTP {response.status_code}: "
            f"{response.text[:250]}"
        )
        return None

    try:
        data = response.json()
    except ValueError:
        print("[SKINSNIPER] La API devolvió una respuesta que no es JSON.")
        return None

    if not isinstance(data, dict):
        print("[SKINSNIPER] Formato de respuesta inesperado.")
        return None

    markets = data.get("markets")
    if not isinstance(markets, list) or not markets:
        print(f"[SKINSNIPER] Sin mercados/precios para: {nombre_skin}")
        return None

    validos = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        price = _precio_usd(market.get("price"))
        if price is None:
            continue
        market_name = _limpiar_texto(market.get("title") or market.get("name"), 60)
        if not market_name:
            continue
        ref = market.get("ref")
        link = urljoin(SITE_URL + "/", ref) if isinstance(ref, str) and ref.startswith("/") else ""
        validos.append({"name": market_name, "price": price, "link": link})

    # El endpoint ya suele devolverlos ordenados, pero ordenamos otra vez
    # para garantizar que el mensaje muestre los más baratos.
    validos.sort(key=lambda item: item["price"])
    validos = validos[:max(1, min(int(cantidad), 5))]

    if not validos:
        print(f"[SKINSNIPER] No hay precios válidos para: {nombre_skin}")
        return None

    nombre_respuesta = _limpiar_texto(data.get("name") or nombre_skin, 200)
    lineas = [
        "🌐 COMPARACIÓN DE MERCADOS — SKINSNIPER",
        nombre_respuesta,
        "",
        "Los 5 precios externos más bajos (USD):"
    ]

    for i, item in enumerate(validos, 1):
        linea = f"{i}. {item['name']}: ${item['price']:.2f}"
        if item["link"]:
            linea += f"\n   {item['link']}"
        lineas.append(linea)

    if isinstance(precio_steam, (int, float)) and not isinstance(precio_steam, bool) and precio_steam > 0:
        lineas.extend([
            "",
            f"🛒 Precio detectado en Steam: ${float(precio_steam):.2f} USD",
            f"📊 Diferencia vs. el mercado externo más barato: "
            f"${float(precio_steam) - validos[0]['price']:+.2f} USD"
        ])

    lineas.extend([
        "",
        "⚠️ Precios de referencia: pueden variar y no incluyen necesariamente "
        "comisiones, depósitos, retiros ni disponibilidad final."
    ])
    return "\n".join(lineas)
