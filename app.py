import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Dashboard Cartera", layout="wide")
st.title("📊 Dashboard de mi Cartera")

uploaded_file = st.file_uploader("Sube tu archivo CARTERA.xlsx", type=["xlsx"])

if uploaded_file is not None:

    # ==============================
    # 1️⃣ CARGA EXCEL
    # ==============================
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # Forzar columnas numéricas reales
    df["ACCIONES"] = pd.to_numeric(df["ACCIONES"], errors="coerce")
    df["PRECIO TOTAL"] = pd.to_numeric(df["PRECIO TOTAL"], errors="coerce")

    # Quinta columna = ticker original
    df["Ticker_Original"] = df.iloc[:, 4].astype(str)

    # ==============================
    # 2️⃣ CONVERSIÓN A YAHOO
    # ==============================
    def convertir_ticker(t):
        t = t.strip()
        if t.startswith("BME:"):
            return t.split(":")[1] + ".MC"
        if t.startswith("LON:"):
            return t.split(":")[1] + ".L"
        if t.startswith("ETR:") or t.startswith("etr:") or t.startswith("vie:"):
            return t.split(":")[1] + ".DE"
        if t.startswith("NYSE:") or t.startswith("nyse:"):
            return t.split(":")[1]
        if t.startswith("NASDAQ:"):
            return t.split(":")[1]
        if t.startswith("AMS:"):
            return t.split(":")[1] + ".AS"
        if t.startswith("epa:"):
            return t.split(":")[1] + ".PA"
        return t

    df["Ticker"] = df["Ticker_Original"].apply(convertir_ticker).str.upper()

    # ==============================
    # 3️⃣ TIPOS DE CAMBIO
    # ==============================
    try:
        eurusd = float(yf.download("EURUSD=X", period="1d", progress=False)["Close"].iloc[-1])
        gbpusd = float(yf.download("GBPUSD=X", period="1d", progress=False)["Close"].iloc[-1])
    except:
        st.error("No se pudieron descargar tipos de cambio.")
        st.stop()

    # ==============================
    # 4️⃣ DESCARGA PRECIOS POR ACCIÓN
    # ==============================
    precios_por_accion = []

    for t in df["Ticker"]:
        try:
            datos = yf.download(t, period="1d", progress=False)
            if datos.empty:
                raise Exception("Sin datos")

            precio = float(datos["Close"].iloc[-1])

            # 🇬🇧 UK (GBP)
            if t.endswith(".L"):

                # Muchas acciones UK cotizan en peniques
                if precio > 100:
                    precio = precio / 100

                # GBP → USD → EUR
                precio = (precio * gbpusd) / eurusd

            # 🇺🇸 USA (USD)
            elif "." not in t:
                precio = precio / eurusd

            # 🇪🇺 Europa ya en EUR

            precios_por_accion.append(precio)

        except:
            st.warning(f"No se pudo obtener precio para {t}")
            precios_por_accion.append(None)

    df["Precio por Acción €"] = precios_por_accion

    # Eliminar filas inválidas
    df = df.dropna(subset=["ACCIONES", "PRECIO TOTAL", "Precio por Acción €"])

    # ==============================
    # 5️⃣ CÁLCULOS FINANCIEROS
    # ==============================
    df["Valor Actual €"] = df["Precio por Acción €"] * df["ACCIONES"]
    df["Inversión Inicial €"] = df["PRECIO TOTAL"]

    df["Rentabilidad €"] = df["Valor Actual €"] - df["Inversión Inicial €"]
    df["Rentabilidad %"] = (df["Rentabilidad €"] / df["Inversión Inicial €"]) * 100

    total_inicial = float(df["Inversión Inicial €"].sum())
    total_actual = float(df["Valor Actual €"].sum())
    rentabilidad_total = ((total_actual - total_inicial) / total_inicial) * 100

    # ==============================
    # 6️⃣ DASHBOARD
    # ==============================
    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Inversión Inicial", f"{total_inicial:,.2f} €")
    col2.metric("Valor Actual", f"{total_actual:,.2f} €")
    col3.metric("Rentabilidad Total", f"{rentabilidad_total:.2f} %")

    st.divider()

    st.subheader("Detalle por posición")
    st.dataframe(
        df[[
            "Ticker",
            "ACCIONES",
            "Precio por Acción €",
            "Valor Actual €",
            "Inversión Inicial €",
            "Rentabilidad €",
            "Rentabilidad %"
        ]].sort_values("Rentabilidad %", ascending=False),
        use_container_width=True
    )

else:
    st.info("Sube tu archivo Excel para empezar.")

