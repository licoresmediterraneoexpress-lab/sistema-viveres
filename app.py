import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="Mediterraneo POS System", layout="wide")

# Credenciales de conexión
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234" # <--- CAMBIA TU CLAVE AQUÍ SI DESEAS

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

# Inicializar estados
if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# Diseño visual
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold; width: 100%;}
    .stMetric {background: #F8F9FA; padding: 10px; border-radius: 10px; border-left: 5px solid #FF8C00;}
</style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
def crear_ticket(carrito, total_bs, total_usd, tasa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(80, 7, "Producto", 1); pdf.cell(20, 7, "Cant", 1); pdf.cell(45, 7, "Precio $", 1); pdf.cell(45, 7, "Total $", 1, ln=True)
    for i in carrito:
        pdf.cell(80, 7, str(i['p']), 1); pdf.cell(20, 7, str(i['c']), 1); pdf.cell(45, 7, f"{i['u']:.2f}", 1); pdf.cell(45, 7, f"{i['t']:.2f}", 1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {total_usd:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "📊 Reporte de Caja"])
    st.markdown("---")
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []; st.rerun()

# --- 4. MÓDULO: INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Control de Existencias")
    
    # Verificación de Clave
    clave = st.sidebar.text_input("Clave de Seguridad", type="password")
    autorizado = clave == CLAVE_ADMIN

    tab_lista, tab_nuevo = st.tabs(["📋 Listado y Edición", "🆕 Nuevo Producto"])

    res_inv = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

    with tab_lista:
        if not df_inv.empty:
            busq_inv = st.text_input("🔍 Filtrar producto por nombre...")
            df_mostrar = df_inv[df_inv['nombre'].str.contains(busq_inv, case=False)] if busq_inv else df_inv
            st.dataframe(df_mostrar[["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]], use_container_width=True, hide_index=True)
            
            if autorizado:
                st.markdown("---")
                st.subheader("🛠️ Editar Producto")
                sel_edit = st.selectbox("Seleccione el producto para modificar", df_inv["nombre"])
                datos_it = df_inv[df_inv["nombre"] == sel_edit].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                en = c1.text_input("Nombre", datos_it["nombre"])
                es = c1.number_input("Stock", value=int(datos_it["stock"]))
                epd = c2.number_input("Precio Detal $", value=float(datos_it["precio_detal"]))
                epm = c2.number_input("Precio Mayor $", value=float(datos_it["precio_mayor"]))
                emm = c3.number_input("Min. para Mayor", value=int(datos_it["min_mayor"]))
                
                col_acc1, col_acc2 = st.columns(2)
                if col_acc1.button("💾 Guardar Cambios"):
                    db.table("inventario").update({"nombre":en, "stock":es, "precio_detal":epd, "precio_mayor":epm, "min_mayor":emm}).eq("id", datos_it["id"]).execute()
                    st.success("Actualizado"); st.rerun()
                if col_acc2.button("🗑️ Eliminar Producto Definitivamente"):
                    db.table("inventario").delete().eq("id", datos_it["id"]).execute()
                    st.error("Producto borrado"); st.rerun()
            else: st.info("🔓 Ingrese clave en la izquierda para editar o borrar.")

    with tab_nuevo:
        if autorizado:
            with st.form("form_nuevo", clear_on_submit=True):
                st.subheader("Registrar en Catálogo")
                n1, n2 = st.columns(2)
                nom = n1.text_input("Nombre del producto")
                stk = n1.number_input("Stock inicial", 0)
                pdet = n2.number_input("Precio Detal ($)", 0.0)
                pmay = n2.number_input("Precio Mayor ($)", 0.0)
                minm = n2.number_input("Cantidad para Mayor", 1)
                if st.form_submit_button("Registrar Producto"):
                    db.table("inventario").insert({"nombre":nom,"stock":stk,"precio_detal":pdet,"precio_mayor":pmay,"min_mayor":minm}).execute()
                    st.success("Producto guardado con éxito."); st.rerun()
        else: st.warning("🔐 Ingrese clave para agregar productos.")

# --- 5. MÓDULO: VENTA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 1000.0, 60.0)
    
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busq_v = st.text_input("🔍 Buscar producto por letras (ej: 'cer', 'har')...").lower()
        df_v = df_p[df_p['nombre'].str.lower().str.contains(busq_v)] if busq_v else df_p
        
        if not df_v.empty:
            v1, v2 = st.columns([3, 1])
            prod_sel = v1.selectbox("Elegir", df_v["nombre"])
            cant_sel = v2.number_input("Cant", 1)
            item = df_p[df_p["nombre"] == prod_sel].iloc[0]
            # Lógica detal/mayor
            p_final = float(item["precio_mayor"]) if cant_sel >= item["min_mayor"] else float(item["precio_detal"])
            
            if st.button("➕ Añadir al Carrito"):
                if item["stock"] >= cant_sel:
                    st.session_state.car.append({"p":prod_sel, "c":cant_sel, "u":p_final, "t":p_final*cant_sel})
                    st.rerun()
                else: st.error("⚠️ No hay suficiente stock disponible.")

    if st.session_state.car:
        st.write("---")
        for i, it in enumerate(st.session_state.car):
            c_a, c_b = st.columns([9, 1])
            c_a.info(f"**{it['p']}** | {it['c']} un x ${it['u']:.2f} = **${it['t']:.2f}**")
            if c_b.button("❌", key=f"v_{i}"): st.session_state.car.pop(i); st.rerun()
        
        tot_u = sum(z['t'] for z in st.session_state.car); tot_b = tot_u * tasa
        st.markdown(f"## Total a Cobrar: Bs. {tot_b:,.2f} (${tot_u:,.2f})")
        
        # Pagos Mixtos
        st.subheader("💳 Formas de Pago")
        p1, p2, p3 = st.columns(3)
        ef_b = p1.number_input("Efectivo Bs", 0.0); pm_b = p1.number_input("Pago Móvil Bs", 0.0)
        pu_b = p2.number_input("Punto Bs", 0.0); ot_b = p2.number_input("Otros Bs", 0.0)
        ze_u = p3.number_input("Zelle $", 0.0); di_u = p3.number_input("Divisas $", 0.0)
        
        pagado_bs = ef_b + pm_b + pu_b + ot_b + ((ze_u + di_u) * tasa)
        if pagado_bs >= tot_b - 0.1:
            st.success(f"Vuelto: {pagado_bs - tot_b:,.2f} Bs.")
            if st.button("✅ FINALIZAR Y FACTURAR"):
                try:
                    for x in st.session_state.car:
                        db.table("ventas").insert({"producto":x['p'],"cantidad":x['c'],"total_usd":x['t'],"tasa_cambio":tasa,"p_efectivo":ef_b,"p_movil":pm_b,"p_punto":pu_b,"p_zelle":ze_u,"p_divisas":di_u,"fecha":datetime.now().isoformat()}).execute()
                        stk_act = int(df_p[df_p["nombre"] == x['p']].iloc[0]['stock'])
                        db.table("inventario").update({"stock": stk_act - x['c']}).eq("nombre", x['p']).execute()
                    st.session_state.pdf_b = crear_ticket(st.session_state.car, tot_b, tot_u, tasa)
                    st.session_state.car = []; st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")
    if st.session_state.pdf_b: st.download_button("📥 Descargar Ticket PDF", st.session_state.pdf_b, "Factura_Mediterraneo.pdf")

# --- 6. MÓDULO: REPORTE ---
elif opcion == "📊 Reporte de Caja":
    st.header("📊 Cierre de Caja y Detalle de Ventas")
    fecha_filtro = st.date_input("Seleccionar Día", date.today())
    
    try:
        res_v = db.table("ventas").select("*").gte("fecha", fecha_filtro.isoformat()).execute()
        if res_v.data:
            df_res = pd.DataFrame(res_v.data)
            # Limpieza de columnas para el cálculo
            for c in ['p_efectivo', 'p_movil', 'p_punto', 'p_zelle', 'p_divisas', 'total_usd']:
                if c not in df_res.columns: df_res[c] = 0.0
            
            # RESUMEN SUPERIOR
            st.subheader("💵 Resumen de Fondos")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Efectivo / Pago Móvil", f"Bs. {(df_res['p_efectivo'].sum() + df_res['p_movil'].sum()):,.2f}")
            r2.metric("Punto / Otros", f"Bs. {df_res['p_punto'].sum():,.2f}")
            r3.metric("Divisas / Zelle", f"$ {(df_res['p_zelle'].sum() + df_res['p_divisas'].sum()):,.2f}")
            r4.metric("TOTAL VENTAS", f"$ {df_res['total_usd'].sum():,.2f}")
            
            st.write("---")
            st.subheader("📝 Libro de Ventas (Tipo Excel)")
            
            # TABLA TIPO EXCEL
            df_final = df_res.copy()
            df_final = df_final.rename(columns={
                'producto': 'PRODUCTO', 'cantidad': 'CANT',
                'p_efectivo': 'EFEC. (Bs)', 'p_movil': 'P.MÓVIL (Bs)',
                'p_punto': 'PUNTO (Bs)', 'p_zelle': 'ZELLE ($)',
                'p_divisas': 'DIVISAS ($)', 'total_usd': 'TOTAL VENTA ($)'
            })
            
            cols_excel = ['PRODUCTO', 'CANT', 'EFEC. (Bs)', 'P.MÓVIL (Bs)', 'PUNTO (Bs)', 'ZELLE ($)', 'DIVISAS ($)', 'TOTAL VENTA ($)']
            st.dataframe(df_final[cols_excel], use_container_width=True, hide_index=True)
            
            # Exportación Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final[cols_excel].to_excel(writer, index=False)
            st.download_button("📥 Descargar Tabla en Excel", buffer.getvalue(), f"Cierre_{fecha_filtro}.xlsx")
        else: st.info("No hay ventas registradas en la fecha seleccionada.")
    except Exception as e: st.error(f"Error cargando reportes: {e}")
