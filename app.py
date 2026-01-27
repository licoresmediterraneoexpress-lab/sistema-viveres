import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import time, io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS v3", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# --- ESTILOS ---
st.markdown("<style>.stApp{background:#f4f7f6;} [data-testid='stSidebar']{background:#0041C2;} .stButton>button{background:#FF8C00;color:white;border-radius:8px;font-weight:bold;width:100%;}</style>", unsafe_allow_html=True)

def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "Precio $", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    pdf.set_font("Arial", '', 9)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    m = st.radio("Módulos", ["📦 Inventario y Ajustes", "🛒 Punto de Venta", "📊 Reportes y Cierre"])
    if st.button("🗑️ Limpiar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 1. INVENTARIO Y AJUSTES ---
if m == "📦 Inventario y Ajustes":
    st.header("📦 Gestión de Inventario")
    tab1, tab2 = st.tabs(["📋 Listado / Nuevo", "⚙️ Ajustes de Stock"])
    
    with tab1:
        with st.expander("➕ Registrar Producto"):
            with st.form("f_inv", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nom = c1.text_input("Nombre")
                stk = c1.number_input("Stock Inicial", 0)
                p_d = c2.number_input("Precio Detal ($)", 0.0)
                p_m = c2.number_input("Precio Mayor ($)", 0.0)
                m_m = c2.number_input("Min. Mayor", 1)
                if st.form_submit_button("Guardar"):
                    db.table("inventario").insert({"nombre":nom,"stock":stk,"precio_detal":p_d,"precio_mayor":p_m,"min_mayor":m_m}).execute()
                    st.success("Guardado"); st.rerun()
        
        res = db.table("inventario").select("*").execute()
        if res.data:
            df_inv = pd.DataFrame(res.data)
            st.dataframe(df_inv[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

    with tab2:
        st.subheader("🛠️ Ajustes y Correcciones")
        if res.data:
            with st.form("f_ajuste"):
                p_ajuste = st.selectbox("Seleccione Producto", [x['nombre'] for x in res.data])
                tipo = st.selectbox("Tipo de Movimiento", ["Carga (Compra)", "Descarga (Consumo Interno)", "Descarga (Dañado/Vencido)", "Corrección Manual"])
                cant_aj = st.number_input("Cantidad", 1)
                if st.form_submit_button("Aplicar Ajuste"):
                    act = next(item for item in res.data if item["nombre"] == p_ajuste)
                    n_stk = (act['stock'] + cant_aj) if "Carga" in tipo else (act['stock'] - cant_aj)
                    db.table("inventario").update({"stock": n_stk}).eq("nombre", p_ajuste).execute()
                    st.success(f"Ajuste aplicado: {p_ajuste} ahora tiene {n_stk} unidades."); st.rerun()

# --- 2. PUNTO DE VENTA (CON BUSCADOR INTELIGENTE) ---
elif m == "🛒 Punto de Venta":
    st.header("🛒 Punto de Venta")
    tasa = st.number_input("Tasa del día (Bs/$)", 1.0, 500.0, 60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # BUSCADOR INTELIGENTE (FILTRADO AUTOMÁTICO)
        busq = st.text_input("🔍 Escriba para buscar (ej: 'cer' para Cerveza)...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busq)] if busq else df_p
        
        if not df_f.empty:
            c1, c2 = st.columns([3, 1])
            p_sel = c1.selectbox("Producto", df_f["nombre"])
            c_sel = c2.number_input("Cant", 1)
            
            it = df_p[df_p["nombre"] == p_sel].iloc[0]
            pre = float(it["precio_mayor"]) if c_sel >= it["min_mayor"] else float(it["precio_detal"])
            
            if st.button("➕ Añadir"):
                if it["stock"] >= c_sel:
                    st.session_state.car.append({"p":p_sel, "c":c_sel, "u":pre, "t":pre*c_sel})
                    st.rerun()
                else: st.error("Stock insuficiente")
        else: st.warning("No hay coincidencias")

    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1])
            ca.info(f"**{x['p']}** | {x['c']} x ${x['u']:.2f} = ${x['t']:.2f}")
            if cb.button("❌", key=f"del_{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        tot_u = sum(z['t'] for z in st.session_state.car); tot_b = tot_u * tasa
        st.markdown(f"### Total: **Bs. {tot_b:,.2f}** (${tot_u:,.2f})")
        
        c1, c2, c3 = st.columns(3)
        ef_b = c1.number_input("Efectivo Bs", 0.0); pm_b = c1.number_input("Pago Móvil Bs", 0.0)
        pu_b = c2.number_input("Punto Bs", 0.0); ot_b = c2.number_input("Otros Bs", 0.0)
        ze_u = c3.number_input("Zelle $", 0.0); di_u = c3.number_input("Divisas $", 0.0)
        
        pago = ef_b + pm_b + pu_b + ot_b + ((ze_u + di_u) * tasa)
        if pago < tot_b - 0.1: st.warning(f"Falta: {tot_b-pago:,.2f} Bs.")
        else:
            st.success(f"Vuelto: {pago-tot_b:,.2f} Bs.")
            if st.button("✅ FINALIZAR VENTA"):
                try:
                    for v in st.session_state.car:
                        db.table("ventas").insert({"producto":v['p'],"cantidad":v['c'],"total_usd":v['t'],"tasa_cambio":tasa,"p_efectivo":ef_b,"p_movil":pm_b,"p_punto":pu_b,"p_zelle":ze_u,"p_divisas":di_u,"fecha":datetime.now().isoformat()}).execute()
                        stk_a = int(df_p[df_p["nombre"] == v['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_a - v['c']}).eq("nombre", v['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, tot_b, tot_u, tasa)
                    st.session_state.car = []; st.success("Venta Exitosa"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    if st.session_state.pdf_b: st.download_button("📥 Ticket PDF", st.session_state.pdf_b, "ticket.pdf")

# --- 3. REPORTES Y CIERRE ---
elif m == "📊 Reportes y Cierre":
    st.header("📊 Cierre de Caja")
    f_c = st.date_input("Día", date.today())
    res_v = db.table("ventas").select("*").gte("fecha", f_c.isoformat()).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo Bs", f"{df_v['p_efectivo'].sum():,.2f}")
        c1.metric("Pago Móvil Bs", f"{df_v['p_movil'].sum():,.2f}")
        c2.metric("Punto Bs", f"{df_v['p_punto'].sum():,.2f}")
        c2.metric("Zelle $", f"{df_v['p_zelle'].sum():,.2f}")
        c3.metric("Divisas $", f"{df_v['p_divisas'].sum():,.2f}")
        c3.metric("TOTAL $", f"{df_v['total_usd'].sum():,.2f}")
        st.dataframe(df_v, use_container_width=True)
    else: st.info("Sin ventas")
