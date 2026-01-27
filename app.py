import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS + Propinas", layout="wide")

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
    .propina-box { background-color: #D4EDDA; padding: 10px; border-radius: 5px; color: #155724; font-weight: bold; }
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
        pdf.cell(190, 7, f"RECARGO/PROPINA: ${propina_usd:.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {total_usd + propina_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MENÚ ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "📊 Reporte de Caja"])
    st.markdown("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Control de Existencias")
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    autorizado = clave == CLAVE_ADMIN
    t1, t2 = st.tabs(["📋 Listado", "🆕 Nuevo"])
    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()
    with t1:
        if not df_inv.empty:
            busq = st.text_input("🔍 Buscar...")
            df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
            st.dataframe(df_m[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True, hide_index=True)
            if autorizado:
                sel = st.selectbox("Editar producto", df_inv["nombre"])
                it = df_inv[df_inv["nombre"] == sel].iloc[0]
                c1, c2, c3 = st.columns(3)
                en, es = c1.text_input("Nombre", it["nombre"]), c1.number_input("Stock", value=int(it["stock"]))
                epd, epm = c2.number_input("Precio Detal $", value=float(it["precio_detal"])), c2.number_input("Precio Mayor $", value=float(it["precio_mayor"]))
                emm = c3.number_input("Min. Mayor", value=int(it["min_mayor"]))
                b1, b2 = st.columns(2)
                if b1.button("💾 Guardar"):
                    db.table("inventario").update({"nombre":en, "stock":es, "precio_detal":epd, "precio_mayor":epm, "min_mayor":emm}).eq("id", it["id"]).execute()
                    st.rerun()
                if b2.button("🗑️ Borrar"):
                    db.table("inventario").delete().eq("id", it["id"]).execute(); st.rerun()
    with t2:
        if autorizado:
            with st.form("f_n"):
                n1, n2 = st.columns(2)
                nom, stk = n1.text_input("Nombre"), n1.number_input("Stock", 0)
                pd_v, pm_v, mm = n2.number_input("Precio Detal $"), n2.number_input("Precio Mayor $"), n2.number_input("Min. Mayor", 1)
                if st.form_submit_button("Registrar"):
                    db.table("inventario").insert({"nombre":nom,"stock":stk,"precio_detal":pd_v,"precio_mayor":pm_v,"min_mayor":mm}).execute(); st.rerun()

# --- 5. VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa (Bs/$)", 1.0, 1000.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busq_v = st.text_input("🔍 Buscar producto...").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(busq_v)] if busq_v else df_p
        if not df_v.empty:
            v1, v2 = st.columns([3, 1])
            psel = v1.selectbox("Elegir", df_v["nombre"])
            csel = v2.number_input("Cant", 1)
            item = df_p[df_p["nombre"] == psel].iloc[0]
            pf = float(item["precio_mayor"]) if csel >= item["min_mayor"] else float(item["precio_detal"])
            if st.button("➕ Añadir"):
                if item["stock"] >= csel:
                    st.session_state.car.append({"p":psel, "c":csel, "u":pf, "t":pf*csel}); st.rerun()
                else: st.error("Sin stock")

    if st.session_state.car:
        st.write("---")
        for i, it in enumerate(st.session_state.car):
            ca, cb = st.columns([9, 1]); ca.info(f"{it['p']} x{it['c']} = ${it['t']:.2f}")
            if cb.button("❌", key=f"v_{i}"): st.session_state.car.pop(i); st.rerun()
        
        tot_u = sum(z['t'] for z in st.session_state.car)
        
        # AJUSTE DE MONTO FINAL (PROPINA)
        st.markdown(f"### Subtotal Productos: ${tot_u:,.2f}")
        monto_ajustado_usd = st.number_input("Monto Final a Cobrar ($)", min_value=tot_u, value=tot_u, step=0.01, help="Si cobras más del subtotal, la diferencia se guardará como propina.")
        propina_calc = monto_ajustado_usd - tot_u
        
        if propina_calc > 0:
            st.markdown(f"<div class='propina-box'>Propina registrada: ${propina_calc:,.2f}</div>", unsafe_allow_html=True)
        
        total_final_bs = monto_ajustado_usd * tasa
        st.markdown(f"## TOTAL A COBRAR: Bs. {total_final_bs:,.2f}")
        
        c1, c2, c3 = st.columns(3)
        eb, pb = c1.number_input("Efec Bs", 0.0), c1.number_input("P.Móvil Bs", 0.0)
        pub, ob = c2.number_input("Punto Bs", 0.0), c2.number_input("Otro Bs", 0.0)
        zu, du = c3.number_input("Zelle $", 0.0), c3.number_input("Divisa $", 0.0)
        
        pag_b = eb + pb + pub + ob + ((zu + du) * tasa)
        if pag_b >= total_final_bs - 0.1:
            st.success(f"Vuelto: {pag_b - total_final_bs:,.2f} Bs.")
            if st.button("✅ FINALIZAR"):
                try:
                    for x in st.session_state.car:
                        db.table("ventas").insert({
                            "producto":x['p'],"cantidad":x['c'],"total_usd":x['t'],"tasa_cambio":tasa,
                            "p_efectivo":eb,"p_movil":pb,"p_punto":pub,"p_zelle":zu,"p_divisas":du,
                            "propina": propina_calc / len(st.session_state.car), # Se divide entre items para el reporte
                            "fecha":datetime.now().isoformat()
                        }).execute()
                        stk_a = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_a - x['c']}).eq("nombre", x['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, total_final_bs, tot_u, tasa, propina_calc)
                    st.session_state.car = []; st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    if st.session_state.pdf_b: st.download_button("📥 Ticket PDF", st.session_state.pdf_b, "ticket.pdf")

# --- 6. REPORTE ---
elif opcion == "📊 Reporte de Caja":
    st.header("📊 Reporte y Cierre")
    f_f = st.date_input("Día", date.today())
    try:
        res_v = db.table("ventas").select("*").gte("fecha", f_f.isoformat()).execute()
        if res_v.data:
            df_r = pd.DataFrame(res_v.data)
            for c in ['p_efectivo', 'p_movil', 'p_punto', 'p_zelle', 'p_divisas', 'total_usd', 'propina']:
                if c not in df_r.columns: df_r[c] = 0.0
            
            # RESUMEN
            st.subheader("💰 Resumen Financiero")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Ventas Netas ($)", f"{df_r['total_usd'].sum():,.2f}")
            # AQUÍ ESTÁ TU PROPINA
            r2.metric("MIS PROPINAS ($)", f"{df_r['propina'].sum():,.2f}", delta="Ganancia Extra")
            r3.metric("Total en Caja ($)", f"{(df_r['total_usd'].sum() + df_r['propina'].sum()):,.2f}")
            r4.metric("Total en Bolívares", f"{(df_r['p_efectivo'].sum() + df_r['p_movil'].sum() + df_res['p_punto'].sum()):,.2f} Bs")

            st.write("---")
            st.subheader("📑 Detalle de Ventas")
            df_f = df_r.rename(columns={
                'producto': 'PRODUCTO', 'cantidad': 'CANT', 'total_usd': 'SUBTOTAL ($)', 'propina': 'PROPINA ($)'
            })
            # Calculamos el total por fila (Subtotal + Propina)
            df_f['TOTAL ($)'] = df_f['SUBTOTAL ($)'] + df_f['PROPINA ($)']
            cols = ['PRODUCTO', 'CANT', 'SUBTOTAL ($)', 'PROPINA ($)', 'TOTAL ($)']
            st.dataframe(df_f[cols], use_container_width=True, hide_index=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as w: df_f.to_excel(w, index=False)
            st.download_button("📥 Excel", buf.getvalue(), f"Cierre_{f_f}.xlsx")
        else: st.info("Sin ventas.")
    except Exception as e: st.error(f"Error: {e}")
