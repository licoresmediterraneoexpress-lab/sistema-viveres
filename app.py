import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import time, io

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo POS Pro", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# Estado de la sesión
if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa;}
    [data-testid="stSidebar"] {background-color: #0041C2;}
    .stButton>button {
        background-color: #FF8C00;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #e67e00; border: 1px solid white; }
    .main-header { color: #0041C2; font-weight: bold; text-align: center; border-bottom: 2px solid #FF8C00; padding-bottom: 10px; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- UTILIDADES ---
def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Encabezado tabla
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, "Producto", 1); pdf.cell(20, 8, "Cant", 1); pdf.cell(45, 8, "Precio ($)", 1); pdf.cell(45, 8, "Total ($)", 1, ln=True)
    
    pdf.set_font("Arial", '', 10)
    for i in carrito:
        pdf.cell(80, 8, str(i['p']), 1); pdf.cell(20, 8, str(i['c']), 1); pdf.cell(45, 8, f"{i['u']:.2f}", 1); pdf.cell(45, 8, f"{i['t']:.2f}", 1, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 10, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(190, 10, f"Tasa: {tasa} Bs/$", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.markdown("<h1 style='color:white;text-align:center;'>MEDITERRANEO</h1>", unsafe_allow_html=True)
    opcion = st.radio("Módulos del Sistema", ["📦 Inventario", "🛒 Punto de Venta", "📊 Reportes y Cierre"])
    st.write("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []
        st.rerun()

# --- MODULO 1: INVENTARIO ---
if opcion == "📦 Inventario":
    st.markdown("<h1 class='main-header'>Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    with st.expander("➕ Agregar Nuevo Producto al Sistema"):
        with st.form("form_nuevo_prod", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n_prod = col1.text_input("Nombre del Producto")
            s_prod = col1.number_input("Existencia (Stock)", min_value=0, step=1)
            pd_prod = col2.number_input("Precio Detal ($)", min_value=0.0, format="%.2f")
            pm_prod = col2.number_input("Precio Mayor ($)", min_value=0.0, format="%.2f")
            mm_prod = col2.number_input("Mínimo para Mayor", min_value=1, step=1)
            
            if st.form_submit_button("Registrar Producto"):
                if n_prod:
                    db.table("inventario").insert({
                        "nombre": n_prod, "stock": s_prod, "precio_detal": pd_prod,
                        "precio_mayor": pm_prod, "min_mayor": mm_prod
                    }).execute()
                    st.success(f"Producto {n_prod} registrado con éxito.")
                    st.rerun()
                else: st.error("Debes ingresar un nombre.")

    st.subheader("📋 Lista de Existencias")
    res_inv = db.table("inventario").select("*").execute()
    if res_inv.data:
        df_inv = pd.DataFrame(res_inv.data)
        st.dataframe(df_inv[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

# --- MODULO 2: PUNTO DE VENTA ---
elif opcion == "🛒 Punto de Venta":
    st.markdown("<h1 class='main-header'>Punto de Venta</h1>", unsafe_allow_html=True)
    
    tasa = st.number_input("Tasa del Día (BCV / Paralelo)", min_value=1.0, value=60.0, step=0.1)
    
    res_stock = db.table("inventario").select("*").execute()
    if res_stock.data:
        df_p = pd.DataFrame(res_stock.data)
        
        # BUSCADOR INTELIGENTE
        st.write("### 🔍 Buscador de Productos")
        busqueda = st.text_input("Escribe el nombre del producto para filtrar...")
        
        df_filtro = df_p[df_p['nombre'].str.contains(busqueda, case=False)] if busqueda else df_p
        
        if not df_filtro.empty:
            c1, c2, c3 = st.columns([3, 1, 1])
            sel_p = c1.selectbox("Producto Seleccionado", df_filtro["nombre"])
            cant_p = c2.number_input("Cantidad", min_value=1, step=1)
            
            item_data = df_p[df_p["nombre"] == sel_p].iloc[0]
            # Lógica de precios
            p_aplicado = float(item_data["precio_mayor"]) if cant_p >= item_data["min_mayor"] else float(item_data["precio_detal"])
            c3.metric("Precio Unit.", f"${p_aplicado:.2f}")
            
            if st.button("➕ Agregar al Carrito"):
                if item_data["stock"] >= cant_p:
                    st.session_state.car.append({
                        "p": sel_p, "c": cant_p, "u": p
