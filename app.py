import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import time, io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init(): return create_client(URL, KEY)
supabase = init()

if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- ESTILOS ---
st.markdown("<style>.stApp{background:white;} [data-testid='stSidebar']{background:#0041C2;} .stButton>button{background:#FF8C00;color:white;border-radius:10px; font-weight:bold;}</style>", unsafe_allow_html=True)

def generar_pdf(carrito, total_bs, total_usd, tasa):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(80, 10, "Producto"); pdf.cell(30, 10, "Cant."); pdf.cell(40, 10, "Precio ($)"); pdf.cell(40, 10, "Total ($)", ln=True)
        pdf.set_font("Arial", '', 12)
        for item in carrito:
            pdf.cell(80, 10, item['p']); pdf.cell(30, 10, str(item['c'])); pdf.cell(40, 10, f"{item['u']:.2f}"); pdf.cell(40, 10, f"{item['t']:.2f}", ln=True)
        pdf.ln(5)
        pdf.cell(190, 10, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
        pdf.cell(190, 10, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
        return pdf.output(dest='S').encode('latin-1')
    except: return None

with st.sidebar:
    st.markdown("<h2 style='color:#FF8C00;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📦 Inventario", "🛒 Ventas", "📊 Reportes"])
    if st.button("🗑️ Vaciar Todo"):
        st.session_state.carrito = []
        st.rerun()

# --- INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Inventario")
    with st.expander("➕ Nuevo Producto"):
        with st.form("f1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n, s = c1.text_input("Nombre"), c1.number_input("Stock", min_value=0)
            pd_v, pm_v, mm_v = c2.number_input("Precio Detal"), c2.number_input("Precio Mayor"), c2.number_input("Min. Mayor", min_value=1)
            if st.form_submit_button("Guardar"):
                supabase.table("inventario").insert({"nombre":n,"stock":int(s),"precio_detal":float(pd_v),"precio_mayor":float(pm_v),"min_mayor":int(mm_v)}).execute()
                st.success("Guardado"); st.rerun()
    res = supabase.table("inventario").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# --- VENTAS ---
elif menu == "🛒 Ventas":
    st.header("🛒 Ventas")
    tasa = st.number_input("Tasa BCV", min_value=1.0, value=50.0)
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        dfp = pd.DataFrame(
