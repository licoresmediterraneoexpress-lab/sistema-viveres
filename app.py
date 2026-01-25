import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Seguridad
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

url = st.secrets["SUPABASE_URL"]; key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- BARRA LATERAL ---
st.sidebar.title("🏪 Mi Negocio")
menu = st.sidebar.selectbox("Menú", ["Punto de Venta", "Inventario", "Gastos", "Cierre de Caja"])
tasa = st.sidebar.number_input("Tasa (BS/$)", value=1.0, min_value=1.0)

# Alerta de Stock Bajo
res_stock = supabase.table("inventario").select("nombre, stock").lt("stock", 6).execute()
if res_stock.data:
    st.sidebar.error("⚠️ STOCK BAJO:")
    for p in res_stock.data: st.sidebar.write(f"- {p['nombre']}: {p['stock']}")

# --- MÓDULO: GASTOS ---
if menu == "Gastos":
    st.header("💸 Registro de Gastos")
    with st.form("nuevo_gasto"):
        desc = st.text_input("Descripción del gasto")
        monto = st.number_input("Monto en Dólares ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Servicios", "Personal", "Mercancía", "Local", "Otros"])
        if st.form_submit_button("Registrar Gasto"):
            supabase.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "categoria": cat}).execute()
            st.success("Gasto guardado.")

# --- MÓDULO: CIERRE DE CAJA (ACTUALIZADO) ---
elif menu == "Cierre de Caja":
    st.header("📈 Balance Total")
    
    # Obtener Ventas y Gastos
    v = supabase.table("ventas").select("*").execute()
    g = supabase.table("gastos").select("*").execute()
    df_v = pd.DataFrame(v.data)
    df_g = pd.DataFrame(g.data)
    
    total_ventas = df_v['total_usd'].sum() if not df_v.empty else 0
    total_gastos = df_g['monto_usd'].sum() if not df_g.empty else 0
    ganancia_neta = total_ventas - total_gastos
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ventas Totales", f"${total_ventas:.2f}")
    c2.metric("Gastos Totales", f"${total_gastos:.2f}", delta_color="inverse")
    c3.metric("GANANCIA REAL", f"${ganancia_neta:.2f}")
    
    st.write("---")
    if not df_g.empty:
        st.subheader("Detalle de Gastos")
        st.table(df_g[["fecha", "descripcion", "monto_usd", "categoria"]])

# (Aquí se mantienen los módulos de Inventario y Punto de Venta que ya tenías)
# --- MÓDULO: INVENTARIO ---
elif menu == "Inventario":
    st.header("📦 Inventario")
    with st.form("inv"):
        n = st.text_input("Nombre"); s = st.number_input("Stock", min_value=0)
        pd1 = st.number_input("Precio Detal"); pm = st.number_input("Precio Mayor")
        if st.form_submit_button("Guardar"):
            supabase.table("inventario").insert({"nombre":n, "stock":s, "precio_detal":pd1, "precio_mayor":pm}).execute()
    res = supabase.table("inventario").select("*").execute()
    st.dataframe(pd.DataFrame(res.data))

# --- MÓDULO: PUNTO DE VENTA ---
elif menu == "Punto de Venta":
    st.header("💰 Venta")
    res = supabase.table("inventario").select("*").execute()
    productos = res.data
    prod_sel = st.selectbox("Producto", [p['nombre'] for p in productos])
    cant = st.number_input("Cantidad", min_value=1)
    if prod_sel:
        p_data = next(item for item in productos if item["nombre"] == prod_sel)
        total_usd = (p_data['precio_detal'] * cant) # Simplificado para el ejemplo
        st.write(f"Total: ${total_usd}")
        if st.button("Cobrar"):
            supabase.table("inventario").update({"stock": p_data['stock']-cant}).eq("id", p_data["id"]).execute()
            supabase.table("ventas").insert({"producto": prod_sel, "cantidad": cant, "total_usd": total_usd}).execute()
            st.success("Vendido")
