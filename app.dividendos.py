import streamlit as st
import pandas as pd
import calendar
import json
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import plotly.express as px

st.set_page_config(page_title="Dividendos Estables", layout="wide")
st.title("📆 Dividendos Proyectados (Estable)")

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

mes = st.selectbox(
    "Mes",
    list(range(1, 13)),
    format_func=lambda x: datetime(2025, x, 1).strftime("%B")
)

año = st.number_input("Año", value=datetime.now().year)

# ================= CARGAR JSON =================

try:
    with open("historico_dividendos.json", "r") as f:
        historico_total = json.load(f)
except:
    st.error("No se encontró historico_dividendos.json en el repo.")
    st.stop()

# ================= PROYECCIÓN =================

def proyectar(historico):

    if len(historico) < 2:
        return None

    df = pd.DataFrame(historico)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["delta"] = df["date"].diff().dt.days
    intervalo = int(df["delta"].median())

    if intervalo <= 0:
        return None

    ultima_fecha = df["date"].iloc[-1]
    ultimo_div = df["dividend"].iloc[-1]

    siguiente = ultima_fecha + relativedelta(days=intervalo)

    return siguiente, float(ultimo_div)

filas = []

for ticker, acciones in cartera.items():

    historico = historico_total.get(ticker, [])

    proy = proyectar(historico)

    if not proy:
        continue

    fecha, div = proy

    if fecha.year != año or fecha.month != mes:
        continue

    bruto = div * acciones
    filas.append({
        "Ticker": ticker,
        "Fecha": fecha.date(),
        "Día": fecha.day,
        "Bruto": round(bruto, 2)
    })

if not filas:
    st.warning("No hay dividendos estimados para ese mes.")
    st.stop()

df = pd.DataFrame(filas)

cal = calendar.monthcalendar(año, mes)
pagos_por_dia = defaultdict(list)

for _, row in df.iterrows():
    pagos_por_dia[row["Día"]].append(row)

html = '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;font-family:monospace;">'

for semana in cal:
    for dia in semana:
        if dia == 0:
            html += '<div style="border:1px solid #eee;min-height:90px;"></div>'
        else:
            pagos = pagos_por_dia.get(dia, [])
            if pagos:
                html += f'<div style="border-left:6px solid #0047AB;padding:8px;min-height:90px;">'
                html += f"<strong>{dia}</strong><br>"
                for p in pagos:
                    html += f"{p['Ticker']}<br>"
                html += "</div>"
            else:
                html += f'<div style="border:1px solid #eee;padding:8px;min-height:90px;"><strong>{dia}</strong></div>'

html += "</div>"

st.markdown(html, unsafe_allow_html=True)

st.markdown("---")
st.markdown(f"Total estimado: **{round(df['Bruto'].sum(),2)} €**")

df = df.sort_values("Fecha")
df["Acumulado"] = df["Bruto"].cumsum()

fig = px.line(df, x="Fecha", y="Acumulado", markers=True)
st.plotly_chart(fig, use_container_width=True)
