import streamlit as st
import pandas as pd
from supabase import create_client

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema de Negocio", layout="wide")

# 🔑 TUS LLAVES (Verifica que sean las correctas)
URL_SUPABASE = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"


try:
    supabase = create_client(URL_SUPABASE, KEY_SUPABASE)
except:
    st.error("Error de conexión.")

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; }
    .titulo-negocio { color: #FF8C00; font-size: 24px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    menu = st.radio("SECCIONES", ["📦 Inventario", "🛒 Ventas"])

# --- SECCIÓN INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    
    with st.expander("➕ Agregar Nuevo Producto"):
        with st.form("form_inv"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre del Producto")
                sto = st.number_input("Stock Actual", min_value=0)
            with col2:
                p_detal = st.number_input("Precio Detal", min_value=0.0)
                p_mayor = st.number_input("Precio Mayor", min_value=0.0)
                m_mayor = st.number_input("Min. para Mayor", min_value=1)
            
            if st.form_submit_button("Guardar Producto"):
                # AJUSTADO A TUS NOMBRES CON GUION BAJO
                datos = {
                    "nombre": nom, 
                    "stock": sto, 
                    "precio_detal": p_detal, 
                    "precio_mayor": p_mayor, 
                    "min_mayor": m_mayor
                }
                try:
                    supabase.table("inventario").insert(datos).execute()
                    st.success(f"¡{nom} guardado con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # Mostrar tabla
    st.subheader("Productos en Almacén")
    res = supabase.table("inventario").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        # Seleccionamos solo las columnas importantes para mostrar
        columnas_visibles = ["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]
        st.dataframe(df[columnas_visibles], use_container_width=True)
    else:
        st.info("El inventario está vacío.")

