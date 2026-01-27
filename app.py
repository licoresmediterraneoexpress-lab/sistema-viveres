import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time, io

st.set_page_config(page_title="Mediterraneo POS", layout="wide")
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

@st.cache_resource
def init(): return create_client(URL, KEY)
db = init()

if 'car' not in st.session_state: st.session_state.car = []

st.markdown("<style>.stApp{background:white;} [data-testid='stSidebar']{background:#0041C2;} .stButton>button{background:#FF8C00;color:white;border-radius:10px;font-weight:bold;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2 style='color:#FF8C00;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    m = st.radio("MENÚ", ["📦 Stock", "🛒 Venta", "📊 Total"])
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

if m == "📦 Stock":
    st.header("📦 Inventario")
    with st.expander("➕ Nuevo"):
        with st.form("f1", clear_on_submit=True):
            n, s = st.text_input("Nombre"), st.number_input("Stock", 0)
            pd_v, pm_v, mm = st.number_input("Detal"), st.number_input("Mayor"), st.number_input("Min. Mayor", 1)
            if st.form_submit_button("Ok"):
                db.table("inventario").insert({"nombre":n,"stock":s,"precio_detal":pd_v,"precio_mayor":pm_v,"min_mayor":mm}).execute()
                st.success("Listo"); st.rerun()
    
    try:
        res = db.table("inventario").select("*").execute()
        if res.data and len(res.data) > 0:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        else:
            st.info("El inventario está vacío.")
    except Exception as e:
        st.error("Error al cargar datos. Verifica la conexión.")

elif m == "🛒 Venta":
    st.header("🛒 Ventas")
    t = st.number_input("Tasa BCV", 1.0, 100.0, 50.0)
    try:
        r = db.table("inventario").select("*").execute()
        if r.data and len(r.data) > 0:
            df = pd.DataFrame(r.data)
            c1, c2 = st.columns([3,1])
            sel = c1.selectbox("Producto", df["nombre"])
            can = c2.number_input("Cant", 1)
            it = df[df["nombre"]==sel].iloc[0]
            p_u = float(it["precio_mayor"]) if can >= it["min_mayor"] else float(it["precio_detal"])
            if st.button("➕ Añadir"):
                if it["stock"] >= can:
                    st.session_state.car.append({"p":sel,"c":can,"u":p_u,"t":p_u*can}); st.rerun()
                else: st.error("No hay stock")
        else:
            st.warning("No hay productos registrados en el inventario.")
    except: st.error("Error en la base de datos.")

    if st.session_state.car:
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([8, 1])
            ca.info(f"{x['p']} | {x['c']} x ${x['u']} = ${x['t']:.2f}")
            if cb.button("❌", key=f"d{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        tot_u = sum(z['t'] for z in st.session_state.car); tot_b = tot_u * t
        st.subheader(f"Total: Bs. {tot_b:,.2f} (${tot_u:,.2f})")
        pag = st.number_input("Pagado Bs", 0.0)
        if pag < tot_b: st.warning(f"Falta: {tot_b-pag:,.2f} Bs")
        else: st.success(f"Vuelto: {pag-tot_b:,.2f} Bs")

        if st.button("✅ FINALIZAR"):
            if pag >= tot_b - 0.1:
                for y in st.session_state.car:
                    db.table("ventas").insert({"producto":y['p'],"cantidad":y['c'],"total_usd":y['t'],"tasa_cambio":t}).execute()
                    # Actualizar stock buscando el item correcto
                    r_stock = db.table("inventario").select("stock").eq("nombre", y['p']).execute()
                    if r_stock.data:
                        nuevo_s = int(r_stock.data[0]['stock']) - y['c']
                        db.table("inventario").update({"stock": nuevo_s}).eq("nombre", y['p']).execute()
                st.session_state.car = []; st.success("Venta realizada"); time.sleep(1); st.rerun()

elif m == "📊 Total":
    st.header("📊 Reportes")
    f = st.date_input("Fecha", date.today())
    try:
        res = db.table("ventas").select("*").execute()
        if res.data:
            dfv = pd.DataFrame(res.data)
            st.dataframe(dfv, use_container_width=True)
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as wr: dfv.to_excel(wr, index=False)
            st.download_button("📥 Descargar Excel", out.getvalue(), "reporte.xlsx")
        else: st.info("No hay ventas registradas.")
    except: st.error("No se pudieron cargar los reportes.")
