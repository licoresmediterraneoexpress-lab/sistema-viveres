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
def init_db(): return create_client(URL, KEY)
db = init_db()

if 'car' not in st.session_state: st.session_state.car = []

st.markdown("""
<style>
    .stApp {background-color: white;}
    [data-testid="stSidebar"] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 10px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, "Producto"); pdf.cell(30, 8, "Cant."); pdf.cell(40, 8, "P. Unit ($)"); pdf.cell(40, 8, "Subtotal ($)", ln=True)
    pdf.set_font("Arial", '', 10)
    for i in carrito:
        pdf.cell(80, 8, str(i['p'])); pdf.cell(30, 8, str(i['c'])); pdf.cell(40, 8, f"{i['u']:.2f}"); pdf.cell(40, 8, f"{i['t']:.2f}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 10, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("", ["📦 Inventario", "🛒 Punto de Venta", "📊 Reportes y Cierre"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 1. INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Inventario")
    with st.expander("➕ Nuevo Producto"):
        with st.form("f_inv", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre")
            stk = c1.number_input("Stock", min_value=0)
            p_d = c2.number_input("Precio Detal ($)", min_value=0.0)
            p_m = c2.number_input("Precio Mayor ($)", min_value=0.0)
            m_m = c2.number_input("Min. Mayor", min_value=1)
            if st.form_submit_button("Guardar"):
                db.table("inventario").insert({"nombre":nom,"stock":stk,"precio_detal":p_d,"precio_mayor":p_m,"min_mayor":m_m}).execute()
                st.success("Guardado"); st.rerun()
    res = db.table("inventario").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data)[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

# --- 2. PUNTO DE VENTA (CON BUSQUEDA INTELIGENTE) ---
elif opcion == "🛒 Punto de Venta":
    st.header("🛒 Punto de Venta")
    tasa = st.number_input("Tasa del día (Bs/$)", min_value=1.0, value=60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # BUSCADOR INTELIGENTE
        busqueda = st.text_input("🔍 Buscar producto por nombre...")
        if busqueda:
            df_filtrado = df_p[df_p['nombre'].str.contains(busqueda, case=False)]
        else:
            df_filtrado = df_p
            
        if not df_filtrado.empty:
            c1, c2 = st.columns([3, 1])
            prod_sel = c1.selectbox("Seleccione el producto filtrado", df_filtrado["nombre"])
            cant_sel = c2.number_input("Cantidad", min_value=1)
            
            dat = df_p[df_p["nombre"] == prod_sel].iloc[0]
            pre = float(dat["precio_mayor"]) if cant_sel >= dat["min_mayor"] else float(dat["precio_detal"])
            
            if st.button("➕ Añadir al Carrito"):
                if dat["stock"] >= cant_sel:
                    st.session_state.car.append({"p": prod_sel, "c": cant_sel, "u": pre, "t": pre * cant_sel})
                    st.rerun()
                else: st.error("Stock insuficiente.")
        else: st.warning("No se encontraron productos.")

    if st.session_state.car:
        st.write("---")
        for i, it in enumerate(st.session_state.car):
            ca, cb = st.columns([8, 1])
            ca.info(f"**{it['p']}** | {it['c']} x ${it['u']:.2f} = ${it['t']:.2f}")
            if cb.button("❌", key=f"d_{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        total_u, total_b = sum(x['t'] for x in st.session_state.car), sum(x['t'] for x in st.session_state.car) * tasa
        st.markdown(f"## Total: **Bs. {total_b:,.2f}** (${total_u:,.2f})")
        
        col1, col2, col3 = st.columns(3)
        ef_b = col1.number_input("Efectivo Bs", 0.0); pm_b = col1.number_input("Pago Móvil Bs", 0.0)
        pu_b = col2.number_input("Punto Bs", 0.0); ot_b = col2.number_input("Otros Bs", 0.0)
        ze_u = col3.number_input("Zelle $", 0.0); di_u = col3.number_input("Divisas $", 0.0)
        
        pag_b = ef_b + pm_b + pu_b + ot_b + ((ze_u + di_u) * tasa)
        vuelto = pag_b - total_b
        
        if pag_b < total_b - 0.1: st.warning(f"Faltan: Bs. {abs(vuelto):,.2f}")
        else:
            st.success(f"Vuelto: Bs. {vuelto:,.2f}")
            if st.button("✅ FINALIZAR"):
                try:
                    for v in st.session_state.car:
                        db.table("ventas").insert({"producto": v['p'], "cantidad": v['c'], "total_usd": v['t'], "tasa_cambio": tasa, "p_efectivo": ef_b, "p_movil": pm_b, "p_punto": pu_b, "p_zelle": ze_u, "p_divisas": di_u, "fecha": datetime.now().isoformat()}).execute()
                        s_act = int(df_p[df_p["nombre"] == v['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": s_act - v['c']}).eq("nombre", v['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, total_b, total_u, tasa)
                    st.session_state.car = []; st.success("Venta procesada."); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        if 'pdf_b' in st.session_state: st.download_button("📥 Descargar Ticket", st.session_state.pdf_b, "ticket.pdf")

# --- 3. REPORTES Y CIERRE DE CAJA ---
elif opcion == "📊 Reportes y Cierre":
    st.header("📊 Reportes y Cierre de Caja")
    fecha_cierre = st.date_input("Seleccione fecha para el cierre", date.today())
    
    res_v = db.table("ventas").select("*").gte("fecha", fecha_cierre.isoformat()).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        
        # CIERRE DE CAJA
        st.subheader(f"💵 Cierre de Caja - {fecha_cierre}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo Bs", f"{df_v['p_efectivo'].sum():,.2f}")
        c1.metric("Pago Móvil Bs", f"{df_v['p_movil'].sum():,.2f}")
        c2.metric("Punto Bs", f"{df_v['p_punto'].sum():,.2f}")
        c2.metric("Zelle $", f"{df_v['p_zelle'].sum():,.2f}")
        c3.metric("Divisas $", f"{df_v['p_divisas'].sum():,.2f}")
        c3.metric("Ventas Totales ($)", f"{df_v['total_usd'].sum():,.2f}")
        
        st.write("---")
        st.subheader("Detalle de Transacciones")
        st.dataframe(df_v, use_container_width=True)
        
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_v.to_excel(wr, index=False)
        st.download_button("📥 Exportar Reporte Excel", out.getvalue(), "reporte.xlsx")
    else: st.info("No hay ventas en esta fecha.")
