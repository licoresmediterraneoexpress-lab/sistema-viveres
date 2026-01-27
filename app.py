import streamlit as st
import os
import subprocess
import sys

# --- ESTO INSTALA LO QUE FALTA AUTOMÁTICAMENTE ---
def instalar_herramientas():
    try:
        import supabase
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
    try:
        import pandas
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])

instalar_herramientas()
from supabase import create_client

# --- CONFIGURACIÓN DE TU BASE DE DATOS ---
# REEMPLAZA ESTO CON TUS DATOS DE SUPABASE
URL_SUPABASE = "https://tu-proyecto.supabase.co" 
KEY_SUPABASE = "tu-llave-larga-aqui"

# --- DISEÑO (Azul Rey y Naranja) ---
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BUSCADOR DE LOGO INTELIGENTE ---
logo_path = None
# Busca archivos que se llamen logo en cualquier formato común
for nombre in ["logo.png", "logo.jpg", "logo.jpeg", "LOGO.PNG", "LOGO.JPG"]:
    if os.path.exists(nombre):
        logo_path = nombre
        break

if logo_path:
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.warning("⚠️ No encontré el logo. Asegúrate de que el archivo se llame logo.png o logo.jpg")

# --- CONTENIDO ---
st.sidebar.title("🏪 MENÚ")
opcion = st.sidebar.selectbox("Selecciona:", ["Inicio", "Ventas", "Inventario"])

st.title("🚀 Sistema de Ventas")
st.write(f"### Bienvenido al sistema")
st.info("Si estás viendo esto, el error de 'supabase' se ha solucionado automáticamente.")
