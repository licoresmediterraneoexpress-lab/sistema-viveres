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

# --- MÓDULO 2: PUNTO DE VENTA (PAGOS MIXTOS) ---
elif menu == "Punto de Venta":
    st.header("💰 Nueva Venta con Pagos Mixtos")
    
    # 1. Selección de Producto
    res = supabase.table("inventario").select("*").execute()
    productos = res.data
    
    col_a, col_b = st.columns(2)
    with col_a:
        prod_sel = st.selectbox("Seleccione Producto", [p['nombre'] for p in productos])
    with col_b:
        cant = st.number_input("Cantidad", min_value=1)
    
    p_data = next(item for item in productos if item["nombre"] == prod_sel)
    total_a_pagar = p_data['precio_detal'] * cant
    total_bs = total_a_pagar * tasa
    
    st.warning(f"### Total a cobrar: ${total_a_pagar:.2f} ({total_bs:.2f} BS)")
    st.divider()

    # 2. GESTIÓN DE PAGOS MIXTOS
    st.subheader("💳 Registrar Pagos")
    
    if "pagos_acumulados" not in st.session_state:
        st.session_state.pagos_acumulados = []

    c1, c2, c3 = st.columns([2, 2, 1])
    metodo = c1.selectbox("Método de Pago", ["Efectivo $", "Efectivo BS", "Pago Móvil", "Zelle", "Punto de Venta", "Otros"])
    monto_pago = c2.number_input("Monto a entregar", min_value=0.0)
    
    if c3.button("Añadir Pago"):
        if monto_pago > 0:
            st.session_state.pagos_acumulados.append({"metodo": metodo, "monto": monto_pago})
        else:
            st.error("El monto debe ser mayor a 0")

    # Mostrar lista de pagos actuales
    total_recibido_usd = 0
    if st.session_state.pagos_acumulados:
        st.write("*Detalle de pagos:*")
        for i, p in enumerate(st.session_state.pagos_acumulados):
            # Convertimos a USD para la suma total si el pago fue en BS
            monto_en_usd = p['monto'] / tasa if "BS" in p['metodo'] or "Móvil" in p['metodo'] else p['monto']
            total_recibido_usd += monto_en_usd
            st.write(f"- {p['metodo']}: {p['monto']:.2f} (Ref: ${monto_en_usd:.2f})")
        
        if st.button("Limpiar Pagos"):
            st.session_state.pagos_acumulados = []
            st.rerun()

    # 3. VERIFICACIÓN Y CIERRE
    restante = total_a_pagar - total_recibido_usd
    
    if restante > 0.01: # Usamos 0.01 por temas de decimales
        st.error(f"Faltan por pagar: ${restante:.2f}")
    else:
        st.success(f"¡Pago Completado! Cambio a devolver: ${abs(restante):.2f}")
        
        if st.button("Finalizar Venta e Imprimir Ticket"):
            # Guardar en Supabase (Guardamos los métodos usados en una sola columna de texto)
            metodos_texto = ", ".join([f"{x['metodo']}({x['monto']})" for x in st.session_state.pagos_acumulados])
            
            supabase.table("inventario").update({"stock": p_data['stock']-cant}).eq("id", p_data["id"]).execute()
            supabase.table("ventas").insert({
                "producto": prod_sel, 
                "cantidad": cant, 
                "total_usd": total_a_pagar,
                "metodo_pago": metodos_texto # Asegúrate de tener esta columna en Supabase
            }).execute()
            
            # Generar PDF (Ticket)
            pdf = FPDF(format=(80, 150))
            pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5, "TICKET DE VENTA", ln=True, align='C')
            pdf.set_font("Arial", "", 8)
            pdf.cell(0, 5, f"Producto: {prod_sel} x{cant}", ln=True)
            pdf.cell(0, 5, f"Total Facturado: ${total_a_pagar:.2f}", ln=True)
            pdf.cell(0, 5, "--- PAGOS RECIBIDOS ---", ln=True)
            for p in st.session_state.pagos_acumulados:
                pdf.cell(0, 5, f"{p['metodo']}: {p['monto']:.2f}", ln=True)
            pdf.cell(0, 5, "------------------------------------------", ln=True)
            
            pdf_bytes = pdf.output()
            st.download_button("📥 Descargar Ticket", data=pdf_bytes, file_name="ticket.pdf", mime="application/pdf")
            
            # Limpiar para la próxima venta
            st.session_state.pagos_acumulados = []



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


