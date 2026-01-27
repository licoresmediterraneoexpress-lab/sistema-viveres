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
    pdf.ln(5)
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

# --- 4. MÓDULO: INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    if not df_inv.empty:
        costo_temp = df_inv['costo'] if 'costo' in df_inv.columns else 0
        df_inv['valor_inv'] = df_inv['stock'] * costo_temp
        st.metric("Inversión en Mercancía ($)", f"{df_inv['valor_inv'].sum():,.2f} USD")

    t1, t2 = st.tabs(["📋 Listado", "🆕 Nuevo"])
    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            cols = ["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]
            if 'costo' in df_inv.columns: cols.insert(2, "costo")
            st.dataframe(df_m[cols], use_container_width=True, hide_index=True)
            
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
                if st.button("💾 Guardar"):
                    db.table("inventario").update({"nombre":en, "stock":es, "costo":ec, "precio_detal":epd, "precio_mayor":epm, "min_mayor":emm}).eq("id", it["id"]).execute()
                    st.rerun()

    with t2:
        if clave == CLAVE_ADMIN:
            with st.form("nuevo_p"):
                f1, f2 = st.columns(2)
                n_nom = f1.text_input("Nombre")
                n_stk = f1.number_input("Stock Inicial", 0)
                n_cos = f2.number_input("Costo $")
                n_pdet = f2.number_input("Precio Detal $")
                n_pmay = f2.number_input("Precio Mayor $")
                n_mmay = f2.number_input("Cant. Mayorista", 1)
                if st.form_submit_button("Registrar"):
                    db.table("inventario").insert({"nombre":n_nom,"stock":n_stk,"costo":n_cos,"precio_detal":n_pdet,"precio_mayor":n_pmay,"min_mayor":n_mmay}).execute()
                    st.rerun()

# --- 5. VENTA RÁPIDA (CON PAGOS MIXTOS Y FACTURACIÓN) ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0, key="tasa_input")
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # Función de añadir (La que arreglamos)
        def añadir_al_carrito():
            p_nom = st.session_state.sel_prod_v
            cant_v = st.session_state.cant_prod_v
            item_db = df_p[df_p["nombre"] == p_nom].iloc[0]
            if item_db["stock"] >= cant_v:
                es_mayor = cant_v >= item_db["min_mayor"]
                precio_u = float(item_db["precio_mayor"]) if es_mayor else float(item_db["precio_detal"])
                st.session_state.car.append({
                    "p": p_nom, "c": int(cant_v), "u": precio_u, 
                    "t": precio_u * cant_v, "costo_u": float(item_db.get('costo', 0))
                })
                st.toast(f"✅ {p_nom} añadido")
            else: st.error("Sin stock suficiente")

        bus = st.text_input("🔍 Buscar producto...", key="bus_ventas").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(bus)] if bus else df_p
        
        if not df_v.empty:
            v1, v2 = st.columns([3, 1])
            psel = v1.selectbox("Producto", df_v["nombre"], key="sel_prod_v")
            csel = v2.number_input("Cant", min_value=1, value=1, key="cant_prod_v")
            st.button("➕ Añadir al Carrito", on_click=añadir_al_carrito, use_container_width=True)
        else: st.warning("No se encontraron productos.")

    # --- VISUALIZACIÓN DE CARRITO Y PAGOS ---
    if st.session_state.car:
        st.write("---")
        st.subheader("📋 Resumen de Compra")
        for i, x in enumerate(st.session_state.car):
            c_a, c_b = st.columns([9, 1])
            c_a.info(f"**{x['p']}** x{x['c']} = ${x['t']:.2f}")
            if c_b.button("❌", key=f"del_{i}"):
                st.session_state.car.pop(i)
                st.rerun()
        
        sub_u = sum(z['t'] for z in st.session_state.car)
        col_f1, col_f2 = st.columns(2)
        mon_f = col_f1.number_input("Monto Final Cobrado ($)", value=float(sub_u))
        pro_tot = mon_f - sub_u
        tot_b = mon_f * tasa
        
        st.markdown(f"### TOTAL A COBRAR: {tot_b:,.2f} Bs. / ${mon_f:,.2f}")
        
        # --- SECCIÓN DE PAGOS MIXTOS ---
        st.write("---")
        st.subheader("💳 Registro de Pago")
        p1, p2, p3 = st.columns(3)
        ef_b = p1.number_input("Efectivo Bs", 0.0); pm_b = p1.number_input("Pago Móvil Bs", 0.0)
        pu_b = p2.number_input("Punto Bs", 0.0); ot_b = p2.number_input("Otros Bs", 0.0)
        ze_u = p3.number_input("Zelle $", 0.0); di_u = p3.number_input("Divisas $", 0.0)
        
        pago_total_bs = ef_b + pm_b + pu_b + ot_b + ((ze_u + di_u) * tasa)
        
        if pago_total_bs >= tot_b - 0.1:
            vuelto = pago_total_bs - tot_b
            st.success(f"💰 Vuelto: {vuelto:,.2f} Bs.")
            
            if st.button("✅ FINALIZAR Y FACTURAR", use_container_width=True):
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto":x['p'], "cantidad":x['c'], "total_usd":x['t'], 
                        "costo_venta": x['costo_u'] * x['c'], 
                        "propina": pro_tot / len(st.session_state.car),
                        "p_efectivo": ef_b, "p_movil": pm_b, "p_punto": pu_b, "p_zelle": ze_u, "p_divisas": di_u,
                        "fecha":datetime.now().isoformat()
                    }).execute()
                    # Actualizar Stock
                    s_act = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock']) - x['c']
                    db.table("inventario").update({"stock": s_act}).eq("nombre", x['p']).execute()
                
                # Generar PDF
                st.session_state.pdf_b = crear_ticket(st.session_state.car, tot_b, sub_u, tasa, pro_tot)
                st.session_state.car = []
                st.rerun()

    if st.session_state.pdf_b:
        st.download_button("📥 Descargar Último Ticket (PDF)", st.session_state.pdf_b, "factura.pdf", mime="application/pdf")
# --- 6. GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("gas"):
        d = st.text_input("Descripción"); m = st.number_input("Monto $")
        if st.form_submit_button("Guardar"):
            db.table("gastos").insert({"descripcion":d, "monto":m, "fecha":datetime.now().isoformat()}).execute()
            st.success("Gasto anotado")

# --- 7. REPORTE DE UTILIDADES ---
elif opcion == "📊 Reporte de Utilidades":
    st.header("📊 Resultado del Negocio")
    
    # Barra lateral para borrado
    clave_r = st.sidebar.text_input("Clave Admin para borrar", type="password")
    if clave_r == CLAVE_ADMIN:
        if st.sidebar.button("🚨 VACIAR TODAS LAS VENTAS"):
            db.table("ventas").delete().neq("id", 0).execute()
            st.sidebar.success("Historial eliminado.")
            st.rerun()

    f_f = st.date_input("Fecha", date.today())
    v






