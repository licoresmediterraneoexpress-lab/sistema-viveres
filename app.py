import streamlit as st
from supabase import create_client, Client
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema de Ventas Pro", layout="wide")

# 2. SEGURIDAD (Login simple)
def verificar_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso al Sistema")
        pwd = st.text_input("Contraseña de administrador", type="password")
        if st.button("Ingresar"):
            if pwd == "1234": # Puedes cambiar esta clave
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

if not verificar_password():
    st.stop()

# 3. CONEXIÓN A SUPABASE
# Asegúrate de tener estos datos en tu archivo .streamlit/secrets.toml o configurados en la PC
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error de conexión: Revisa tus credenciales de Supabase.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title("🏪 Menú de Control")
menu = st.sidebar.selectbox("Ir a:", ["Inicio", "Punto de Venta", "Inventario", "Gastos", "Cierre de Caja"])
tasa = st.sidebar.number_input("Tasa de Cambio (BS/$)", value=60.0, min_value=1.0)

# Alerta de Stock Bajo
try:
    res_stock = supabase.table("inventario").select("nombre, stock").lt("stock", 6).execute()
    if res_stock.data:
        st.sidebar.warning("⚠️ STOCK BAJO:")
        for p in res_stock.data:
            st.sidebar.write(f"- {p['nombre']}: {p['stock']} unid.")
except:
    pass

# --- MÓDULO 1: INICIO (DASHBOARD) ---
if menu == "Inicio":
    st.title("🚀 Panel de Control")
    
    # Obtener datos de ventas
    v = supabase.table("ventas").select("*").execute()
    df_v = pd.DataFrame(v.data)
    
    total_ventas = df_v['total_usd'].sum() if not df_v.empty else 0
    num_ventas = len(df_v)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas Totales ($)", f"${total_ventas:.2f}")
    col2.metric("Nro. de Operaciones", num_ventas)
    col3.metric("Alertas de Stock", len(res_stock.data) if 'res_stock' in locals() else 0)
    
    st.divider()
    st.subheader("📝 Registro Reciente")
    if not df_v.empty:
        st.dataframe(df_v.sort_values("fecha", ascending=False).head(10), use_container_width=True)

