import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import calendar
from datetime import datetime
from collections import defaultdict
import plotly.express as px

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Panel Dividendos Internacional", layout="wide")
st.title("📆 Panel Profesional de Dividendos")

# ---------------- CARTERA ----------------
cartera = [
    ("ENAGÁS", "ENG.MC", 350),
    ("INDITEX", "ITX.MC", 100),
    ("REDEIA", "RED.MC", 350),
    ("NATIONAL GRID", "NG.L", 290),
    ("SHELL", "SHEL.L", 100),
    ("BASF", "BAS.DE", 25),
    ("PFIZER", "PFE", 75),
    ("PEPSICO", "PEP", 20),
    ("IBM", "IBM", 15),
    ("REALTY INCOME", "O", 25),
    ("MICROSOFT", "MSFT", 5),
    ("JOHNSON & JOHNSON", "JNJ", 10),
    ("PROCTER & GAMBLE", "PG", 25),
]

# ---------------- INPUTS ----------------
mes = st.selectbox("Mes", list(range(1, 13)),
                   format_func=lambda x: datetime(2025, x, 1).strftime("%B"))
año = st.number_input("Año", value=datetime.now().year)

vista = st.radio("Vista", ["Calendario", "Detalle de Lista"], horizontal=True)

# ---------------- TIPOS DE CAMBIO ----------------
def obtener_tipos_cambio():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=EUR&symbols=USD,GBP"
        ).json()
        return r["rates"]
    except:
        return {"USD": 1.10, "GBP": 0.85}

rates = obtener_tipos_cambio()

# ---------------- RETENCIONES ----------------
def calcular_neto(bruto_total, currency):
    ret_origen = {
        "USD": 0.30,
        "GBP": 0.0,
        "EUR": 0.19
    }

    ret_esp = 0.19
    r_origen = ret_origen.get(currency, 0.19)

    if currency == "EUR":
        neto = bruto_total * (1 - ret_esp)
    else:
        neto = bruto_total * (1 - r_origen) * (1 - ret_esp)

    return neto

# ---------------- OBTENER DIVIDENDOS ----------------
def dividendos_del_mes(ticker):
    tk = yf.Ticker(ticker)
    hist = tk.dividends

    if hist.empty:
        return []

    resultados = []
    for fecha, value in hist.items():
        if fecha.year == año and fecha.month == mes:
            resultados.append((fecha, float(value)))
    return resultados

filas = []

for nombre, ticker, acciones in cartera:
    pagos = dividendos_del_mes(ticker)
    if not pagos:
        continue

    info = yf.Ticker(ticker).info
    currency = info.get("currency", "EUR")

    for fecha, div in pagos:

        if currency == "USD":
            tipo_cambio = rates["USD"]
            div_eur = div / tipo_cambio
        elif currency == "GBP":
            tipo_cambio = rates["GBP"]
            div_eur = div / tipo_cambio
        else:
            tipo_cambio = 1
            div_eur = div

        bruto_total = div_eur * acciones
        neto_total = calcular_neto(bruto_total, currency)

        filas.append({
            "Empresa": nombre,
            "Ticker": ticker,
            "Fecha": fecha.date(),
            "Día": fecha.day,
            "Bruto €": round(bruto_total, 2),
            "Neto €": round(neto_total, 2)
        })

# ---------------- CSS ----------------
st.markdown("""
<style>
.calendar {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
    font-family: monospace;
}
.day {
    border: 1px solid #e6e6e6;
    padding: 10px;
    min-height: 100px;
    border-radius: 6px;
    transition: all 0.2s ease-in-out;
}
.day:hover {
    transform: translateY(-2px);
    box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
}
.has-dividend {
    border-left: 6px solid #0047AB;
}
.ticker {
    font-weight: bold;
    color: #0047AB;
    display: block;
    margin-top: 6px;
}
.tooltip {
    visibility: hidden;
    background-color: #111;
    color: #fff;
    padding: 6px;
    border-radius: 6px;
    font-size: 12px;
    position: absolute;
}
.day:hover .tooltip {
    visibility: visible;
}
@media (max-width: 768px) {
    .calendar { display: block; }
    .day { margin-bottom: 10px; }
}
</style>
""", unsafe_allow_html=True)

# ---------------- RENDER ----------------
if not filas:
    st.warning("No hay dividendos para ese mes.")
else:
    df = pd.DataFrame(filas)

    if vista == "Calendario":
        calendario = calendar.monthcalendar(año, mes)
        pagos_por_dia = defaultdict(list)

        for _, row in df.iterrows():
            pagos_por_dia[row["Día"]].append(row)

        html = '<div class="calendar">'

        for semana in calendario:
            for dia in semana:
                if dia == 0:
                    html += '<div class="day"></div>'
                else:
                    pagos = pagos_por_dia.get(dia, [])
                    if pagos:
                        total_dia = sum(p["Neto €"] for p in pagos)
                        intensidad = min(total_dia / 200, 1)
                        color = f"rgba(0,71,171,{0.08 + intensidad*0.3})"

                        html += f'<div class="day has-dividend" style="background-color:{color}">'
                        html += f'<div><strong>{dia}</strong></div>'

                        for p in pagos:
                            html += f'<span class="ticker">{p["Ticker"]}</span>'

                        html += f'<div class="tooltip">Total día: {round(total_dia,2)} €</div>'
                        html += '</div>'
                    else:
                        html += f'<div class="day"><strong>{dia}</strong></div>'

        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    else:
        df_sorted = df.sort_values("Fecha")
        for _, row in df_sorted.iterrows():
            st.markdown(f"""
            **{row['Fecha']}**  
            <span style="color:#0047AB; font-weight:bold;">{row['Ticker']}</span>  
            Neto estimado: {row['Neto €']} €  
            ---
            """, unsafe_allow_html=True)

    # Resumen
    st.markdown("---")
    st.markdown(f"### Resumen mensual")
    st.markdown(f"Empresas que pagan: **{df['Empresa'].nunique()}**")
    st.markdown(f"Total neto estimado: **{round(df['Neto €'].sum(),2)} €**")

    # Gráfico acumulado
    df_sorted = df.sort_values("Fecha")
    df_sorted["Acumulado"] = df_sorted["Neto €"].cumsum()

    fig = px.line(df_sorted,
                  x="Fecha",
                  y="Acumulado",
                  markers=True,
                  title="Acumulado Neto en el Mes")

    st.plotly_chart(fig, use_container_width=True)
