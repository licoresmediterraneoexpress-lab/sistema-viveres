import streamlit as st
import os

# 1. INSTALACIÓN AUTOMÁTICA DE PIEZAS (Por si acaso)
try:
    from supabase import create_client, Client
except ImportError:
    st.error("Falta instalar la conexión. Por favor ejecuta: pip install supabase")
    st.stop()

# 2. CONFIGURACIÓN DE TU BASE DE DATOS (Pega tus datos aquí)
# Sustituye lo que está entre comillas por tus llaves reales
URL_SUPABASE = "TU_URL_AQUÍ" 
KEY_SUPABASE = "TU_LLAVE_AQUÍ"

try:
    supabase = create_client(URL_SUPABASE, KEY_SUPABASE)
except:
    st.error("Error en las llaves de Supabase. Verifica que estén bien pegadas.")

# 3. BUSCADOR DE LOGO AUTOMÁTICO
# El código buscará cualquier imagen que se llame logo o tenga formato png/jpg
posibles_logos = ["logo.png", "logo.jpg", "logo.jpeg", "LOGO.PNG"]
logo_encontrado = None

for nombre in posibles_logos:
    if os.path.exists(nombre):
        logo_encontrado = nombre
        break

# --- DISEÑO ---
st.set_page_config(page_title="Mi Negocio", layout="wide")

# Colores Azul Rey y Naranja
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- MOSTRAR LOGO ---
if logo_encontrado:
    st.sidebar.image(logo_encontrado, use_container_width=True)
else:
    st.sidebar.warning("⚠️ No encontré el logo. Asegúrate que esté en la carpeta.")

st.sidebar.title("🏪 MENÚ PRINCIPAL")
opcion = st.sidebar.selectbox("Ir a:", ["Ventas", "Inventario", "Cierre"])

st.title("🚀 Sistema de Ventas")
st.write("Si ves esto, ¡el sistema ya funciona!")
