import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mediterraneo Express - POS", layout="wide")

# 🔑 DATOS DE CONEXIÓN
URL_SUPABASE = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init_connection():
    return create_client(URL_SUPABASE, KEY_SUPABASE)

supabase = init_connection()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; font-weight: bold; width: 100%; }
    .titulo-negocio { color: #FF8C00; font-size: 26px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    st.write("---")
    menu = st.radio("SECCIONES", ["📦 Inventario", "🛒 Ventas", "📊 Cierre de Caja"])
    st.write("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.carrito = []
        st.rerun()

# --- MÓDULO: INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    with st.expander("➕ Registrar Nuevo Producto"):
        with st.form("form_registro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre del Producto")
                sto = st.number_input("Stock Inicial", min_value=0, step=1)
            with col2:
                p_detal = st.number_input("Precio Detal", min_value=0.0, format="%.2f")
                p_mayor = st.number_input("Precio Mayor", min_value=0.0, format="%.2f")
                m_mayor = st.number_input("Mínimo para Mayor", min_value=1, step=1)
            
            if st.form_submit_button("Guardar en Sistema"):
                if nom:
                    datos_inv = {
                        "nombre": nom, 
                        "stock": int(sto), 
                        "precio_detal": float(p_detal), 
                        "precio_mayor": float(p_mayor), 
                        "min_mayor": int(m_mayor)
                    }
                    supabase.table("inventario").insert(datos_inv).execute()
                    st.success(f"¡{nom} guardado!")
                    st.rerun()

    res = supabase.table("inventario").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data)[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

# --- MÓDULO: VENTAS ---
elif menu == "🛒 Ventas":
    st.header("🛒 Módulo de Ventas")
    tasa = st.number_input("Tasa de Cambio", min_value=1.0, value=50.0)
    
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        df_prod = pd.DataFrame(res.data)
        col_p, col_c = st.columns([3, 1])
        with col_p:
            seleccion = st.selectbox("Seleccione un producto", df_prod["nombre"])
        with col_c:
            cantidad = st.number_input("Cant.", min_value=1, value=1)
        
        p_info = df_prod[df_prod["nombre"] == seleccion].iloc[0]
        precio_usar = float(p_info["precio_mayor"]) if cantidad >= p_info["min_mayor"] else float(p_info["precio_detal"])
        
        if st.button("➕ Agregar al Carrito"):
            if int(p_info["stock"]) >= cantidad:
                st.session_state.carrito.append({
                    "producto": seleccion, "cantidad": int(cantidad), 
                    "precio_u": float(precio_usar), "subtotal": float(precio_usar * cantidad)
                })
                st.rerun()
            else:
                st.error("Stock insuficiente")

    if st.session_state.carrito:
        st.write("---")
        df_car = pd.DataFrame(st.session_state.carrito)
        st.table(df_car)
        total_usd = float(df_car["subtotal"].sum())
        st.subheader(f"Total: ${total_usd:.2f}")

        st.markdown("### 💳 Registro de Pago")
        c1, c2, c3, c4 = st.columns(4)
        with c1: ef = st.number_input("Efectivo $", min_value=0.0)
        with c2: pu = st.number_input("Punto $", min_value=0.0)
        with c3: mo = st.number_input("Pago Móvil $", min_value=0.0)
        with c4: ze = st.number_input("Zelle $", min_value=0.0)
        ot = st.number_input("Otros $", min_value=0.0)
        
        if st.button("✅ FINALIZAR VENTA"):
            if (ef + pu + mo + ze + ot) >= (total_usd - 0.01):
                try:
                    for i, item in enumerate(st.session_state.carrito):
                        # Aquí está la parte corregida del diccionario 'venta'
                        venta_data = {
                            "fecha": datetime.now().isoformat(),
                            "producto": item["producto"],
                            "cantidad": int(item["cantidad"]),
                            "total_usd": float(item["subtotal"]),
                            "tasa_cambio": float(tasa),
                            "pago_efectivo": float(ef) if i == 0 else 0.0,
                            "pago_punto": float(pu) if i == 0 else 0.0,
                            "pago_movil": float(mo) if i == 0 else 0.0,
                            "pago_zelle": float(ze) if i == 0 else 0.0,
                            "pago_otros": float(ot) if i == 0 else 0.0
                        }
                        supabase.table("ventas").insert(venta_data).execute()
                        
                        # Descontar stock
                        stk_act = int(df_prod[df_prod["nombre"] == item["producto"]].iloc[0]["stock"])
                        supabase.table("inventario").update({"stock": stk_act - item["cantidad"]}).eq("nombre", item["producto"]).execute()
                    
                    st.balloons()
                    st.success("🎉 ¡COMPRA EXITOSA!")
                    time.sleep(2)
                    st.session_state.carrito = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
