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
st.sidebar.title("Navegación")
menu = st.sidebar.selectbox("Ir a:", ["Punto de Venta", "Inventario", "Historial de Ventas"])
tasa = st.sidebar.number_input("Tasa del Dólar (BS/USD)", value=1.0, step=0.1)

# --- MÓDULO: INVENTARIO ---
if menu == "Inventario":
    st.header("📦 Gestión de Inventario")
    with st.form("nuevo_producto"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre del Producto")
        stock = c2.number_input("Cantidad inicial", min_value=0)
        p_detal = c1.number_input("Precio Detal ($)")
        p_mayor = c2.number_input("Precio Mayor ($)")
        min_mayor = st.number_input("Cantidad mínima para precio mayor", value=6)
        
        if st.form_submit_button("Guardar en SQL"):
            supabase.table("inventario").insert({
                "nombre": nombre, "stock": stock, 
                "precio_detal": p_detal, "precio_mayor": p_mayor, 
                "min_mayor": min_mayor
            }).execute()
            st.success(f"{nombre} guardado con éxito.")

    # Ver tabla de productos
    res = supabase.table("inventario").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        st.subheader("Productos en Estante")
        st.dataframe(df[["nombre", "stock", "precio_detal", "precio_mayor"]])

# --- MÓDULO: PUNTO DE VENTA ---
elif menu == "Punto de Venta":
    st.header("💰 Nueva Venta")
    
    # Obtener lista de productos para el buscador
    res = supabase.table("inventario").select("*").execute()
    productos = res.data
    nombres_productos = [p['nombre'] for p in productos]
    
    prod_sel = st.selectbox("Seleccionar Producto", nombres_productos)
    cant = st.number_input("Cantidad a vender", min_value=1, value=1)
    
    if prod_sel:
        # Buscar datos del producto seleccionado
        p_data = next(item for item in productos if item["nombre"] == prod_sel)
        
        # Lógica de precio Mayor vs Detal
        precio_usar = p_data['precio_mayor'] if cant >= p_data['min_mayor'] else p_data['precio_detal']
        total_usd = precio_usar * cant
        
        st.metric("Precio Unitario", f"${precio_usar}")
        st.subheader(f"Total a cobrar: ${total_usd:.2f}  /  {total_usd * tasa:.2f} BS")
        
        if st.button("Confirmar Venta"):
            if p_data['stock'] >= cant:
                # 1. Restar del inventario
                nuevo_stock = p_data['stock'] - cant
                supabase.table("inventario").update({"stock": nuevo_stock}).eq("id", p_data["id"]).execute()
                
                # 2. Guardar registro de venta
                supabase.table("ventas").insert({
                    "producto": prod_sel, "cantidad": cant, 
                    "total_usd": total_usd, "tasa_cambio": tasa
                }).execute()
                
                st.success("Venta realizada. Inventario actualizado.")
            else:
                st.error("No hay suficiente stock.")

# --- MÓDULO: REPORTES ---
elif menu == "Historial de Ventas":
    st.header("📈 Reporte de Ventas")
    res_v = supabase.table("ventas").select("*").execute()
    df_v = pd.DataFrame(res_v.data)
    if not df_v.empty:
        st.write(f"Total vendido: ${df_v['total_usd'].sum():.2f}")
        st.dataframe(df_v)
    else:
        st.write("Aún no hay ventas registradas.")
