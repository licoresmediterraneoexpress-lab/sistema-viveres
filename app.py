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
CLAVE_ADMIN = "1234" # <--- Puedes cambiar tu clave aquí

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

st.markdown("<style>.stApp{background:white;} [data-testid='stSidebar']{background:#0041C2;} .stButton>button{background:#FF8C00;color:white;border-radius:10px;font-weight:bold;}</style>", unsafe_allow_html=True)

# --- FUNCIÓN TICKET ---
def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "Precio $", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    m = st.radio("MENÚ", ["📦 Stock", "🛒 Venta", "📊 Total"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 1. STOCK (CON EDICIÓN Y SEGURIDAD) ---
if m == "📦 Stock":
    st.header("📦 Control de Inventario")
    
    # Bloque de Seguridad
    admin_pass = st.sidebar.text_input("Clave Admin", type="password")
    es_admin = admin_pass == CLAVE_ADMIN

    with st.expander("➕ Nuevo Producto"):
        if es_admin:
            with st.form("f1", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n, s = c1.text_input("Nombre"), c1.number_input("Stock", 0)
                pd_v, pm_v, mm = c2.number_input("Precio Detal ($)"), c2.number_input("Precio Mayor ($)"), c2.number_input("Min. Mayor", 1)
                if st.form_submit_button("Guardar"):
                    db.table("inventario").insert({"nombre":n,"stock":s,"precio_detal":pd_v,"precio_mayor":pm_v,"min_mayor":mm}).execute()
                    st.success("Guardado"); st.rerun()
        else: st.warning("🔐 Ingrese clave en el menú lateral para agregar productos.")

    res = db.table("inventario").select("*").execute()
    if res.data:
        df_inv = pd.DataFrame(res.data)
        st.subheader("📋 Lista de Productos")
        st.dataframe(df_inv[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

        if es_admin:
            st.markdown("---")
            st.subheader("🛠️ Modificar o Eliminar")
            sel_p = st.selectbox("Seleccione producto para editar", df_inv["nombre"])
            it_edit = df_inv[df_inv["nombre"] == sel_p].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            edit_n = col1.text_input("Nombre", it_edit["nombre"])
            edit_s = col1.number_input("Stock", value=int(it_edit["stock"]))
            edit_pd = col2.number_input("Precio Detal $", value=float(it_edit["precio_detal"]))
            edit_pm = col2.number_input("Precio Mayor $", value=float(it_edit["precio_mayor"]))
            edit_mm = col3.number_input("Min. Mayor", value=int(it_edit["min_mayor"]))

            b1, b2 = st.columns(2)
            if b1.button("💾 Guardar Cambios"):
                db.table("inventario").update({"nombre":edit_n, "stock":edit_s, "precio_detal":edit_pd, "precio_mayor":edit_pm, "min_mayor":edit_mm}).eq("id", it_edit["id"]).execute()
                st.success("Actualizado"); st.rerun()
            if b2.button("🗑️ Borrar Producto"):
                db.table("inventario").delete().eq("id", it_edit["id"]).execute()
                st.error("Eliminado"); st.rerun()

# --- 2. VENTA (BUSCADOR INTELIGENTE) ---
elif m == "🛒 Venta":
    st.header("🛒 Ventas")
    t = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busq = st.text_input("🔍 Buscar (ej: 'cer', 'arr', 'pan')...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busq)] if busq else df_p
        
        if not df_f.empty:
            c1, c2 = st.columns([3, 1])
            sel = c1.selectbox("Producto", df_f["nombre"])
            can = c2.number_input("Cant", 1)
            it = df_p[df_p["nombre"] == sel].iloc[0]
            pre = float(it["precio_mayor"]) if can >= it["min_mayor"] else float(it["precio_detal"])
            if st.button("➕ Añadir"):
                if it["stock"] >= can:
                    st.session_state.car.append({"p":sel, "c":can, "u":pre, "t":pre*can}); st.rerun()
                else: st.error("Stock insuficiente")
    
    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1])
            ca.info(f"**{x['p']}** | {x['c']} x ${x['u']:.2f} = ${x['t']:.2f}")
            if cb.button("❌", key=f"del_{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        tu, tb = sum(z['t'] for z in st.session_state.car), sum(z['t'] for z in st.session_state.car) * t
        st.markdown(f"### Total: **Bs. {tb:,.2f}** (${tu:,.2f})")
        
        c1, c2, c3 = st.columns(3)
        e_b = c1.number_input("Efectivo Bs", 0.0); pm_b = c1.number_input("Pago Móvil Bs", 0.0)
        p_b = c2.number_input("Punto Bs", 0.0); ot_b = c2.number_input("Otros Bs", 0.0)
        z_u = c3.number_input("Zelle $", 0.0); d_u = c3.number_input("Divisas $", 0.0)
        
        pag = e_b + pm_b + p_b + ot_b + ((z_u + d_u) * t)
        if pag >= tb - 0.1:
            st.success(f"Vuelto: {pag-tb:,.2f} Bs.")
            if st.button("✅ FINALIZAR"):
                try:
                    for v in st.session_state.car:
                        db.table("ventas").insert({"producto":v['p'],"cantidad":v['c'],"total_usd":v['t'],"tasa_cambio":t,"p_efectivo":e_b,"p_movil":pm_b,"p_punto":p_b,"p_zelle":z_u,"p_divisas":d_u,"fecha":datetime.now().isoformat()}).execute()
                        stk_a = int(df_p[df_p["nombre"] == v['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_a - v['c']}).eq("nombre", v['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, tb, tu, t)
                    st.session_state.car = []; st.success("Venta Ok"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    if st.session_state.pdf_b: st.download_button("📥 Ticket PDF", st.session_state.pdf_b, "ticket.pdf")

# --- 3. TOTAL (CORRECCIÓN KEYERROR) ---
elif m == "📊 Total":
    st.header("📊 Reporte de Ventas")
    f = st.date_input("Fecha", date.today())
    try:
        res_v = db.table("ventas").select("*").gte("fecha", f.isoformat()).execute()
        if res_v.data:
            df_v = pd.DataFrame(res_v.data)
            # Asegurar columnas para evitar errores de cuadre
            for col in ['p_efectivo', 'p_movil', 'p_punto', 'p_zelle', 'p_divisas', 'total_usd']:
                if col not in df_v.columns: df_v[col] = 0.0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Efectivo Bs", f"{df_v['p_efectivo'].sum():,.2f}")
            c1.metric("Pago Móvil Bs", f"{df_v['p_movil'].sum():,.2f}")
            c2.metric("Punto/Otros Bs", f"{df_v['p_punto'].sum():,.2f}")
            c2.metric("Dólares/Zelle $", f"{(df_v['p_zelle'].sum() + df_v['p_divisas'].sum()):,.2f}")
            c3.metric("VENTA TOTAL $", f"{df_v['total_usd'].sum():,.2f}")
            st.dataframe(df_v, use_container_width=True)
        else: st.info("No hay ventas hoy.")
    except Exception as e: st.error(f"Error: {e}")
