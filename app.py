import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

# Estilo personalizado: Azul Rey y Naranja
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; width: 100%; }
    h1, h2, h3 { color: #0041C2; }
    .titulo-negocio { color: #FF8C00; font-size: 28px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS TEMPORAL (Simulada para que no falle) ---
if 'inventario' not in st.session_state:
    st.session_state.inventario = pd.DataFrame([
        {"Producto": "Producto A", "Precio": 100, "Stock": 20},
        {"Producto": "Producto B", "Precio": 50, "Stock": 50}
    ])

if 'ventas' not in st.session_state:
    st.session_state.ventas = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown('<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    st.write("---")
    menu = st.radio("MENÚ PRINCIPAL", ["Nueva Venta", "Inventario", "Reporte de Ventas"])

# --- LÓGICA DE LAS PÁGINAS ---

if menu == "Nueva Venta":
    st.header("🛒 Registrar Nueva Venta")
    col1, col2 = st.columns(2)
    
    with col1:
        prod = st.selectbox("Seleccione Producto", st.session_state.inventario["Producto"])
        cant = st.number_input("Cantidad", min_value=1, value=1)
        
    precio_unitario = st.session_state.inventario.loc[st.session_state.inventario["Producto"] == prod, "Precio"].values[0]
    total = precio_unitario * cant
    
    st.subheader(f"Total a Pagar: ${total}")
    
    if st.button("Confirmar Venta"):
        nueva_venta = {
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Producto": prod,
            "Cantidad": cant,
            "Total": total
        }
        st.session_state.ventas.append(nueva_venta)
        st.success("✅ Venta registrada con éxito")

elif menu == "Inventario":
    st.header("📦 Control de Inventario")
    st.dataframe(st.session_state.inventario, use_container_width=True)
    
    st.subheader("Agregar Nuevo Producto")
    with st.expander("Abrir formulario"):
        nombre_n = st.text_input("Nombre del Producto")
        precio_n = st.number_input("Precio", min_value=1)
        stock_n = st.number_input("Stock Inicial", min_value=1)
        if st.button("Guardar Producto"):
            nuevo_item = {"Producto": nombre_n, "Precio": precio_n, "Stock": stock_n}
            st.session_state.inventario = pd.concat([st.session_state.inventario, pd.DataFrame([nuevo_item])], ignore_index=True)
            st.rerun()

elif menu == "Reporte de Ventas":
    st.header("📊 Reporte de Ventas")
    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        st.table(df_ventas)
        st.metric("Ventas Totales del Día", f"${df_ventas['Total'].sum()}")
    else:
        st.info("Aún no hay ventas registradas hoy.")

