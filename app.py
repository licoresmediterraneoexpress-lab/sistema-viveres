import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS Expert", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold;}
    .stMetric {background: #F0F7FF; padding: 10px; border-radius: 10px; border-left: 5px solid #0041C2;}
    .propina-box { background-color: #D4EDDA; padding: 10px; border-radius: 5px; color: #155724; font-weight: bold; border: 1px solid #c3e6cb; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES ---
def crear_ticket(carrito, total_bs, total_usd, tasa, propina_usd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "P. Unit $", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 11)
    if propina_usd > 0:
        pdf.cell(190, 7, f"RECARGO / SERVICIO: ${propina_usd:.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {(total_usd + propina_usd):,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MENÚ ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Reporte de Ganancias"])
    st.markdown("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. MÓDULO: INVENTARIO (CON COSTOS) ---
if opcion == "📦 Inventario":
    st.header("📦 Inventario y Valor de Mercancía")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    autorizado = (clave == CLAVE_ADMIN)

    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    if not df_inv.empty:
        # Cálculo de Valor de Inventario
        # Nota: Asegúrate de tener la columna 'costo' en Supabase. Si no, el sistema la creará como 0 por defecto.
        if 'costo' not in df_inv.columns: df_inv['costo'] = 0.0
        df_inv['valor_total'] = df_inv['stock'] * df_inv['costo']
        valor_mercancia = df_inv['valor_total'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Valor Total Mercancía ($)", f"{valor_mercancia:,.2f} USD")
        c2.metric("Items en Stock", f"{df_inv['stock'].sum()}")

    t1, t2 = st.tabs(["📋 Listado", "🆕 Nuevo Producto"])
    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            st.dataframe(df_m[["nombre", "stock", "costo", "precio_detal", "precio_mayor"]], use_container_width=True, hide_index=True)
            
            if autorizado:
                st.write("---")
                sel = st.selectbox("Editar", df_inv["nombre"])
                it = df_inv[df_inv["nombre"] == sel].iloc[0]
                c1, c2, c3 = st.columns(3)
                en = c1.text_input("Nombre", it["nombre"])
                es = c1.number_input("Stock", value=int(it["stock"]))
                ec = c2.number_input("Costo Compra $", value=float(it.get('costo', 0)))
                epd = c2.number_input("Precio Detal $", value=float(it["precio_detal"]))
                epm = c3.number_input("Precio Mayor $", value=float(it["precio_mayor"]))
                if st.button("💾 Actualizar"):
                    db.table("inventario").update({"nombre":en, "stock":es, "costo":ec, "precio_detal":epd, "precio_mayor":epm}).eq("id", it["id"]).execute()
                    st.rerun()
    with t2:
        if autorizado:
            with st.form("n"):
                f1, f2 = st.columns(2)
                nom = f1.text_input("Nombre")
                stk = f1.number_input("Stock", 0)
                cos = f2.number_input("Costo $")
                pdet = f2.number_input("Precio Detal $")
                pmay = f2.number_input("Precio Mayor $")
                mmay = f2.number_input("Mín. Mayor", 1)
                if st.form_submit_button("Guardar"):
                    db.table("inventario").insert({"nombre":nom,"stock":stk,"costo":cos,"precio_detal":pdet,"precio_mayor":pmay,"min_mayor":mmay}).execute()
                    st.rerun()

# --- 5. MÓDULO: VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Ventas")
    tasa = st.number_input("Tasa Bs/$", 1.0, 1000.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        bus = st.text_input("🔍 Buscar...").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(bus)] if bus else df_p
        v1, v2 = st.columns([3, 1])
        psel = v1.selectbox("Producto", df_v["nombre"])
        csel = v2.number_input("Cant", 1)
        it = df_p[df_p["nombre"] == psel].iloc[0]
        pf = float(it["precio_mayor"]) if csel >= it["min_mayor"] else float(it["precio_detal"])
        
        if st.button("➕ Añadir"):
            if it["stock"] >= csel:
                # Guardamos el costo en el momento de la venta para calcular utilidad exacta luego
                st.session_state.car.append({"p":psel, "c":csel, "u":pf, "t":pf*csel, "costo_u": float(it.get('costo', 0))})
                st.rerun()
            else: st.error("Sin Stock")

    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            st.info(f"{x['p']} x{x['c']} = ${x['t']:.2f}")
        
        sub_u = sum(z['t'] for z in st.session_state.car)
        mon_f = st.number_input("Monto Final $", value=float(sub_u))
        pro = mon_f - sub_u
        tot_b = mon_f * tasa
        st.markdown(f"## TOTAL: {tot_b:,.2f} Bs.")
        
        if st.button("✅ FINALIZAR"):
            for x in st.session_state.car:
                db.table("ventas").insert({
                    "producto":x['p'], "cantidad":x['c'], "total_usd":x['t'], 
                    "costo_venta": x['costo_u'] * x['c'], # REGISTRO DE COSTO
                    "propina": pro / len(st.session_state.car), "fecha":datetime.now().isoformat()
                }).execute()
                stk_n = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock']) - x['c']
                db.table("inventario").update({"stock": stk_n}).eq("nombre", x['p']).execute()
            st.session_state.pdf_b = crear_ticket(st.session_state.car, tot_b, sub_u, tasa, pro)
            st.session_state.car = []; st.rerun()
    if st.session_state.pdf_b: st.download_button("📥 Ticket", st.session_state.pdf_b, "ticket.pdf")

# --- 6. MÓDULO: GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Registro de Gastos Operativos")
    with st.form("g"):
        desc = st.text_input("Descripción del Gasto (Hielo, Luz, Sueldo, etc.)")
        monto_g = st.number_input("Monto USD", 0.0)
        if st.form_submit_button("Registrar Gasto"):
            db.table("gastos").insert({"descripcion":desc, "monto":monto_g, "fecha":datetime.now().isoformat()}).execute()
            st.success("Gasto guardado")

# --- 7. MÓDULO: REPORTE DE GANANCIAS ---
elif opcion == "📊 Reporte de Ganancias":
    st.header("📊 Utilidades y Cierre")
    f = st.date_input("Fecha", date.today())
    
    # Obtener Ventas y Gastos
    v_res = db.table("ventas").select("*").gte("fecha", f.isoformat()).execute()
    g_res = db.table("gastos").select("*").gte("fecha", f.isoformat()).execute()
    
    if v_res.data:
        df_v = pd.DataFrame(v_res.data)
        df_g = pd.DataFrame(g_res.data) if g_res.data else pd.DataFrame(columns=['monto'])
        
        # Asegurar columnas
        for col in ['total_usd', 'costo_venta', 'propina']:
            if col not in df_v.columns: df_v[col] = 0.0
        
        v_netas = df_v['total_usd'].sum()
        costo_total = df_v['costo_venta'].sum()
        total_propinas = df_v['propina'].sum()
        total_gastos = df_g['monto'].sum() if not df_g.empty else 0.0
        
        # CALCULOS CLAVE
        ganancia_bruta = v_netas - costo_total
        ganancia_neta = ganancia_bruta + total_propinas - total_gastos
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas Netas ($)", f"{v_netas:,.2f}")
        c1.caption("Total de productos vendidos")
        
        c2.metric("Ganancia Bruta ($)", f"{ganancia_bruta:,.2f}", delta="Venta - Costo")
        c2.caption("Dinero real tras reponer mercancía")
        
        c3.metric("Gastos ($)", f"-{total_gastos:,.2f}", delta_color="inverse")
        c3.caption("Hielo, servicios, etc.")
        
        # EL DATO MÁS IMPORTANTE
        st.write("---")
        st.metric("💰 GANANCIA NETA FINAL ($)", f"{ganancia_neta:,.2f}", delta="Dinero libre para ti")
        
        with st.expander("Ver Detalles del día"):
            st.write("**Ventas:**")
            st.dataframe(df_v[['producto', 'cantidad', 'total_usd', 'propina']], use_container_width=True)
            st.write("**Gastos:**")
            st.dataframe(df_g, use_container_width=True)
    else: st.info("Sin datos para esta fecha.")