# --- MÓDULO 2: PUNTO DE VENTA ---
elif menu == "Punto de Venta":
    st.header("💰 Nueva Venta")
    
    # Obtener productos para el selector
    res_inv = supabase.table("inventario").select("*").execute()
    productos = res_inv.data
    
    if not productos:
        st.error("No hay productos en el inventario. Ve al módulo Inventario primero.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            nombres_prod = [p['nombre'] for p in productos]
            prod_sel_nombre = st.selectbox("Seleccione Producto", nombres_prod)
        
        p_data = next(item for item in productos if item["nombre"] == prod_sel_nombre)
        
        with col_b:
            cant = st.number_input(f"Cantidad (Disponible: {p_data['stock']})", min_value=1, max_value=int(p_data['stock']))
        
        total_a_pagar = float(p_data['precio_detal']) * cant
        total_bs = total_a_pagar * tasa
        
        st.info(f"### Total a cobrar: ${total_a_pagar:.2f} | {total_bs:.2f} BS")
        
        st.subheader("💳 Registro de Pagos")
        if "pagos_acumulados" not in st.session_state:
            st.session_state.pagos_acumulados = []

        c1, c2, c3 = st.columns([2, 2, 1])
        metodo = c1.selectbox("Método", ["Efectivo $", "Efectivo BS", "Pago Móvil", "Zelle", "Punto de Venta", "Otros"])
        monto_pago = c2.number_input("Monto entregado", min_value=0.0)
        
        if c3.button("Añadir Pago"):
            if monto_pago > 0:
                st.session_state.pagos_acumulados.append({"metodo": metodo, "monto": monto_pago})
                st.rerun()

        # Calcular totales recibidos
        total_recibido_usd = 0
        pago_detalles = {"pago_efectivo": 0, "pago_punto": 0, "pago_movil": 0, "pago_zelle": 0, "pago_otros": 0}

        if st.session_state.pagos_acumulados:
            for p in st.session_state.pagos_acumulados:
                # Conversión lógica a USD para la base de datos
                monto_en_usd = p['monto'] / tasa if "BS" in p['metodo'] or "Móvil" in p['metodo'] or "Punto" in p['metodo'] else p['monto']
                total_recibido_usd += monto_en_usd
                
                # Clasificación para las columnas de la tabla
                if "Efectivo" in p['metodo']: pago_detalles["pago_efectivo"] += monto_en_usd
                elif "Punto" in p['metodo']: pago_detalles["pago_punto"] += monto_en_usd
                elif "Móvil" in p['metodo']: pago_detalles["pago_movil"] += monto_en_usd
                elif "Zelle" in p['metodo']: pago_detalles["pago_zelle"] += monto_en_usd
                else: pago_detalles["pago_otros"] += monto_en_usd
                
                st.write(f"✅ {p['metodo']}: {p['monto']:.2f} (Ref: ${monto_en_usd:.2f})")

        restante = total_a_pagar - total_recibido_usd
        
        if restante > 0.01:
            st.error(f"Faltan por cobrar: ${restante:.2f}")
        else:
            st.success(f"Cobro completo. Cambio: ${abs(restante):.2f}")
            if st.button("Finalizar Venta"):
                # 1. Actualizar Stock
                nuevo_stock = p_data['stock'] - cant
                supabase.table("inventario").update({"stock": nuevo_stock}).eq("id", p_data["id"]).execute()
                
                # 2. Guardar Venta
                data_venta = {
                    "producto": prod_sel_nombre,
                    "cantidad": cant,
                    "total_usd": total_a_pagar,
                    "tasa_cambio": tasa,
                    **pago_detalles # Inserta automáticamente las columnas de pagos
                }
                supabase.table("ventas").insert(data_venta).execute()
                
                st.session_state.pagos_acumulados = []
                st.success("Venta guardada con éxito.")
                st.rerun()

        if st.button("Limpiar todo"):
            st.session_state.pagos_acumulados = []
            st.rerun()

# --- MÓDULO 3: INVENTARIO ---
elif menu == "Inventario":
    st.header("📦 Gestión de Inventario")
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("inv_form"):
            n = st.text_input("Nombre del producto")
            s = st.number_input("Cantidad inicial", min_value=0)
            pd1 = st.number_input("Precio Detal ($)")
            pm = st.number_input("Precio Mayor ($)")
            if st.form_submit_button("Registrar"):
                supabase.table("inventario").insert({"nombre":n, "stock":s, "precio_detal":pd1, "precio_mayor":pm}).execute()
                st.success("Producto agregado")
                st.rerun()
                
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# --- MÓDULO 4: GASTOS ---
elif menu == "Gastos":
    st.header("💸 Registro de Gastos")
    with st.form("nuevo_gasto"):
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Servicios", "Personal", "Mercancía", "Local", "Otros"])
        if st.form_submit_button("Guardar Gasto"):
            supabase.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "categoria": cat}).execute()
            st.success("Gasto registrado")

# --- MÓDULO 5: CIERRE DE CAJA ---
elif menu == "Cierre de Caja":
    st.header("📈 Cierre de Caja (Día Actual)")
    v = supabase.table("ventas").select("*").execute()
    g = supabase.table("gastos").select("*").execute()
    
    df_v = pd.DataFrame(v.data)
    df_g = pd.DataFrame(g.data)
    
    if not df_v.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Efectivo Total ($)", f"${df_v['pago_efectivo'].sum():.2f}")
        c2.metric("Punto/Móvil ($)", f"${(df_v['pago_punto'].sum() + df_v['pago_movil'].sum()):.2f}")
        c3.metric("Zelle ($)", f"${df_v['pago_zelle'].sum():.2f}")
        c4.metric("Gastos ($)", f"${df_g['monto_usd'].sum() if not df_g.empty else 0:.2f}")
        
        total_ingreso = df_v['total_usd'].sum()
        total_egreso = df_g['monto_usd'].sum() if not df_g.empty else 0
        st.divider()
        st.subheader(f"Balance Neto: ${total_ingreso - total_egreso:.2f}")
    else:
        st.warning("No hay datos registrados aún.")
