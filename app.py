import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo Express - POS", layout="wide")

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
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; font-weight: bold; }
    .titulo-negocio { color: #FF8C00; font-size: 26px; font-weight: bold; text-align: center; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #0041C2; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    menu = st.radio("SECCIONES", ["📦 Inventario", "🛒 Ventas", "📊 Cierre de Caja"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.carrito = []
        st.rerun()

# --- SECCIÓN INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    with st.expander("➕ Registrar Nuevo Producto"):
        with st.form("form_registro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre del Producto")
                sto = st.number_input("Stock Inicial", min_value=0)
            with col2:
                p_detal = st.number_input("Precio Detal", min_value=0.0)
                p_mayor = st.number_input("Precio Mayor", min_value=0.0)
                m_mayor = st.number_input("Mínimo para Mayor", min_value=1)
            if st.form_submit_button("Guardar en Sistema"):
                supabase.table("inventario").insert({"nombre": nom, "stock": sto, "precio_detal": p_detal, "precio_mayor": p_mayor, "min_mayor": m_mayor}).execute()
                st.success("¡Producto guardado!")
                st.rerun()
    
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data)[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

# --- SECCIÓN VENTAS ---
elif menu == "🛒 Ventas":
    st.header("🛒 Módulo de Ventas")
    tasa = st.number_input("Tasa de Cambio (BCV)", min_value=1.0, value=50.0)
    
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        df_prod = pd.DataFrame(res.data)
        col_p, col_c = st.columns([3, 1])
        with col_p:
            seleccion = st.selectbox("Seleccione un producto", df_prod["nombre"])
        with col_c:
            cantidad = st.number_input("Cant.", min_value=1, value=1)
        
        p_info = df_prod[df_prod["nombre"] == seleccion].iloc[0]
        precio_usar = p_info["precio_mayor"] if cantidad >= p_info["min_mayor"] else p_info["precio_detal"]
        
        if st.button("➕ Agregar al Carrito"):
            if p_info["stock"] >= cantidad:
                st.session_state.carrito.append({
                    "producto": seleccion, "cantidad": cantidad, 
                    "precio_u": precio_usar, "subtotal": precio_usar * cantidad
                })
                st.rerun()
            else:
                st.error(f"Stock insuficiente ({p_info['stock']} disponibles).")

    if st.session_state.carrito:
        df_car = pd.DataFrame(st.session_state.carrito)
        st.table(df_car)
        total_usd = df_car["subtotal"].sum()
        st.subheader(f"Total: ${total_usd:.2f} | Bs. {total_usd * tasa:.2f}")

        st.markdown("### 💳 Métodos de Pago")
        c1, c2, c3, c4 = st.columns(4)
        with c1: p_efectivo = st.number_input("Efectivo $", min_value=0.0)
        with c2: p_punto = st.number_input("Punto $", min_value=0.0)
        with c3: p_movil = st.number_input("Pago Móvil $", min_value=0.0)
        with c4: p_zelle = st.number_input("Zelle $", min_value=0.0)
        p_otros = st.number_input("Otros $", min_value=0.0)
        
        if st.button("✅ Finalizar Venta"):
            total_pagado = p_efectivo + p_punto + p_movil + p_zelle + p_otros
            if total_pagado >= total_usd:
                try:
                    for i, item in enumerate(st.session_state.carrito):
                        # Solo asignamos los montos de pago al primer item de la venta para no duplicar totales en el cierre
                        venta = {
                            "fecha": datetime.now().isoformat(),
                            "producto": item["producto"],
                            "cantidad": item["cantidad"],
                            "total_usd": item["subtotal"],
                            "tasa_cambio": tasa,
                            "pago_efectivo": p_efectivo if i == 0 else 0,
                            "pago_punto": p_punto if i == 0 else 0,
                            "pago_movil": p_movil if i == 0 else 0,
                            "pago_zelle": p_zelle if i == 0 else 0,
                            "pago_otros": p_otros if i == 0 else 0
                        }
                        supabase.table("ventas").insert(venta).execute()
                        # Actualizar Stock
                        stock_actual = df_prod[df_prod["nombre"] == item["producto"]].iloc[0]["stock"]
                        supabase.table("inventario").update({"stock": stock_actual - item["cantidad"]}).eq("nombre", item["producto"]).execute()
                    
                    st.success("Venta Exitosa")
                    st.session_state.carrito = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Monto insuficiente.")

# --- SECCIÓN CIERRE DE CAJA (NUEVO) ---
elif menu == "📊 Cierre de Caja":
    st.header("📊 Resumen de Cierre de Caja")
    fecha_consulta = st.date_input("Seleccione el día", date.today())
    
    try:
        # Consultamos las ventas del día seleccionado
        res = supabase.table("ventas").select("*").gte("fecha", fecha_consulta.isoformat()).lt("fecha", pd.to_datetime(fecha_consulta + pd.Timedelta(days=1)).isoformat()).execute()
        
        if res.data:
            df_ventas = pd.DataFrame(res.data)
            
            # Sumatorias por tipo de pago
            total_efectivo = df_ventas["pago_efectivo"].sum()
            total_punto = df_ventas["pago_punto"].sum()
            total_movil = df_ventas["pago_movil"].sum()
            total_zelle = df_ventas["pago_zelle"].sum()
            total_otros = df_ventas["pago_otros"].sum()
            gran_total = total_efectivo + total_punto + total_movil + total_zelle + total_otros
            
            # Visualización en Tarjetas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💵 Efectivo", f"${total_efectivo:.2f}")
                st.metric("📱 Pago Móvil", f"${total_movil:.2f}")
            with col2:
                st.metric("💳 Punto de Venta", f"${total_punto:.2f}")
                st.metric("🏦 Zelle", f"${total_zelle:.2f}")
            with col3:
                st.metric("📦 Otros", f"${total_otros:.2f}")
                st.markdown(f"### 💰 TOTAL GENERAL\n## ${gran_total:.2f}")
            
            st.write("---")
            st.subheader("Detalle de Transacciones")
            st.dataframe(df_ventas[["fecha", "producto", "cantidad", "total_usd"]], use_container_width=True)
            
        else:
            st.info("No hay ventas registradas en la fecha seleccionada.")
    except Exception as e:
        st.error(f"Error al generar reporte: {e}")
