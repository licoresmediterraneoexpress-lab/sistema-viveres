import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración y Estética
st.set_page_config(page_title="Sistema POS Víveres", layout="wide")
st.markdown("""<style> .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; } </style>""", unsafe_allow_html=True)

# Archivos Locales para guardar datos
DB_INV = "inventario.csv"
DB_VENTAS = "ventas.csv"

def cargar_datos():
    if os.path.exists(DB_INV): return pd.read_csv(DB_INV)
    return pd.DataFrame(columns=["ID", "Producto", "Stock", "Precio_Detal", "Precio_Mayor", "Min_Mayor"])

def guardar_datos(df):
    df.to_csv(DB_INV, index=False)

# Cargar datos
if 'inv' not in st.session_state: st.session_state.inv = cargar_datos()
if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- INTERFAZ ---
st.title("🛒 Sistema de Ventas Víveres y Licores")
tasa = st.sidebar.number_input("Tasa del dólar hoy:", value=1.0, step=0.1)

menu = st.sidebar.selectbox("Ir a:", ["Vender", "Inventario", "Reportes"])

if menu == "Vender":
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Caja")
        prod = st.selectbox("Selecciona Producto", st.session_state.inv["Producto"].tolist() if not st.session_state.inv.empty else ["No hay productos"])
        cant = st.number_input("Cantidad", min_value=1, value=1)
        
        if st.button("Agregar al Carrito"):
            item = st.session_state.inv[st.session_state.inv["Producto"] == prod].iloc[0]
            precio = item["Precio_Mayor"] if cant >= item["Min_Mayor"] else item["Precio_Detal"]
            st.session_state.carrito.append({"Producto": prod, "Cant": cant, "Precio $": precio, "Total $": precio * cant})

    with col2:
        st.subheader("Carrito")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c)
            total_usd = df_c["Total $"].sum()
            st.metric("Total USD", f"${total_usd:,.2f}")
            st.metric("Total Local", f"{total_usd * tasa:,.2f}")
            if st.button("Finalizar Venta"):
                # Aquí restaría del inventario (Lógica para la próxima versión)
                st.session_state.carrito = []
                st.success("Venta realizada con éxito")

elif menu == "Inventario":
    st.subheader("Gestión de Productos")
    with st.form("nuevo"):
        c1, c2, c3 = st.columns(3)
        nombre = c1.text_input("Nombre")
        stock = c2.number_input("Stock", min_value=0)
        p_d = c3.number_input("Precio Detal $")
        p_m = c1.number_input("Precio Mayor $")
        min_m = c2.number_input("Mínimo para Mayor", value=6)
        if st.form_submit_button("Guardar"):
            nuevo = pd.DataFrame([{"ID": len(st.session_state.inv)+1, "Producto": nombre, "Stock": stock, "Precio_Detal": p_d, "Precio_Mayor": p_m, "Min_Mayor": min_m}])
            st.session_state.inv = pd.concat([st.session_state.inv, nuevo], ignore_index=True)
            guardar_datos(st.session_state.inv)
            st.success("Guardado en tu PC")
    st.dataframe(st.session_state.inv)