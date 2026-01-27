import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="Mediterraneo POS Premium", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

# Inicializar estados de sesión
if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# Estilos personalizados
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold; width: 100%;}
    .stMetric {background: #F0F7FF; padding: 10px; border-radius: 10px; border-left: 5px solid #0041C2;}
    .propina-box { background-color: #D4EDDA; padding: 10px; border-radius: 5px; color: #155724; font-weight: bold; border: 1px solid #c3e6cb; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
def crear_ticket(carrito, total_bs, total_usd, tasa, propina_usd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    # Encabezado tabla
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "P. Unit $", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 11)
    if propina_usd > 0:
        pdf.cell(190, 7, f"RECARGO / SERVICIO: ${propina_usd:.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {(total_usd + propina_usd):,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "📊 Reporte de Caja"])
    st.markdown("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. MÓDULO: INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    autorizado = (clave == CLAVE_ADMIN)

    t1, t2 = st.tabs(["📋 Listado y Edición", "🆕 Nuevo Producto"])
    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar en inventario...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            st.dataframe(df_m[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True, hide_index=True)
            
            if autorizado:
                st.write("---")
                st.subheader("🛠️ Editar Item Seleccionado")
                sel = st.selectbox("Seleccione producto", df_inv["nombre"])
                it = df_inv[df_inv["nombre"] == sel].iloc[0]
                c1, c2, c3 = st.columns(3)
                en = c1.text_input("Nombre", it["nombre"])
                es = c1.number_input("Stock", value=int(it["stock"]))
                epd = c2.number_input("Precio Detal $", value=float(it["precio_detal"]))
                epm = c2.number_input("Precio Mayor $", value=float(it["precio_mayor"]))
                emm = c3.number_input("Mínimo para Mayor", value=int(it["min_mayor"]))
                
                b1, b2 = st.columns(2)
                if b1.button("💾 Guardar Cambios"):
                    db.table("inventario").update({"nombre":en, "stock":es, "precio_detal":epd, "precio_mayor":epm, "min_mayor":emm}).eq("id", it["id"]).execute()
                    st.success("¡Actualizado!"); st.rerun()
                if b2.button("🗑️ Eliminar Producto"):
                    db.table("inventario").delete().eq("id", it["id"]).execute(); st.rerun()
        else: st.info("El inventario está vacío.")

    with t2:
        if autorizado:
            with st.form("form_nuevo"):
                st.subheader("Agregar Producto al Catálogo")
                n1, n2 = st.columns(2)
                nom_n = n1.text_input("Nombre (Ej: Caja Polar 36 un)")
                stk_n = n1.number_input("Stock Inicial", 0)
                pd_n = n2.number_input("Precio Detal $")
                pm_n = n2.number_input("Precio Mayor $")
                mm_n = n2.number_input("Mínimo Unidades para Mayor", 1)
                if st.form_submit_button("Registrar"):
                    db.table("inventario").insert({"nombre":nom_n,"stock":stk_n,"precio_detal":pd_n,"precio_mayor":pm_n,"min_mayor":mm_n}).execute()
                    st.success("Producto registrado"); st.rerun()
        else: st.warning("🔐 Ingrese clave para añadir productos.")

# --- 5. MÓDULO: VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busq_v = st.text_input("🔍 Buscar producto...").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(busq_v)] if busq_v else df_p
        
        if not df_v.empty:
            v1, v2 = st.columns([3, 1])
            psel = v1.selectbox("Elegir Item", df_v["nombre"])
            csel = v2.number_input("Cantidad", 1)
            item = df_p[df_p["nombre"] == psel].iloc[0]
            # Lógica automática Mayorista/Detal
            pf = float(item["precio_mayor"]) if csel >= item["min_mayor"] else float(item["precio_detal"])
            
            if st.button("➕ Añadir al Carrito"):
                if item["stock"] >= csel:
                    st.session_state.car.append({"p":psel, "c":csel, "u":pf, "t":pf*csel})
                    st.rerun()
                else: st.error("Stock insuficiente")

    if st.session_state.car:
        st.write("---")
        for i, it in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1])
            ca.info(f"**{it['p']}** | {it['c']} un x ${it['u']:.2f} = **${it['t']:.2f}**")
            if cb.button("❌", key=f"v_{i}"): st.session_state.car.pop(i); st.rerun()
