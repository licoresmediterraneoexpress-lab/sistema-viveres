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
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {(total_usd + propina_usd):,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MENÚ ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Reporte"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    if not df_inv.empty:
        df_inv['valor_inv'] = df_inv['stock'] * df_inv.get('costo', 0)
        st.metric("Inversión en Mercancía ($)", f"{df_inv['valor_inv'].sum():,.2f} USD")

    t1, t2 = st.tabs(["📋 Listado", "🆕 Nuevo"])
    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            st.dataframe(df_m[["nombre", "stock", "costo", "precio_detal", "precio_mayor"]], use_container_width=True, hide_index=True)
            
            if clave == CLAVE_ADMIN:
                sel = st.selectbox("Editar Item", df_inv["nombre"])
                it = df_inv[df_inv["nombre"] == sel].iloc[0]
                with st.form("edit_f"):
                    en = st.text_input("Nombre", it["nombre"])
                    es = st.number_input("Stock", value=int(it["stock"]))
                    ec = st.number_input("Costo", value=float(it.get('costo', 0)))
                    if st.form_submit_button("Actualizar"):
                        db.table("inventario").update({"nombre":en, "stock":es, "costo":ec}).eq("id", it["id"]).execute()
                        st.rerun()

    with t2:
        if clave == CLAVE_ADMIN:
            with st.form("nuevo_p"):
                n_nom = st.text_input("Nombre")
                n_stk = st.number_input("Stock Inicial", 0)
                n_cos = st.number_input("Costo $")
                n_pdet = st.number_input("Precio Detal $")
                if st.form_submit_button("Registrar"):
                    db.table("inventario").insert({"nombre":n_nom,"stock":n_stk,"costo":n_cos,"precio_detal":n_pdet,"precio_mayor":n_pdet,"min_mayor":12}).execute()
                    st.rerun()

# --- 5. VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        def add_car():
            p = df_p[df_p["nombre"] == st.session_state.ps].iloc[0]
            if p["stock"] >= st.session_state.cs:
                precio = float(p["precio_mayor"]) if st.session_state.cs >= p["min_mayor"] else float(p["precio_detal"])
                st.session_state.car.append({"p": p["nombre"], "c": st.session_state.cs, "u": precio, "t": round(precio * st.session_state.cs, 2), "costo_u": float(p.get('costo', 0))})
                st.toast("Añadido")
        
        c1, c2 = st.columns([3,1])
        c1.selectbox("Producto", df_p["nombre"], key="ps")
        c2.number_input("Cant", 1, key="cs")
        st.button("➕ Añadir", on_click=add_car)

    if st.session_state.car:
        st.write("---")
        sub_total_usd = sum(x['t'] for x in st.session_state.car)
        st.write(f"Total sugerido: **{sub_total_usd * tasa:,.2f} Bs.**")
        total_bs = st.number_input("A cobrar (Bs.)", value=float(sub_total_usd * tasa))
        total_usd_final = round(total_bs / tasa, 2)
        
        p1, p2, p3 = st.columns(3)
        ef = p1.number_input("Efec. Bs", 0.0); pm = p1.number_input("P. Móvil Bs", 0.0)
        pu = p2.number_input("Punto Bs", 0.0); ot = p2.number_input("Otros Bs", 0.0)
        ze = p3.number_input("Zelle $", 0.0); di = p3.number_input("Divisas $", 0.0)
        
        pagado_bs = ef + pm + pu + ot + ((ze + di) * tasa)
        st.write(f"Diferencia: {total_bs - pagado_bs:,.2f} Bs.")

        if st.button("✅ FINALIZAR"):
            try:
                st.session_state.pdf_b = crear_ticket(st.session_state.car, total_bs, sub_total_usd, tasa, total_usd_final - sub_total_usd)
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, "pago_otros": ot, "pago_divisas": di,
                        "costo_venta": x['costo_u'] * x['c'], "fecha": datetime.now().isoformat()
                    }).execute()
                    n_stk = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock']) - x['c']
                    db.table("inventario").update({"stock": n_stk}).eq("nombre", x['p']).execute()
                st.session_state.car = []
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    if st.session_state.pdf_b:
        st.download_button("📥 Descargar Ticket", st.session_state.pdf_b, "ticket.pdf", "application/pdf")

# --- 6. GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("gas"):
        d = st.text_input("Descripción"); m = st.number_input("Monto $")
        if st.form_submit_button("Guardar"):
            db.table("gastos").insert({"descripcion":d, "monto_usd":m, "fecha":datetime.now().isoformat()}).execute()
            st.success("Gasto anotado")

# --- 7. REPORTE ---
elif opcion == "📊 Reporte":
    st.header("📊 Reporte de Ventas")
    f = st.date_input("Fecha", date.today())
    res = db.table("ventas").select("*").gte("fecha", f.isoformat()).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("Ventas del Día", f"${df['total_usd'].sum():,.2f}")
        st.dataframe(df)
