import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
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

with st.sidebar:
    st.markdown("<h2 style='color:#FF8C00;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📦 Inventario", "🛒 Ventas", "📊 Reportes"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.carrito = []
        st.rerun()

# --- INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Inventario")
    with st.expander("➕ Nuevo Producto"):
        with st.form("f1", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre")
            s = c1.number_input("Stock", min_value=0)
            pd = c2.number_input("Precio Detal ($)", min_value=0.0)
            pm = c2.number_input("Precio Mayor ($)", min_value=0.0)
            mm = c2.number_input("Min. Mayor", min_value=1)
            if st.form_submit_button("Guardar"):
                supabase.table("inventario").insert({"nombre":n,"stock":int(s),"precio_detal":float(pd),"precio_mayor":float(pm),"min_mayor":int(mm)}).execute()
                st.success("Guardado"); st.rerun()
    
    res = supabase.table("inventario").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data)[["nombre","stock","precio_detal","precio_mayor","min_mayor"]], use_container_width=True)

# --- VENTAS ---
elif menu == "🛒 Ventas":
    st.header("🛒 Ventas")
    tasa = st.number_input("Tasa BCV", min_value=1.0, value=50.0)
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        dfp = pd.DataFrame(res.data)
        c1, c2 = st.columns([3,1])
        sel = c1.selectbox("Producto", dfp["nombre"])
        cant = c2.number_input("Cant.", min_value=1)
        
        info = dfp[dfp["nombre"]==sel].iloc[0]
        p_u = float(info["precio_mayor"]) if cant >= info["min_mayor"] else float(info["precio_detal"])
        
        if st.button("➕ Añadir"):
            if info["stock"] >= cant:
                st.session_state.carrito.append({"p":sel,"c":int(cant),"u":p_u,"t":p_u*cant})
                st.rerun()
            else: st.error("Sin stock")

    if st.session_state.carrito:
        dfc = pd.DataFrame(st.session_state.carrito)
        st.table(dfc)
        tot_u = dfc["t"].sum(); tot_b = tot_u * tasa
        st.subheader(f"Total: Bs. {tot_b:,.2f} (${tot_u:,.2f})")
        
        col1, col2, col3 = st.columns(3)
        e_b = col1.number_input("Efectivo Bs")
        m_b = col1.number_input("Móvil Bs")
        p_b = col2.number_input("Punto Bs")
        o_b = col2.number_input("Otros Bs")
        z_u = col3.number_input("Zelle $")
        d_u = col3.number_input("Divisa $")
        
        pagado = e_b + m_b + p_b + o_b + ((z_u + d_u)*tasa)
        dif = tot_b - pagado
        
        if dif > 0.1: st.warning(f"Faltan: Bs. {dif:,.2f}")
        elif dif < -0.1: st.info(f"Vuelto: Bs. {abs(dif):,.2f}")
        else: st.success("Pago Completo")
        
        if st.button("✅ FINALIZAR"):
            if pagado >= (tot_b - 0.1):
                for i, item in enumerate(st.session_state.carrito):
                    v_data = {"fecha":datetime.now().isoformat(),"producto":item["p"],"cantidad":item["c"],"total_usd":item["t"],"tasa_cambio":tasa,
                             "pago_efectivo":float(e_b/tasa) if i==0 else 0,"pago_punto":float(p_b/tasa) if i==0 else 0,
                             "pago_movil":float(m_b/tasa) if i==0 else 0,"pago_zelle":float(z_u) if i==0 else 0,
                             "pago_divisas":float(d_u) if i==0 else 0,"pago_otros":float(o_b/tasa) if i==0 else 0}
                    supabase.table("ventas").insert(v_data).execute()
                    stk = int(dfp[dfp["nombre"]==item["p"]].iloc[0]["stock"])
                    supabase.table("inventario").update({"stock":stk-item["c"]}).eq("nombre",item["p"]).execute()
                st.balloons(); st.session_state.carrito = []; st.rerun()

# --- REPORTES ---
elif menu == "📊 Reportes":
    st.header("📊 Reportes")
    f_sel = st.date_input("Fecha", date.today())
    try:
        ini = datetime.combine(f_sel, datetime.min.time()).isoformat()
        fin = datetime.combine(f_sel, datetime.max.time()).isoformat()
        res = supabase.table("ventas").select("*").gte("fecha", ini).lte("fecha", fin).execute()
        if res.data:
            dfv = pd.DataFrame(res.data)
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as wr: dfv.to_excel(wr, index=False)
            st.download_button("📥 Descargar Excel", out.getvalue(), f"{f_sel}.xlsx")
            st.subheader("Resumen Productos")
            st.table(dfv.groupby("producto").agg({"cantidad":"sum","total_usd":"sum"}))
            st.subheader("Ventas Detalladas")
            st.dataframe(dfv[["fecha","producto","cantidad","total_usd"]], use_container_width=True)
        else: st.info("Sin datos")
    except Exception as e: st.error(f"Error: {e}")
