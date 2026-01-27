import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

# ==========================================
# 🔑 PEGA AQUÍ TUS CÓDIGOS DE SUPABASE
# ==========================================
URL_SUPABASE = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

# ==========================================

# Conexión a la base de datos
try:
    supabase = create_client(URL_SUPABASE, KEY_SUPABASE)
except:
    st.error("Error al conectar con Supabase. Revisa tus llaves.")

# Estilo personalizado (Azul Rey y Naranja)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; width: 100%; }
    .titulo-negocio { color: #FF8C00; font-size: 28px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# BARRA LATERAL
with st.sidebar:
    st.markdown('<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    st.write("---")
    menu = st.radio("MENÚ PRINCIPAL", ["Nueva Venta", "Inventario", "Reporte de Ventas"])

# CUERPO DEL SISTEMA
st.title(f"🚀 {menu}")

if menu == "Nueva Venta":
    st.write("Aquí podrás registrar ventas que se guardarán en Supabase.")
    # (Aquí iremos agregando la lógica para guardar datos reales)

elif menu == "Inventario":
    st.write("Aquí verás los productos guardados en tu base de datos.")

elif menu == "Reporte de Ventas":
    st.write("Historial de ventas real.")
