import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Panel Dividendos", layout="wide")

st.title("📊 Panel Profesional de Dividendos")

RETENCION = 0.19

# ------------------------------------
# CARGA DATOS
# ------------------------------------
@st.cache_data
def cargar_datos():
    try:
        cartera = pd.read_excel("CARTERA_acc_etf_fon.xlsx", sheet_name="CARTERA", engine="openpyxl")
        dividendos = pd.read_excel("CARTERA_acc_etf_fon.xlsx", sheet_name="DIVIDENDOS", engine="openpyxl")
    except Exception as e:
        st.error(f"Error cargando Excel: {e}")
        st.stop()

    dividendos["Fecha_pago"] = pd.to_datetime(dividendos["Fecha_pago"])
    df = dividendos.merge(cartera, on=["Empresa", "Ticker"], how="left")

    df["Importe_bruto"] = df["Dividendo_por_accion"] * df["Nº_acciones"]
    df["Importe_neto"] = df["Importe_bruto"] * (1 - 0.19)

    return df, cartera

# ------------------------------------
# ESTIMACIÓN ANUAL AUTOMÁTICA
# ------------------------------------
def estimar_dividendo_anual(ticker, acciones):
    try:
        stock = yf.Ticker(ticker)
        dividendos = stock.dividends.tail(4)
        anual = dividendos.sum()
        return anual * acciones
    except:
        return 0

st.subheader("📈 Estimación Dividendos Anuales")

estimaciones = []
for _, row in cartera.iterrows():
    anual = estimar_dividendo_anual(row["Ticker"], row["Nº_acciones"])
    coste = row["Precio_medio"] * row["Nº_acciones"]
    yield_coste = (anual / coste * 100) if coste > 0 else 0
    
    estimaciones.append({
        "Empresa": row["Empresa"],
        "Ingreso anual estimado (€)": round(anual,2),
        "Yield sobre coste (%)": round(yield_coste,2)
    })

df_estimaciones = pd.DataFrame(estimaciones)
st.dataframe(df_estimaciones, use_container_width=True)

total_anual_estimado = df_estimaciones["Ingreso anual estimado (€)"].sum()
st.markdown(f"### 💰 Total anual estimado: {round(total_anual_estimado,2)} €")

# ------------------------------------
# CALENDARIO MENSUAL
# ------------------------------------
st.subheader("📅 Calendario de Cobros")

col1, col2 = st.columns(2)

with col1:
    año = st.selectbox("Año", sorted(df["Fecha_pago"].dt.year.unique()))

with col2:
    mes = st.selectbox(
        "Mes",
        range(1, 13),
        format_func=lambda x: calendar.month_name[x]
    )

df_mes = df[
    (df["Fecha_pago"].dt.year == año) &
    (df["Fecha_pago"].dt.month == mes)
]

cal = calendar.monthcalendar(año, mes)
tabla = []

for semana in cal:
    fila = []
    for dia in semana:
        if dia == 0:
            fila.append("")
        else:
            pagos = df_mes[df_mes["Fecha_pago"].dt.day == dia]
            if not pagos.empty:
                total = pagos["Importe_neto"].sum()
                fila.append(f"💸 {dia}\n{round(total,2)} €")
            else:
                fila.append(str(dia))
    tabla.append(fila)

st.table(tabla)

# ------------------------------------
# DETALLE MES
# ------------------------------------
if not df_mes.empty:
    st.subheader("Detalle del mes")
    st.dataframe(df_mes.sort_values("Fecha_pago"), use_container_width=True)
    
    total_bruto = df_mes["Importe_bruto"].sum()
    total_neto = df_mes["Importe_neto"].sum()
    
    st.markdown(f"**Bruto:** {round(total_bruto,2)} €")
    st.markdown(f"**Neto (19%):** {round(total_neto,2)} €")

# ------------------------------------
# GRÁFICO ACUMULADO
# ------------------------------------
st.subheader("📊 Flujo de Dividendos Mensual")

df["Mes"] = df["Fecha_pago"].dt.to_period("M").astype(str)

resumen_mensual = df.groupby("Mes")["Importe_neto"].sum().reset_index()

fig = px.bar(
    resumen_mensual,
    x="Mes",
    y="Importe_neto",
    title="Dividendos Netos por Mes",
)

st.plotly_chart(fig, use_container_width=True)

