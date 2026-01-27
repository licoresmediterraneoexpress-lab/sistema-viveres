import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS Premium", layout="wide")

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
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold; width: 100%;}
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
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Reporte de Utilidades"])
    st.markdown("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. MÓDULO: INVENTARIO (COMPLETO) ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión Integral de Stock")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    if not df_inv.empty:
        df_inv['valor_inv'] = df_inv['stock'] * df_inv.get('costo', 0)
        st.metric("Inversión Total en Mercancía ($)", f"{df_inv['valor_inv'].sum():,.2f} USD")

    t1, t2 = st.tabs(["📋 Listado y Edición", "🆕 Nuevo Producto"])
    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            st.dataframe(df_m[["nombre", "stock", "costo", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True, hide_index=True)
            
            if clave == CLAVE_ADMIN:
                st.write("---")
                sel = st.selectbox("Editar Item", df_inv["nombre"])
                it = df_inv[df_inv["nombre"] == sel].iloc[0]
                c1, c2, c3 = st.columns(3)
                en = c1.text_input("Nombre", it["nombre"])
                es = c1.number_input("Stock", value=int(it["stock"]))
                ec = c2.number_input("Costo Compra $", value=float(it.get('costo', 0)))
                epd = c2.number_input("Precio Detal $", value=float(it["precio_detal"]))
                epm = c3.number_input("Precio Mayor $", value=float(it["precio_mayor"]))
                emm = c3.number_input("Mínimo Mayorista", value=int(it["min_mayor"]))
                if st.button("💾 Guardar Cambios"):
                    db.table("inventario").update({"nombre":en, "stock":es, "costo":ec, "precio_detal":epd, "precio_mayor":epm, "min_mayor":emm}).eq("id", it["id"]).execute()
                    st.rerun()
    with t2:
        if clave == CLAVE_ADMIN:
            with st.form("nuevo_p"):
                f1, f2 = st.columns(2)
                n_nom = f1.text_input("Nombre del Producto")
                n_stk = f1.number_input("Stock Inicial", 0)
                n_cos = f2.number_input("Costo de Compra $")
                n_pdet = f2.number_input("Precio Detal $")
                n_pmay = f2.number_input("Precio Mayor $")
                n_mmay = f2.number_input("Cant. para Mayorista", 1)
                if st.form_submit_button("Registrar Producto"):
                    db.table("inventario").insert({"nombre":n_nom,"stock":n_stk,"costo":n_cos,"precio_detal":n_pdet,"precio_mayor":n_pmay,"min_mayor":n_mmay}).execute()
                    st.rerun()

# --- 5. MÓDULO: VENTA RÁPIDA (PAGOS MIXTOS + MAYORISTA) ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        bus = st.text_input("🔍 Buscar producto...").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(bus)] if bus else df_p
        v1, v2 = st.columns([3, 1])
        psel = v1.selectbox("Producto", df_v["nombre"])
        csel = v2.number_input("Cantidad", 1)
        it = df_p[df_p["nombre"] == psel].iloc[0]
        
        # Lógica Mayorista
        precio_v = float(it["precio_mayor"]) if csel >= it["min_mayor"] else float(it["precio_detal"])
        
        if st.button("➕ Añadir al Carrito"):
            if it["stock"] >= csel:
                st.session_state.car.append({
                    "p":psel, "c":csel, "u":precio_v, "t":precio_v*csel, 
                    "costo_u": float(it.get('costo', 0))
                })
                st.rerun()
            else: st.error("Stock insuficiente")

    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1])
            ca.info(f"**{x['p']}** x{x['c']} = ${x['t']:.2f}")
            if cb.button("❌", key=f"del_{i}"): st.session_state.car.pop(i); st.rerun()
        
        sub_total = sum(z['t'] for z in st.session_state.car)
        monto_final_u = st.number_input("Ajustar Monto Final ($)", value=float(sub_total))
        ajuste_propina = monto_final_u - sub_total
        total_bs = monto_final_u * tasa
        
        st.markdown(f"### TOTAL A PAGAR: {total_bs:,.2f} Bs. / ${monto_final_u:,.2f}")
        
        # Pagos Mixtos
        st.subheader("💳 Formas de Pago")
        p1, p2, p3 = st.columns(3)
        ef_b = p1.number_input("Efectivo Bs", 0.0); pm_b = p1.number_input("Pago Móvil Bs", 0.0)
        pu_b = p2.number_input("Punto Bs", 0.0); ot_b = p2.number_input("Otros Bs", 0.0)
        ze_u = p3.number_input("Zelle $", 0.0); di_u = p3.number_input("Divisas $", 0.0)
        
        total_pagado_bs = ef_b + pm_b + pu_b + ot_b + ((ze_u + di_u) * tasa)
        
        if total_pagado_bs >= total_bs - 0.1:
            st.success(f"Vuelto: {total_pagado_bs - total_bs:,.2f} Bs.")
            if st.button("✅ PROCESAR VENTA"):
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto":x['p'], "cantidad":x['c'], "total_usd":x['t'], 
                        "costo_venta": x['costo_u'] * x['c'], 
                        "propina": ajuste_propina / len(st.session_state.car),
                        "p_efectivo": ef_b, "p_movil": pm_b, "p_punto": pu_b, "p_zelle": ze_u, "p_divisas": di_u,
                        "fecha":datetime.now().isoformat()
                    }).execute()
                    stk_act = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock']) - x['c']
                    db.table("inventario").update({"stock": stk_act}).eq("nombre", x['p']).execute()
                st.session_state.pdf_b = crear_ticket(st.session_state.car, total_bs, sub_total, tasa, ajuste_propina)
                st.session_state.car = []; st.rerun()
    if st.session_state.pdf_b: st.download_button("📥 Descargar Ticket PDF", st.session_state.pdf_b, "ticket.pdf")

