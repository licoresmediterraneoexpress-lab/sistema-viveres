import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import time, io

# --- CONFIGURACIÓN TIPO EMPRESARIAL ---
st.set_page_config(page_title="Mediterraneo ERP v4", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# --- ESTILOS PROFESIONALES ---
st.markdown("""
<style>
    .stApp {background:#f0f2f5;}
    [data-testid='stSidebar'] {background:#1e293b;}
    .stButton>button {background:#2563eb; color:white; border-radius:5px;}
    .stMetric {background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #2563eb;}
    .valery-card {background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
</style>
""", unsafe_allow_html=True)

# --- UTILIDADES ---
def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS - POS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "P.$", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    pdf.set_font("Arial", '', 9)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MENU EMPRESARIAL</h2>", unsafe_allow_html=True)
    m = st.radio("Módulos", ["📦 Maestro de Inventario", "🛒 Facturación (POS)", "📊 Cierre y Auditoría"])
    if st.button("🗑️ Resetear Carrito"):
        st.session_state.car = []; st.rerun()

# --- 1. MAESTRO DE INVENTARIO (ESTILO VALERY) ---
if m == "📦 Maestro de Inventario":
    st.title("📦 Maestro de Productos y Servicios")
    t1, t2, t3 = st.tabs(["📑 Inventario Actual", "➕ Nuevo Producto", "🔄 Ajustes de Entrada/Salida"])

    with t1:
        st.subheader("Buscador Maestro")
        busq_m = st.text_input("Filtrar por nombre, código o descripción...")
        res = db.table("inventario").select("*").execute()
        if res.data:
            df_i = pd.DataFrame(res.data)
            if busq_m: df_i = df_i[df_i['nombre'].str.contains(busq_m, case=False)]
            st.dataframe(df_i, use_container_width=True, hide_index=True)

    with t2:
        with st.form("nuevo_item"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre del Producto")
            s = c1.number_input("Existencia Inicial", 0)
            pd_v = c2.number_input("Precio Detal $", 0.0)
            pm_v = c2.number_input("Precio Mayor $", 0.0)
            mm_v = c2.number_input("Mínimo Mayorista", 1)
            if st.form_submit_button("Registrar en Catálogo"):
                db.table("inventario").insert({"nombre":n,"stock":s,"precio_detal":pd_v,"precio_mayor":pm_v,"min_mayor":mm_v}).execute()
                st.success("Registrado correctamente"); st.rerun()

    with t3:
        st.subheader("Movimientos de Almacén")
        if res.data:
            with st.form("ajuste_valery"):
                prod = st.selectbox("Seleccionar Item", [x['nombre'] for x in res.data])
                tipo = st.selectbox("Concepto", ["Compra de Mercancía (+)", "Consumo Interno (-)", "Avería/Vencimiento (-)", "Ajuste por Inventario Fisico"])
                cant = st.number_input("Cantidad del Movimiento", 1)
                if st.form_submit_button("Procesar Movimiento"):
                    curr = next(i for i in res.data if i['nombre'] == prod)
                    new_s = (curr['stock'] + cant) if "+" in tipo else (curr['stock'] - cant)
                    db.table("inventario").update({"stock": new_s}).eq("nombre", prod).execute()
                    st.success(f"Kardex Actualizado: {prod} -> Nuevo Stock: {new_s}"); st.rerun()

# --- 2. FACTURACIÓN POS ---
elif m == "🛒 Facturación (POS)":
    st.title("🛒 Punto de Venta")
    tasa = st.number_input("Tasa Referencial Bs/$", 1.0, 1000.0, 60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        # BUSCADOR INTELIGENTE EN TIEMPO REAL
        busq = st.text_input("🔍 Buscar Producto (ej: har, arr, pol)...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busq)] if busq else df_p
        
        if not df_f.empty:
            c1, c2 = st.columns([3, 1])
            sel = c1.selectbox("Producto Seleccionado", df_f["nombre"])
            can = c2.number_input("Cant", 1)
            
            it = df_p[df_p["nombre"] == sel].iloc[0]
            pre = float(it["precio_mayor"]) if can >= it["min_mayor"] else float(it["precio_detal"])
            
            if st.button("➕ Añadir a Factura"):
                if it["stock"] >= can:
                    st.session_state.car.append({"p":sel, "c":can, "u":pre, "t":pre*can})
                    st.rerun()
                else: st.error("Sin Existencia")
    
    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1])
            ca.info(f"**{x['p']}** | {x['c']} x ${x['u']:.2f} = ${x['t']:.2f}")
            if cb.button("❌", key=f"d_{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        tu, tb = sum(z['t'] for z in st.session_state.car), sum(z['t'] for z in st.session_state.car) * tasa
        st.markdown(f"### TOTAL A PAGAR: **Bs. {tb:,.2f}** (${tu:,.2f})")
        
        c1, c2, c3 = st.columns(3)
        e_b = c1.number_input("Efectivo Bs", 0.0); pm_b = c1.number_input("Pago Móvil Bs", 0.0)
        p_b = c2.number_input("Punto Bs", 0.0); ot_b = c2.number_input("Otros Bs", 0.0)
        z_u = c3.number_input("Zelle $", 0.0); d_u = c3.number_input("Divisas $", 0.0)
        
        pag = e_b + pm_b + p_b + ot_b + ((z_u + d_u) * tasa)
        if pag < tb - 0.1: st.warning(f"Diferencia: {tb-pag:,.2f} Bs.")
        else:
            st.success(f"Cambio: {pag-tb:,.2f} Bs.")
            if st.button("✅ TOTALIZAR FACTURA"):
                try:
                    for v in st.session_state.car:
                        db.table("ventas").insert({"producto":v['p'],"cantidad":v['c'],"total_usd":v['t'],"tasa_cambio":tasa,"p_efectivo":e_b,"p_movil":pm_b,"p_punto":p_b,"p_zelle":z_u,"p_divisas":d_u,"fecha":datetime.now().isoformat()}).execute()
                        stk_a = int(df_p[df_p["nombre"] == v['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_a - v['c']}).eq("nombre", v['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, tb, tu, tasa)
                    st.session_state.car = []; st.success("Venta Procesada"); st.rerun()
                except Exception as e: st.error(f"Error de base de datos: {e}")
    if st.session_state.pdf_b: st.download_button("📥 Imprimir Ticket", st.session_state.pdf_b, "ticket.pdf")

# --- 3. CIERRE Y AUDITORÍA ---
elif m == "📊 Cierre y Auditoría":
    st.title("📊 Auditoría de Ventas y Caja")
    f = st.date_input("Consultar Fecha", date.today())
    try:
        res_v = db.table("ventas").select("*").gte("fecha", f.isoformat()).execute()
        if res_v.data:
            df_v = pd.DataFrame(res_v.data)
            
            # --- CORRECCIÓN KEYERROR: Validación de columnas ---
            cols_check = ['p_efectivo', 'p_movil', 'p_punto', 'p_zelle', 'p_divisas', 'total_usd']
            for c in cols_check:
                if c not in df_v.columns: df_v[c] = 0.0
            
            st.subheader(f"Cuadre de Caja - {f}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Efectivo Bs", f"{df_v['p_efectivo'].sum():,.2f}")
            c2.metric("Pago Móvil Bs", f"{df_v['p_movil'].sum():,.2f}")
            c3.metric("Punto/Otros Bs", f"{df_v['p_punto'].sum():,.2f}")
            c4.metric("Divisas/Zelle $", f"{(df_v['p_zelle'].sum() + df_v['p_divisas'].sum()):,.2f}")
            
            st.write("---")
            st.subheader("Historial de Facturación")
            st.dataframe(df_v, use_container_width=True)
        else: st.info("No hay movimientos registrados para esta fecha.")
    except Exception as e: st.error(f"Error de reporte: {e}")
