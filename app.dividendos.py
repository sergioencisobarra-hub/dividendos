import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from collections import defaultdict
import plotly.express as px
import requests

st.set_page_config(page_title="Dividendos desde Excel", layout="wide")
st.title("📆 Calendario de Dividendos (Fuente Excel)")

# ==============================
# CARGAR EXCEL
# ==============================

RUTA = "CARTERA_acc_etf_fon.xlsx"

@st.cache_data
def cargar_datos():

    xls = pd.ExcelFile(RUTA, engine="openpyxl")

    st.write("📂 Hojas detectadas en el Excel:")
    st.write(xls.sheet_names)

    st.stop()

df = cargar_datos()

# ==============================
# INPUTS
# ==============================

mes = st.selectbox(
    "Mes",
    list(range(1, 13)),
    format_func=lambda x: datetime(2025, x, 1).strftime("%B")
)

año = st.number_input("Año", value=datetime.now().year)

vista = st.radio("Vista", ["Calendario", "Detalle de Lista"], horizontal=True)

# ==============================
# TIPOS DE CAMBIO
# ==============================

def obtener_tipos_cambio():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=EUR&symbols=USD,GBP"
        ).json()
        return r["rates"]
    except:
        return {"USD": 1.10, "GBP": 0.85}

rates = obtener_tipos_cambio()

# ==============================
# RETENCIONES
# ==============================

def calcular_neto(bruto_total, moneda):
    ret_origen = {
        "USD": 0.30,
        "GBP": 0.0,
        "EUR": 0.19
    }

    ret_esp = 0.19
    r_origen = ret_origen.get(moneda, 0.19)

    if moneda == "EUR":
        neto = bruto_total * (1 - ret_esp)
    else:
        neto = bruto_total * (1 - r_origen) * (1 - ret_esp)

    return neto

# ==============================
# FILTRAR MES
# ==============================

df_mes = df[
    (df["Fecha_pago"].dt.month == mes) &
    (df["Fecha_pago"].dt.year == año)
].copy()

if df_mes.empty:
    st.warning("No hay dividendos ese mes.")
    st.stop()

# Conversión y cálculo
resultados = []

for _, row in df_mes.iterrows():

    div = row["Dividendo_por_accion"]
    acciones = row["Acciones"]
    moneda = row["Moneda"]

    if moneda == "USD":
        div_eur = div / rates["USD"]
    elif moneda == "GBP":
        div_eur = div / rates["GBP"]
    else:
        div_eur = div

    bruto = div_eur * acciones
    neto = calcular_neto(bruto, moneda)

    resultados.append({
        "Empresa": row["Empresa"],
        "Ticker": row["Ticker"],
        "Fecha": row["Fecha_pago"].date(),
        "Día": row["Fecha_pago"].day,
        "Bruto €": round(bruto, 2),
        "Neto €": round(neto, 2)
    })

df_final = pd.DataFrame(resultados)

# ==============================
# CALENDARIO
# ==============================

if vista == "Calendario":

    calendario_mes = calendar.monthcalendar(año, mes)
    pagos_por_dia = defaultdict(list)

    for _, row in df_final.iterrows():
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
    df_sorted = df_final.sort_values("Fecha")
    st.dataframe(df_sorted)

# ==============================
# RESUMEN
# ==============================

st.markdown("---")
st.markdown(f"### Resumen mensual")
st.markdown(f"Empresas que pagan: **{df_final['Empresa'].nunique()}**")
st.markdown(f"Total neto estimado: **{round(df_final['Neto €'].sum(),2)} €**")

df_sorted = df_final.sort_values("Fecha")
df_sorted["Acumulado"] = df_sorted["Neto €"].cumsum()

fig = px.line(df_sorted, x="Fecha", y="Acumulado", markers=True)
st.plotly_chart(fig, use_container_width=True)

