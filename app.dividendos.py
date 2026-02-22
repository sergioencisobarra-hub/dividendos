import streamlit as st
import pandas as pd
import requests
import calendar
from datetime import datetime
from collections import defaultdict
import plotly.express as px

st.set_page_config(page_title="Dividendos Automáticos", layout="wide")
st.title("📆 Dividendos Automáticos Internacionales")

API_KEY = "hD9hC5yNHNLgzSn88NaDvmCIMOEEkMho"

# ================= CARTERA =================

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

# ================= INPUT =================

mes = st.selectbox("Mes", list(range(1, 13)),
                   format_func=lambda x: datetime(2025, x, 1).strftime("%B"))

año = st.number_input("Año", value=datetime.now().year)

vista = st.radio("Vista", ["Calendario", "Lista"], horizontal=True)

# ================= TIPOS CAMBIO =================

def obtener_fx():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=EUR&symbols=USD,GBP"
        ).json()
        return r["rates"]
    except:
        return {"USD": 1.10, "GBP": 0.85}

rates = obtener_fx()

# ================= RETENCIONES =================

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

# ================= OBTENER CALENDARIO GLOBAL =================

@st.cache_data(ttl=3600)
def obtener_calendario_mes(año, mes):

    inicio = f"{año}-{mes:02d}-01"
    fin = f"{año}-{mes:02d}-31"

    url = f"https://financialmodelingprep.com/api/v3/stock_dividend_calendar?from={inicio}&to={fin}&apikey={API_KEY}"

    r = requests.get(url)
    data = r.json()

    return data

data = obtener_calendario_mes(año, mes)

# ================= FILTRAR CARTERA =================

filas = []

for item in data:

    ticker = item["symbol"]

    if ticker not in cartera:
        continue

    acciones = cartera[ticker]
    fecha_pago = datetime.strptime(item["paymentDate"], "%Y-%m-%d")
    div = float(item["dividend"])

    # Detectar moneda por sufijo
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
        "Fecha": fecha_pago.date(),
        "Día": fecha_pago.day,
        "Neto €": round(neto, 2)
    })

if not filas:
    st.warning("No hay dividendos ese mes.")
    st.stop()

df = pd.DataFrame(filas)

# ================= CALENDARIO =================

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

fig = px.line(df_sorted, x="Fecha", y="Acumulado", markers=True)
st.plotly_chart(fig, use_container_width=True)
