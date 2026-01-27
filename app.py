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
    with st.expander("➕ Nuevo Producto"):
        with st.form("f1", clear_on_submit=True):
            n, s = st.text_input("Nombre"), st.number_input("Stock", 0)
            pd_v, pm_v, mm = st.number_input("Precio Detal ($)"), st.number_input("Precio Mayor ($)"), st.number_input("Min. Mayor", 1)
            if st.form_submit_button("Guardar"):
                db.table("inventario").insert({"nombre":n,"stock":s,"precio_detal":pd_v,"precio_mayor":pm_v,"min_mayor":mm}).execute()
                st.success("Guardado correctamente"); st.rerun()
    
    try:
        res = db.table("inventario").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        else: st.info("Inventario vacío.")
    except: st.error("Error al conectar con el inventario.")

elif m == "🛒 Venta":
    st.header("🛒 Ventas")
    # CORRECCIÓN TASA: Ahora permite hasta 1.000.000
    t = st.number_input("Tasa del Día (Bs/$)", min_value=1.0, max_value=1000000.0, value=60.0, step=0.1)
    
    try:
        r = db.table("inventario").select("*").execute()
        if r.data:
            df = pd.DataFrame(r.data)
            c1, c2 = st.columns([3,1])
            sel = c1.selectbox("Seleccione Producto", df["nombre"])
            can = c2.number_input("Cantidad", 1)
            it = df[df["nombre"]==sel].iloc[0]
            p_u = float(it["precio_mayor"]) if can >= it["min_mayor"] else float(it["precio_detal"])
            if st.button("➕ Añadir al Carrito"):
                if it["stock"] >= can:
                    st.session_state.car.append({"p":sel,"c":can,"u":p_u,"t":p_u*can}); st.rerun()
                else: st.error("Stock insuficiente")
    except: st.error("Error cargando productos.")

    if st.session_state.car:
        st.write("---")
        for i, x in enumerate(st.session_state.car):
            ca, cb = st.columns([8, 1])
            ca.info(f"{x['p']} | {x['c']} x ${x['u']} = ${x['t']:.2f}")
            if cb.button("❌", key=f"d{i}"):
                st.session_state.car.pop(i); st.rerun()
        
        tot_u = sum(z['t'] for z in st.session_state.car); tot_b = tot_u * t
        st.subheader(f"Total a Pagar: Bs. {tot_b:,.2f} (${tot_u:,.2f})")
        
        pag = st.number_input("Monto Recibido (Bs)", 0.0)
        if pag < tot_b - 0.1: st.warning(f"Faltan: {tot_b-pag:,.2f} Bs")
        else: st.success(f"Vuelto: {pag-tot_b:,.2f} Bs")

        if st.button("✅ FINALIZAR FACTURA"):
            if pag >= tot_b - 0.1:
                try:
                    for y in st.session_state.car:
                        # Insertar venta (solo columnas básicas para evitar errores)
                        db.table("ventas").insert({
                            "producto": y['p'],
                            "cantidad": y['c'],
                            "total_usd": y['t'],
                            "tasa_cambio": t,
                            "fecha": datetime.now().isoformat()
                        }).execute()
                        
                        # Restar Stock
                        r_s = db.table("inventario").select("stock").eq("nombre", y['p']).execute()
                        if r_s.data:
                            n_s = int(r_s.data[0]['stock']) - y['c']
                            db.table("inventario").update({"stock": n_s}).eq("nombre", y['p']).execute()
                    
                    st.session_state.car = []
                    st.success("¡Factura procesada con éxito!")
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")
            else: st.error("El pago no está completo.")

elif m == "📊 Total":
    st.header("📊 Reporte de Ventas")
    try:
        res = db.table("ventas").select("*").order("fecha", desc=True).execute()
        if res.data:
            dfv = pd.DataFrame(res.data)
            st.dataframe(dfv, use_container_width=True)
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as wr: dfv.to_excel(wr, index=False)
            st.download_button("📥 Descargar Reporte Excel", out.getvalue(), "ventas.xlsx")
        else: st.info("No hay ventas registradas.")
    except: st.error("No se pudieron cargar los reportes.")