# --- 6. MÓDULO: GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos del Negocio")
    with st.form("gas"):
        d_g = st.text_input("Motivo del Gasto")
        m_g = st.number_input("Monto en USD", 0.0)
        if st.form_submit_button("Registrar"):
            db.table("gastos").insert({"descripcion":d_g, "monto":m_g, "fecha":datetime.now().isoformat()}).execute()
            st.success("Gasto guardado")

# --- 7. MÓDULO: UTILIDADES (REPORTE EXCEL INCLUIDO) ---
elif opcion == "📊 Reporte de Utilidades":
    st.header("📊 Resultado Financiero")
    f_rep = st.date_input("Fecha", date.today())
    v_res = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g_res = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v_res.data:
        df_v = pd.DataFrame(v_res.data)
        df_g = pd.DataFrame(g_res.data) if g_res.data else pd.DataFrame(columns=['monto'])
        
        # Totales
        v_brutas = df_v['total_usd'].sum()
        costos = df_v['costo_venta'].sum()
        propinas = df_v['propina'].sum()
        gastos_tot = df_g['monto'].sum() if not df_g.empty else 0
        
        utilidad_bruta = v_brutas - costos
        utilidad_neta = utilidad_bruta + propinas - gastos_tot
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas ($)", f"{v_brutas:,.2f}")
        c2.metric("Utilidad Bruta ($)", f"{utilidad_bruta:,.2f}")
        c3.metric("Gastos ($)", f"{gastos_tot:,.2f}")
        c4.metric("GANANCIA NETA ($)", f"{utilidad_neta:,.2f}")
        
        st.write("---")
        st.subheader("📝 Libro de Ventas")
        df_v['Total Final $'] = df_v['total_usd'] + df_v['propina']
        st.dataframe(df_v[['producto', 'cantidad', 'total_usd', 'propina', 'Total Final $']], use_container_width=True, hide_index=True)
        
        # Exportar Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as w: df_v.to_excel(w, index=False)
        st.download_button("📥 Descargar Reporte Excel", buf.getvalue(), f"Cierre_{f_rep}.xlsx")
    else: st.info("Sin movimientos hoy.")
