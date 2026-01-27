import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO VISUAL
st.set_page_config(page_title="Sistema de Ventas - Mi Negocio", layout="wide")

# CSS Personalizado: Azul Rey (#0041C2), Naranja (#FF8C00) y Blanco
st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; }}
    
    /* Barra lateral Azul Rey */
    [data-testid="stSidebar"] {{
        background-color: #0041C2;
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    
    /* Títulos en Azul Rey */
    h1, h2, h3 {{ color: #0041C2 !important; font-family: 'Arial'; }}

    /* Botones en Naranja */
    div.stButton > button:first-child {{
        background-color: #FF8C00;
        color: white;
        border-radius: 10px;
        border: none;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }}
    
    /* Métricas */
    [data-testid="stMetricValue"] {{ color: #0041C2 !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIÓN PARA MOSTRAR LOGO
def mostrar_logo():
    if os.path.exists("logo.png"):
        # Esto centra el logo en la barra lateral
        st.sidebar.image("logo.png", use_container_width=True)
    else:
        st.sidebar.title("🏪 MI NEGOCIO")

# 3. SEGURIDAD
if "password_correct" not in st.session_state:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=300)
        st.subheader("🔐 Acceso al Sistema")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pwd == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Contraseña incorrecta")
    st.stop()

# 4. CONEXIÓN (Mantenemos tu lógica de secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- SIDEBAR ---
mostrar_logo()
st.sidebar.divider()
menu = st.sidebar.selectbox("📂 MENÚ", ["Inicio", "Punto de Venta", "Inventario", "Gastos", "Cierre de Caja"])
tasa = st.sidebar.number_input("Tasa del Día (BS/$)", value=60.0)

# --- LÓGICA DE MÓDULOS (Ejemplo Punto de Venta con Estilo) ---
if menu == "Inicio":
    st.title("🚀 Panel de Control")
    # ... (resto de tu lógica de métricas igual que antes)

elif menu == "Punto de Venta":
    st.header("💰 Punto de Venta")
    
    # Diseño de ticket visualmente atractivo
    with st.container():
        st.markdown("""
            <div style="background-color: #f0f2f6; padding: 20px; border-left: 10px solid #FF8C00; border-radius: 10px;">
                <h4 style="margin:0; color: #0041C2;">Nueva Operación</h4>
            </div>
        """, unsafe_allow_html=True)
        
        # Aquí continúa el código de selección de productos que ya tienes...
        # (Se mantiene la lógica de pagos mixtos del código anterior)

# --- NOTA: He mantenido la estructura para que solo copies y pegues ---
