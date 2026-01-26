import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. CONFIGURACIÓN Y SEGURIDAD
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

def verificar_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pwd == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Error")
        return False
    return True

if not verificar_password(): st.stop()

# Conexión Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- BARRA LATERAL ---
st.sidebar.title("🏪 Mi Negocio")
menu = st.sidebar.selectbox("Menú Principal", ["Inicio", "Punto de Venta", "Inventario", "Gastos", "Cierre de Caja"])
tasa = st.sidebar.number_input("Tasa (BS/$)", value=1.0, min_value=1.0)

# Alerta de Stock Bajo (Global)
res_stock = supabase.table("inventario").select("nombre, stock").lt("stock", 6).execute()
if res_stock.data:
    st.sidebar.error("⚠️ STOCK BAJO:")
    for p in res_stock.data: st.sidebar.write(f"- {p['nombre']}: {p['stock']}")

# --- MÓDULO 1: INICIO (DASHBOARD) ---
if menu == "Inicio":
    st.title("🚀 Panel de Control")
    
    # Obtener datos reales para las métricas
    v = supabase.table("ventas").select("*").execute()
    df_v = pd.DataFrame(v.data)
    total_ventas = df_v['total_usd'].sum() if not df_v.empty else 0
    num_ventas = len(df_v)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ventas Totales ($)", f"${total_ventas:.2f}")
    c2.metric("Nro. de Operaciones", num_ventas)
    c3.metric("Alertas de Stock", len(res_stock.data), delta_color="inverse")
    
    st.markdown("---")
    st.subheader("📝 Últimas Ventas")
    if not df_v.empty:
        st.dataframe(df_v.tail(5), use_container_width=True)

from fpdf import FPDF # Asegúrate de que esta línea esté al inicio del archivo app.py

# --- MÓDULO 2: PUNTO DE VENTA (CON PDF) ---
elif menu == "Punto de Venta":
    st.header("💰 Nueva Venta")
    res = supabase.table("inventario").select("*").execute()
    productos = res.data
    
    col_a, col_b = st.columns(2)
    with col_a:
        prod_sel = st.selectbox("Seleccione Producto", [p['nombre'] for p in productos])
    with col_b:
        cant = st.number_input("Cantidad", min_value=1)
    
    if prod_sel:
        p_data = next(item for item in productos if item["nombre"] == prod_sel)
        total_usd = (p_data['precio_detal'] * cant)
        total_bs = total_usd * tasa
        st.info(f"Monto a cobrar: ${total_usd:.2f} | En Bolívares: {total_bs:.2f} BS")
        
        if st.button("Finalizar Venta y Generar Ticket PDF"):
            # 1. Actualizar Stock y Registrar en Supabase
            supabase.table("inventario").update({"stock": p_data['stock']-cant}).eq("id", p_data["id"]).execute()
            supabase.table("ventas").insert({"producto": prod_sel, "cantidad": cant, "total_usd": total_usd}).execute()
            
            # 2. CREACIÓN DEL PDF EN MEMORIA
            pdf = FPDF(format=(80, 150)) # Formato de ticket pequeño (80mm)
            pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5, "TICKET DE VENTA", ln=True, align='C')
            pdf.set_font("Arial", "", 8)
            pdf.cell(0, 5, "------------------------------------------", ln=True, align='C')
            pdf.cell(0, 5, f"Producto: {prod_sel}", ln=True)
            pdf.cell(0, 5, f"Cantidad: {cant}", ln=True)
            pdf.cell(0, 5, f"Precio Unit: ${p_data['precio_detal']:.2f}", ln=True)
            pdf.cell(0, 10, f"TOTAL USD: ${total_usd:.2f}", ln=True)
            pdf.cell(0, 5, f"TASA: {tasa:.2f}", ln=True)
            pdf.cell(0, 5, f"TOTAL BS: {total_bs:.2f}", ln=True)
            pdf.cell(0, 5, "------------------------------------------", ln=True, align='C')
            pdf.cell(0, 5, "¡Gracias por su compra!", ln=True, align='C')
            
            # 3. Botón de descarga
            pdf_bytes = pdf.output() 
            st.success("✅ Venta registrada.")
            st.download_button(
                label="📥 Descargar Ticket PDF",
                data=pdf_bytes,
                file_name=f"ticket_{prod_sel}.pdf",
                mime="application/pdf"
            )

# --- MÓDULO 3: INVENTARIO ---
elif menu == "Inventario":
    st.header("📦 Gestión de Inventario")
    with st.form("inv"):
        n = st.text_input("Nombre")
        s = st.number_input("Stock", min_value=0)
        pd1 = st.number_input("Precio Detal")
        pm = st.number_input("Precio Mayor")
        if st.form_submit_button("Guardar Producto"):
            supabase.table("inventario").insert({"nombre":n, "stock":s, "precio_detal":pd1, "precio_mayor":pm}).execute()
            st.rerun()
            
    res = supabase.table("inventario").select("*").execute()
    st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# --- MÓDULO 4: GASTOS ---
elif menu == "Gastos":
    st.header("💸 Registro de Gastos")
    with st.form("nuevo_gasto"):
        desc = st.text_input("Descripción del gasto")
        monto = st.number_input("Monto en Dólares ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Servicios", "Personal", "Mercancía", "Local", "Otros"])
        if st.form_submit_button("Registrar Gasto"):
            supabase.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "categoria": cat}).execute()
            st.success("Gasto guardado.")

# --- MÓDULO 5: CIERRE DE CAJA ---
elif menu == "Cierre de Caja":
    st.header("📈 Balance General")
    v = supabase.table("ventas").select("*").execute()
    g = supabase.table("gastos").select("*").execute()
    df_v = pd.DataFrame(v.data)
    df_g = pd.DataFrame(g.data)
    
    total_ventas = df_v['total_usd'].sum() if not df_v.empty else 0
    total_gastos = df_g['monto_usd'].sum() if not df_g.empty else 0

