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
def init(): return create_client(URL, KEY)
supabase = init()

if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- ESTILOS ---
st.markdown("<style>.stApp{background:white;} [data-testid='stSidebar']{background:#0041C2;} .stButton>button{background:#FF8C00;color:white;border-radius:10px; font-weight:bold;}</style>", unsafe_allow_html=True)

def generar_pdf(carrito, total_bs, total_usd, tasa):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(190, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(80, 10, "Producto"); pdf.cell(30, 10, "Cant."); pdf.cell(40, 10, "Precio ($)"); pdf.cell(40, 10, "Total ($)", ln=True)
        pdf.set_font("Arial", '', 12)
        for item in carrito:
            pdf.cell(80, 10, item['p']); pdf.cell(30, 10, str(item['c'])); pdf.cell(40, 10, f"{item['u']:.2f}"); pdf.cell(40, 10, f"{item['t']:.2f}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
        pdf.cell(190, 10, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
        return pdf.output(dest='S').encode('latin-1')
    except:
        return None

with st.sidebar:
    st.markdown("<h2 style='color:#FF8C00;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📦 Inventario", "🛒 Ventas", "📊 Reportes"])
    if st.button("🗑️ Vaciar Todo el Carrito"):
        st.session_state.carrito = []
        st.rerun()

# --- INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Inventario")
    with st.expander("➕ Nuevo Producto"):
        with st.form("f1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n, s = c1.text_input("Nombre"), c1.number_input("Stock", min_value=0)
            pd_v, pm_v, mm_v = c2.number_input("Precio Detal ($)"), c2.number_input("Precio Mayor ($)"), c2.number_input("Min. Mayor", min_value=1)
            if st.form_submit_button("Guardar"):
                supabase.table("inventario").insert({"nombre":n,"stock":int(s),"precio_detal":float(pd_v),"precio_mayor":float(pm_v),"min_mayor":int(mm_v)}).execute()
                st.success("Guardado"); st.rerun()
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        df_inv = pd.DataFrame(res.data)
        st.dataframe(df_inv, use_container_width=True)

# --- VENTAS ---
elif menu == "🛒 Ventas":
    st.header("🛒 Ventas")
    tasa = st.number_input("Tasa BCV", min_value=1.0, value=50.0)
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        dfp = pd.DataFrame(res.data)
        c1, c2 = st.columns([3,1])
        sel = c1.selectbox("Seleccione Producto", dfp["nombre"])
        cant = c2.number_input("Cantidad", min_value=1)
        info = dfp[dfp["nombre"]==sel].iloc[0]
        p_u = float(info.get("precio_mayor", 0)) if cant >= int(info.get("min_mayor", 1)) else float(info.get("precio_detal", 0))
        
        if st.button("➕ Agregar al Carrito"):
            if info["stock"] >= cant:
                st.session_state.carrito.append({"p":sel,"c":int(cant),"u":p_u,"t":p_u*cant})
                st.rerun()
            else: st.error("Sin stock suficiente")

    if st.session_state.carrito:
        st.subheader("🛒 Resumen de Compra")
        
        # --- TABLA DE ELIMINACIÓN (BOTONES VISIBLES) ---
        for i, item in enumerate(st.session_state.carrito):
            col_info, col_btn = st.columns([8, 1])
            col_info.info(f"{item['p']} - Cant: {item['c']} - Subtotal: ${item['t']:.2f}")
            if col_btn.button("❌", key=f"btn_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        
        tot_u = sum(item['t'] for item in st.session_state.carrito)
        tot_b = tot_u * tasa
        st.markdown(f"### **Total: Bs. {tot_b:,.2f}**")
        
        st.write("---")
        st.subheader("💳 Registro de Pago")
        c1, c2, c3 = st.columns(3)
        e_b = c1.number_input("Efectivo Bs", min_value=0.0)
        m_b = c1.number_input("Móvil Bs", min_value=0.0)
        p_b = c2.number_input("Punto Bs", min_value=0.0)
        o_b = c2.number_input("Otros Bs", min_value=0.0)
        z_u = c3.number_input("Zelle $", min_value=0.0)
        d_u = c3.number_input("Divisa $", min_value=0.0)
        
        pagado = e_b + m_b + p_b + o_b + ((z_u + d_u)*tasa)
        dif = tot_b - pagado

        if dif > 0.1: st.warning(f"Faltan: Bs. {dif:,.2f}")
        elif dif < -0.1: st.success(f"Vuelto: Bs. {abs(dif):,.2f}")
        else: st.success("¡Monto Exacto!")

        if st.button("✅ FINALIZAR VENTA"):
            if pagado >= (tot_b - 0.1):
                pdf_val = generar_pdf(st.session_state.carrito, tot_b, tot_u, tasa)
                for idx, it in enumerate(st.session_state.carrito):
                    v_data = {"fecha":datetime.now().isoformat(),"producto":it['p'],"cantidad":it['c'],"total_usd":it['t'],"tasa_cambio":tasa,
                             "pago_efectivo":float(e_b/tasa) if idx==0 else 0,"pago_punto":float(p_b/tasa) if idx==0 else 0,
                             "pago_movil":float(m_b/tasa) if idx==0 else 0,"pago_zelle":float(z_u) if idx==0 else 0,
                             "pago_divisas":float(d_u) if idx==0 else 0,"pago_otros":float(o_b/tasa) if idx==0 else 0}
                    supabase.table("ventas").insert(v_data).execute()
                    
                    p_row = dfp[dfp["nombre"]==it['p']].iloc[0]
                    supabase.table("inventario").update({"stock": int(p_row["stock"] - it['c'])}).eq("nombre",it['p']).execute()
                
                st.session_state.pdf_ready = pdf_val
                st.session_state.carrito = []
                st.success("Venta Guardada con Éxito")
                st.rerun()
            else:
                st.error("El pago no está completo")
        
        if 'pdf_ready' in st.session_state and st.session_state.pdf_ready:
            st.download_button("📥 DESCARGAR TICKET", st.session_state.pdf_ready, "ticket.pdf", "application/pdf")

# --- REPORTES ---
elif menu == "📊 Reportes":
    st.header("📊 Reportes")
    f_sel = st.date_input("
