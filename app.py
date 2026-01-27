import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import time, io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mediterraneo POS", layout="wide")

# Credenciales Supabase
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# Inicializar Carrito
if 'car' not in st.session_state:
    st.session_state.car = []

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .stApp {background-color: white;}
    [data-testid="stSidebar"] {background-color: #0041C2;}
    .stButton>button {
        background-color: #FF8C00;
        color: white;
        border-radius: 10px;
        font-weight: bold;
        width: 100%;
    }
    .stInfo { background-color: #f0f2f6; border-left: 5px solid #0041C2; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN TICKET PDF ---
def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, "Producto")
    pdf.cell(30, 8, "Cant.")
    pdf.cell(40, 8, "P. Unit ($)")
    pdf.cell(40, 8, "Subtotal ($)", ln=True)
    
    pdf.set_font("Arial", '', 10)
    for i in carrito:
        pdf.cell(80, 8, str(i['p']))
        pdf.cell(30, 8, str(i['c']))
        pdf.cell(40, 8, f"{i['u']:.2f}")
        pdf.cell(40, 8, f"{i['t']:.2f}", ln=True)
    
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 10, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(190, 10, f"Tasa de cambio: {tasa} Bs/$", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:white;text-align:center;'>MENÚ</h1>", unsafe_allow_html=True)
    opcion = st.radio("", ["📦 Inventario", "🛒 Punto de Venta", "📊 Reportes"])
    st.write("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []
        st.rerun()

# --- 1. INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    
    with st.expander("➕ Registrar Nuevo Producto"):
        with st.form("form_inv", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre del Producto")
            stock = col1.number_input("Existencia Inicial", min_value=0, step=1)
            p_detal = col2.number_input("Precio Detal ($)", min_value=0.0)
            p_mayor = col2.number_input("Precio Mayor ($)", min_value=0.0)
            min_mayor = col2.number_input("Cantidad para Mayor", min_value=1, step=1)
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    db.table("inventario").insert({
                        "nombre": nombre, "stock": stock, 
                        "precio_detal": p_detal, "precio_mayor": p_mayor, 
                        "min_mayor": min_mayor
                    }).execute()
                    st.success("Producto guardado.")
                    st.rerun()
                else: st.error("El nombre es obligatorio.")

    st.subheader("Listado de Productos")
    res = db.table("inventario").select("*").execute()
    if res.data:
        df_inv = pd.DataFrame(res.data)
        st.dataframe(df_inv[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True)

# --- 2. PUNTO DE VENTA ---
elif opcion == "🛒 Punto de Venta":
    st.header("🛒 Punto de Venta")
    tasa = st.number_input("Tasa del día (Bs/$)", min_value=1.0, value=60.0, step=0.1)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        col_a, col_b = st.columns([3, 1])
        prod_sel = col_a.selectbox("Seleccione Producto", df_p["nombre"])
        cant_sel = col_b.number_input("Cant.", min_value=1, step=1)
        
        datos_p = df_p[df_p["nombre"] == prod_sel].iloc[0]
        precio = float(datos_p["precio_mayor"]) if cant_sel >= datos_p["min_mayor"] else float(datos_p["precio_detal"])
        
        if st.button("➕ Agregar al Carrito"):
            if datos_p["stock"] >= cant_sel:
                st.session_state.car.append({
                    "p": prod_sel, "c": cant_sel, "u": precio, "t": precio * cant_sel
                })
                st.rerun()
            else: st.error("No hay stock suficiente.")

    if st.session_state.car:
        st.write("---")
        st.subheader("Detalle de la Venta")
        for i, item in enumerate(st.session_state.car):
            c1, c2 = st.columns([8, 1])
            c1.info(f"**{item['p']}** | Cant: {item['c']} | Precio: ${item['u']:.2f} | Subtotal: ${item['t']:.2f}")
            if c2.button("❌", key=f"del_{i}"):
                st.session_state.car.pop(i)
                st.rerun()
        
        total_usd = sum(x['t'] for x in st.session_state.car)
        total_bs = total_usd * tasa
        st.markdown(f"## Total: **Bs. {total_bs:,.2f}** (${total_usd:,.2f})")
        
        st.subheader("💳 Registro de Pagos")
        c1, c2, c3 = st.columns(3)
        ef_bs = c1.number_input("Efectivo Bs", min_value=0.0)
        pm_bs = c1.number_input("Pago Móvil Bs", min_value=0.0)
        pu_bs = c2.number_input("Punto Bs", min_value=0.0)
        ot_bs = c2.number_input("Otros Bs", min_value=0.0)
        ze_us = c3.number_input("Zelle $", min_value=0.0)
        di_us = c3.number_input("Divisas $", min_value=0.0)
        
        pagado_bs = ef_bs + pm_bs + pu_bs + ot_bs + ((ze_us + di_us) * tasa)
        vuelto = pagado_bs - total_bs
        
        if pagado_bs < total_bs - 0.1:
            st.warning(f"Faltan: Bs. {abs(vuelto):,.2f}")
        else:
            st.success(f"Vuelto: Bs. {vuelto:,.2f}")
            
            if st.button("✅ FINALIZAR Y FACTURAR"):
                try:
                    for v in st.session_state.car:
                        db.table("ventas").insert({
                            "producto": v['p'], "cantidad": v['c'], "total_usd": v['t'],
                            "tasa_cambio": tasa, "p_efectivo": ef_bs, "p_movil": pm_bs,
                            "p_punto": pu_bs, "p_zelle": ze_us, "p_divisas": di_us,
                            "fecha": datetime.now().isoformat()
                        }).execute()
                        # Actualizar Stock
                        stk_actual = int(df_p[df_p["nombre"] == v['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_actual - v['c']}).eq("nombre", v['p']).execute()
                    
                    st.session_state.pdf_bytes = crear_ticket(st.session_state.car, total_bs, total_usd, tasa)
                    st.session_state.car = []
                    st.success("Venta procesada.")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

        if 'pdf_bytes' in st.session_state:
            st.download_button("📥 Descargar Ticket PDF", st.session_state.pdf_bytes, "ticket.pdf", "application/pdf")

# --- 3. REPORTES ---
elif opcion == "📊 Reportes":
    st.header("📊 Reportes de Ventas")
    res_v = db.table("ventas").select("*").order("fecha", desc=True).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        st.dataframe(df_v, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_v.to_excel(writer, index=False, sheet_name='Ventas')
        
        st.download_button("📥 Descargar Reporte Excel", output.getvalue(), "reporte_ventas.xlsx")
    else: st.info("No hay ventas registradas.")
