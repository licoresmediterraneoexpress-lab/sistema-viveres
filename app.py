import streamlit as st
from supabase import create_client, Client
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO VISUAL
st.set_page_config(page_title="Sistema de Ventas - Mi Negocio", layout="wide")

# CSS Personalizado para Colores Azul Rey, Naranja y Blanco
st.markdown(f"""
    <style>
    /* Fondo principal y textos */
    .stApp {{
        background-color: #FFFFFF;
    }}
    /* Barra lateral Azul Rey */
    [data-testid="stSidebar"] {{
        background-color: #0041C2;
        color: white;
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    /* Títulos y Métricas */
    h1, h2, h3, .stMetric {{
        color: #0041C2 !important;
    }}
    /* Botones en Naranja */
    div.stButton > button:first-child {{
        background-color: #FF8C00;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }}
    div.stButton > button:hover {{
        background-color: #E07B00;
        color: white;
    }}
    /* Estilo de los cuadros de información */
    .stAlert {{
        border-radius: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. SEGURIDAD (Login simple)
def verificar_password():
    if "password_correct" not in st.session_state:
        # Logo en la pantalla de inicio de sesión
        if os.path.exists("logo.png"):
            st.image("logo.png", width=200)
        else:
            st.title("🏪 Mi Negocio")
            
        st.subheader("🔐 Acceso al Sistema")
        pwd = st.text_input("Contraseña de administrador", type="password")
        if st.button("Ingresar"):
            if pwd == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

if not verificar_password():
    st.stop()

# 3. CONEXIÓN A SUPABASE
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error de conexión: Revisa tus credenciales.")
    st.stop()

# --- BARRA LATERAL (Azul Rey con Logo) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.title("🏪 MI NEGOCIO")
    
    st.divider()
    menu = st.selectbox("📌 MENÚ PRINCIPAL", ["Inicio", "Punto de Venta", "Inventario", "Gastos", "Cierre de Caja"])
    st.divider()
    tasa = st.number_input("Tasa del Día (BS/$)", value=60.0, min_value=1.0)

# --- MÓDULO 1: INICIO ---
if menu == "Inicio":
    st.title("🚀 Panel de Control")
    
    # Obtener datos
    v = supabase.table("ventas").select("*").execute()
    df_v = pd.DataFrame(v.data)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Ventas Totales ($)", f"${df_v['total_usd'].sum() if not df_v.empty else 0:.2f}")
    with c2:
        st.metric("Operaciones", len(df_v))
    with c3:
        # Alerta de stock naranja
        res_stock = supabase.table("inventario").select("nombre").lt("stock", 6).execute()
        st.metric("Alertas Stock", len(res_stock.data), delta_color="inverse")

    st.markdown("### 📝 Historial Reciente")
    if not df_v.empty:
        st.dataframe(df_v.sort_values("fecha", ascending=False).head(10), use_container_width=True)

# --- MÓDULO 2: PUNTO DE VENTA ---
elif menu == "Punto de Venta":
    st.header("💰 Punto de Venta")
    
    res_inv = supabase.table("inventario").select("*").execute()
    productos = res_inv.data
    
    if not productos:
        st.warning("No hay productos registrados.")
    else:
        col_prod, col_cant = st.columns([3, 1])
        with col_prod:
            prod_sel_nombre = st.selectbox("Buscar Producto", [p['nombre'] for p in productos])
        
        p_data = next(item for item in productos if item["nombre"] == prod_sel_nombre)
        
        with col_cant:
            cant = st.number_input("Cant.", min_value=1, max_value=int(p_data['stock']))
        
        total_a_pagar = float(p_data['precio_detal']) * cant
        
        # Banner de total llamativo
        st.markdown(f"""
            <div style="background-color: #FF8C00; padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">TOTAL A COBRAR: ${total_a_pagar:.2f}</h2>
                <p style="color: white; margin: 0;">Equivalente: {(total_a_pagar * tasa):.2f} BS</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("---")
        
        # Gestión de Pagos
        if "pagos_acumulados" not in st.session_state:
            st.session_state.pagos_acumulados = []

        c1, c2, c3 = st.columns([2, 2, 1])
        metodo = c1.selectbox("Método", ["Efectivo $", "Efectivo BS", "Pago Móvil", "Zelle", "Punto de Venta"])
        monto_pago = c2.number_input("Monto", min_value=0.0)
        
        if c3.button("➕ Añadir"):
            if monto_pago > 0:
                st.session_state.pagos_acumulados.append({"metodo": metodo, "monto": monto_pago})
                st.rerun()

        # Resumen de pagos recibidos
        total_recibido_usd = 0
        pago_detalles = {"pago_efectivo": 0, "pago_punto": 0, "pago_movil": 0, "pago_zelle": 0, "pago_otros": 0}

        for p in st.session_state.pagos_acumulados:
            monto_en_usd = p['monto'] / tasa if "BS" in p['metodo'] or "Móvil" in p['metodo'] or "Punto" in p['metodo'] else p['monto']
            total_recibido_usd += monto_en_usd
            
            if "Efectivo" in p['metodo']: pago_detalles["pago_efectivo"] += monto_en_usd
            elif "Punto" in p['metodo']: pago_detalles["pago_punto"] += monto_en_usd
            elif "Móvil" in p['metodo']: pago_detalles["pago_movil"] += monto_en_usd
            elif "Zelle" in p['metodo']: pago_detalles["pago_zelle"] += monto_en_usd
            
            st.write(f"🔸 {p['metodo']}: {p['monto']:.2f} (Ref: ${monto_en_usd:.2f})")

        restante = total_a_pagar - total_recibido_usd
        
        if restante > 0.01:
            st.error(f"Falta por cobrar: ${restante:.2f}")
        else:
            st.success("¡Cobro completo!")
            if st.button("🚀 FINALIZAR VENTA"):
                supabase.table("inventario").update({"stock": p_data['stock'] - cant}).eq("id", p_data["id"]).execute()
                data_venta = {
                    "producto": prod_sel_nombre, "cantidad": cant, "total_usd": total_a_pagar,
                    "tasa_cambio": tasa, **pago_detalles
                }
                supabase.table("ventas").insert(data_venta).execute()
                st.session_state.pagos_acumulados = []
                st.balloons()
                st.rerun()

# --- MÓDULO 3, 4 y 5 (Simplificados para brevedad, mantienen la lógica anterior) ---
elif menu == "Inventario":
    st.header("📦 Inventario")
    with st.expander("Nuevo Producto"):
        with st.form("inv_form"):
            n = st.text_input("Nombre")
            s = st.number_input("Stock", min_value=0)
            p = st.number_input("Precio $")
            if st.form_submit_button("Guardar"):
                supabase.table("inventario").insert({"nombre":n, "stock":s, "precio_detal":p}).execute()
                st.rerun()
    res = supabase.table("inventario").select("*").execute()
    st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif menu == "Gastos":
    st.header("💸 Gastos")
    with st.form("g"):
        d = st.text_input("Descripción")
        m = st.number_input("Monto $")
        if st.form_submit_button("Registrar Gasto"):
            supabase.table("gastos").insert({"descripcion": d, "monto_usd": m}).execute()
            st.success("Registrado")

elif menu == "Cierre de Caja":
    st.header("📈 Cierre de Caja")
    v = supabase.table("ventas").select("*").execute()
    g = supabase.table("gastos").select("*").execute()
    df_v, df_g = pd.DataFrame(v.data), pd.DataFrame(g.data)
    
    if not df_v.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo", f"${df_v['pago_efectivo'].sum():.2f}")
        c2.metric("Banco", f"${(df_v['pago_punto'].sum() + df_v['pago_movil'].sum()):.2f}")
        c3.metric("Zelle", f"${df_v['pago_zelle'].sum():.2f}")
        st.divider()
        st.subheader(f"Balance: ${df_v['total_usd'].sum() - (df_g['monto_usd'].sum() if not df_g.empty else 0):.2f}")
