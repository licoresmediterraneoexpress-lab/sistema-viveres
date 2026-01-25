import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Seguridad
def verificar_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso al Sistema")
        pwd = st.text_input("Contraseña del negocio", type="password")
        if st.button("Entrar"):
            if pwd == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Incorrecta")
        return False
    return True

if not verificar_password(): st.stop()

# 2. Conexión SQL
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- INTERFAZ ---
st.sidebar.title("🏪 Mi Negocio")
menu = st.sidebar.selectbox("Menú", ["Punto de Venta", "Inventario", "Cierre de Caja"])
tasa = st.sidebar.number_input("Tasa del Dólar (BS/USD)", value=1.0, min_value=1.0)

# --- NUEVO: ALERTAS DE STOCK BAJO ---
st.sidebar.write("---")
res_stock = supabase.table("inventario").select("nombre, stock").lt("stock", 6).execute()
if res_stock.data:
    st.sidebar.error("⚠️ PRODUCTOS BAJOS:")
    for p in res_stock.data:
        st.sidebar.warning(f"{p['nombre']}: quedan {p['stock']}")

# --- MÓDULO: INVENTARIO ---
if menu == "Inventario":
    st.header("📦 Gestión de Inventario")
    with st.form("nuevo_producto"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre del Producto")
        stock = c2.number_input("Cantidad inicial", min_value=0)
        p_detal = c1.number_input("Precio Detal ($)")
        p_mayor = c2.number_input("Precio Mayor ($)")
        min_mayor = st.number_input("Mínimo para precio mayor", value=6)
        if st.form_submit_button("Guardar Producto"):
            supabase.table("inventario").insert({"nombre": nombre, "stock": stock, "precio_detal": p_detal, "precio_mayor": p_mayor, "min_mayor": min_mayor}).execute()
            st.success("Guardado en la nube.")
    
    res = supabase.table("inventario").select("*").execute()
    st.dataframe(pd.DataFrame(res.data))

# --- MÓDULO: PUNTO DE VENTA (MULTIMÉTODO) ---
elif menu == "Punto de Venta":
    st.header("💰 Nueva Venta")
    res = supabase.table("inventario").select("*").execute()
    productos = res.data
    nombres = [p['nombre'] for p in productos]
    
    prod_sel = st.selectbox("Producto", nombres)
    cant = st.number_input("Cantidad", min_value=1)
    
    if prod_sel:
        p_data = next(item for item in productos if item["nombre"] == prod_sel)
        precio = p_data['precio_mayor'] if cant >= p_data['min_mayor'] else p_data['precio_detal']
        total_usd = precio * cant
        total_bs = total_usd * tasa
        
        st.warning(f"Total a Cobrar: ${total_usd:.2f} / {total_bs:.2f} BS")
        
        col1, col2 = st.columns(2)
        with col1:
            efectivo = st.number_input("Efectivo ($)", min_value=0.0)
            zelle = st.number_input("Zelle ($)", min_value=0.0)
        with col2:
            punto = st.number_input("Punto (BS)", min_value=0.0)
            pmovil = st.number_input("Pago Móvil (BS)", min_value=0.0)
        
        abonado = efectivo + zelle + ((punto + pmovil) / tasa)
        restante = total_usd - abonado
        
        if restante > 0.01: st.info(f"Faltan: ${restante:.2f}")
        else: st.success("✅ Pago completo")

        if st.button("Finalizar Venta"):
            if p_data['stock'] >= cant and restante <= 0.01:
                supabase.table("inventario").update({"stock": p_data['stock'] - cant}).eq("id", p_data["id"]).execute()
                supabase.table("ventas").insert({
                    "producto": prod_sel, "cantidad": cant, "total_usd": total_usd, "tasa_cambio": tasa,
                    "pago_efectivo": efectivo, "pago_zelle": zelle, "pago_punto": punto, "pago_movil": pmovil
                }).execute()
                st.success("Venta Exitosa")
                st.balloons()

# --- MÓDULO: CIERRE DE CAJA ---
elif menu == "Cierre de Caja":
    st.header("📈 Resumen del Día")
    res = supabase.table("ventas").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total USD", f"${df['total_usd'].sum():.2f}")
        col2.metric("Efectivo en Caja", f"${df['pago_efectivo'].sum():.2f}")
        col3.metric("Zelle", f"${df['pago_zelle'].sum():.2f}")
        
        st.write("---")
        st.subheader("Bolívares en Banco")
        st.info(f"Total Punto + Pago Móvil: {df['pago_punto'].sum() + df['pago_movil'].sum():.2f} BS")
        
        st.write("### Detalle de Ventas")
        st.dataframe(df[["fecha", "producto", "cantidad", "total_usd"]])
    else:
        st.write("No hay ventas hoy.")

