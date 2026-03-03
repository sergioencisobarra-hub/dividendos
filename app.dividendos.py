import streamlit as st
import pandas as pd
import requests
import calendar
import json
import os
from datetime import datetime
from collections import defaultdict
import plotly.express as px

# ======================================
# CONFIGURACIÓN
# ======================================

st.set_page_config(page_title="Dividendos Robustecidos", layout="wide")
st.title("📆 Dividendos Automáticos (Modo Robusto)")

API_KEY = "hD9hC5yNHNLgzSn88NaDvmCIMOEEkMho"
CACHE_DIR = "cache_dividendos"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ======================================
# CARTERA
# ======================================

cartera = {
    "ENG.MC": 350,
    "ITX.MC": 100,
    "RED.MC": 350,
    "NG.L": 290,
    "SHEL.L": 100,
    "BAS.DE": 25,
    "PFE": 75,
    "PEP": 20,
    "IBM": 15,
    "O": 25,
    "MSFT": 5,
    "JNJ": 10,
    "PG": 25,
}

# ======================================
# INPUTS
# ======================================

mes = st.selectbox(
    "Mes",
    list(range(1, 13)),
    format_func=lambda x: datetime(2025, x, 1).strftime("%B")
)

año = st.number_input("Año", value=datetime.now().year)

vista = st.radio("Vista", ["Calendario", "Lista"], horizontal=True)

# ======================================
# TIPOS DE CAMBIO
# ======================================

def obtener_fx():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=EUR&symbols=USD,GBP",
            timeout=10
        )
        data = r.json()
        if "rates" in data:
            return data["rates"]
    except:
        pass
    return {"USD": 1.10, "GBP": 0.85}

rates = obtener_fx()

# ======================================
# RETENCIONES
# ======================================

def calcular_neto(bruto, moneda):
    ret_origen = {
        "USD": 0.30,
        "GBP": 0.0,
        "EUR": 0.19
    }
    ret_esp = 0.19
    r_origen = ret_origen.get(moneda, 0.19)

    if moneda == "EUR":
        return bruto * (1 - ret_esp)
    else:
        return bruto * (1 - r_origen) * (1 - ret_esp)

# ======================================
# DESCARGAR HISTÓRICO POR TICKER
# ======================================

def obtener_historico_ticker(ticker):

    cache_file = os.path.join(CACHE_DIR, f"{ticker}.json")

    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{ticker}?apikey={API_KEY}"

    try:
        r = requests.get(url, timeout=15)
        data = r.json()

        if "historical" in data and isinstance(data["historical"], list):
            with open(cache_file, "w") as f:
                json.dump(data["historical"], f)
            return data["historical"]

    except:
        pass

    # fallback cache
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    return []

# ======================================
# PROCESAR CARTERA
# ======================================

filas = []

for ticker, acciones in cartera.items():

    historico = obtener_historico_ticker(ticker)

    for item in historico:

        fecha_str = item.get("date")
        dividend = item.get("dividend")

        if not fecha_str or not dividend:
            continue

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            div = float(dividend)
        except:
            continue

        if fecha.year != año or fecha.month != mes:
            continue

        # detectar moneda
        if ticker.endswith(".L"):
            moneda = "GBP"
        elif ticker.endswith(".MC") or ticker.endswith(".DE"):
            moneda = "EUR"
        else:
            moneda = "USD"

        if moneda == "USD":
            div_eur = div / rates["USD"]
        elif moneda == "GBP":
            div_eur = div / rates["GBP"]
        else:
            div_eur = div

        bruto = div_eur * acciones
        neto = calcular_neto(bruto, moneda)

        filas.append({
            "Ticker": ticker,
            "Fecha": fecha.date(),
            "Día": fecha.day,
            "Neto €": round(neto, 2)
        })

if not filas:
    st.warning("No hay dividendos ese mes según histórico disponible.")
    st.stop()

df = pd.DataFrame(filas)

# ======================================
# CALENDARIO
# ======================================

if vista == "Calendario":

    calendario_mes = calendar.monthcalendar(año, mes)
    pagos_por_dia = defaultdict(list)

    for _, row in df.iterrows():
        pagos_por_dia[row["Día"]].append(row)

    html = '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;font-family:monospace;">'

    for semana in calendario_mes:
        for dia in semana:
            if dia == 0:
                html += '<div style="border:1px solid #eee;min-height:100px;"></div>'
            else:
                pagos = pagos_por_dia.get(dia, [])
                if pagos:
                    total = sum(p["Neto €"] for p in pagos)
                    intensidad = min(total / 200, 1)
                    color = f"rgba(0,71,171,{0.1 + intensidad*0.3})"

                    html += f'<div style="border-left:6px solid #0047AB;background:{color};padding:8px;min-height:100px;">'
                    html += f"<strong>{dia}</strong><br>"

                    for p in pagos:
                        html += f"<span style='color:#0047AB;font-weight:bold'>{p['Ticker']}</span><br>"

                    html += f"<small>Total: {round(total,2)} €</small>"
                    html += "</div>"
                else:
                    html += f'<div style="border:1px solid #eee;padding:8px;min-height:100px;"><strong>{dia}</strong></div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

else:
    st.dataframe(df.sort_values("Fecha"))

st.markdown("---")
st.markdown(f"### Total neto mensual estimado: **{round(df['Neto €'].sum(),2)} €**")

df_sorted = df.sort_values("Fecha")
df_sorted["Acumulado"] = df_sorted["Neto €"].cumsum()

fig = px.line(
    df_sorted,
    x="Fecha",
    y="Acumulado",
    markers=True,
    title="Acumulado Neto en el Mes"
)

st.plotly_chart(fig, use_container_width=True)
