import streamlit as st
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema de Ventas", layout="wide")

# 2. ESTILO PERSONALIZADO (Azul Rey y Naranja)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { 
        background-color: #0041C2; 
    }
    .titulo-negocio {mediterrano express
        color: #FF8C00;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border: 2px solid #FF8C00;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton>button { background-color: #FF8C00; color: white; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 3. BARRA LATERAL (Donde iba el logo, ahora va el nombre)
with st.sidebar:
    st.markdown('<div class="titulo-negocio">NOMBRE DE TU NEGOCIO</div>', unsafe_allow_html=True)
    st.title("🏪 MENÚ")
    opcion = st.radio("Ir a:", ["Ventas", "Inventario", "Reportes"])

# 4. CUERPO DEL SISTEMA
st.title(f"🚀 Bienvenido a {opcion}")

# INTENTO DE IMPORTAR SUPABASE SOLO CUANDO SE NECESITA
try:
    from supabase import create_client
    st.success("✅ Conexión establecida")
except ImportError:
    st.error("⚠️ Falta una pieza técnica (supabase).")
    st.info("Para arreglarlo, escribe en la pantalla negra: python -m pip install supabase")
