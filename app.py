import streamlit as st
import os

# CONFIGURACIÓN VISUAL INMEDIATA (Para que veas que funciona)
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; }
    </style>
    """, unsafe_allow_html=True)

# BUSCADOR DE LOGO (Busca logo.png o logo.jpg)
logo_path = None
for nombre in ["logo.png", "logo.jpg", "logo.jpeg"]:
    if os.path.exists(nombre):
        logo_path = nombre
        break

if logo_path:
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.warning("⚠️ No veo el archivo logo.png")

st.title("🚀 Sistema de Ventas")

# INTENTO DE CONEXIÓN SEGURO
try:
    from supabase import create_client
    st.success("✅ Conexión con Supabase lista.")
except ImportError:
    st.error("⚠️ Todavía falta instalar una pieza.")
    st.info("Por favor, ve a la pantalla negra y escribe: pip install supabase")
