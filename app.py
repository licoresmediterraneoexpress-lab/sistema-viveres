import streamlit as st
import pandas as pd
from supabase import create_client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mediterraneo Express - Sistema", layout="wide")

# 🔑 DATOS DE CONEXIÓN (Ya configurados)
URL_SUPABASE = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"

# Inicializar conexión
@st.cache_resource
def init_connection():
    return create_client(URL_SUPABASE, KEY_SUPABASE)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stSidebar"] { background-color: #0041C2; color: white; }
    .stButton>button { background-color: #FF8C00; color: white; border-radius: 10px; font-weight: bold; width: 100%; }
    .titulo-negocio { color: #FF8C00; font-size: 26px; font-weight: bold; text-align: center; margin-bottom: 20px; }
    h1, h2 { color: #0041C2; }
    </style>
    """, unsafe_allow_html=True)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<div class="titulo-negocio">MEDITERRANEO EXPRESS</div>', unsafe_allow_html=True)
    st.write("---")
    menu = st.radio("SECCIONES", ["📦 Inventario", "🛒 Ventas", "💸 Gastos"])

# --- SECCIÓN INVENTARIO ---
if menu == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    
    # Formulario para agregar productos
    with st.expander("➕ Registrar Nuevo Producto"):
        with st.form("form_registro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre del Producto")
                sto = st.number_input("Stock Inicial", min_value=0, step=1)
            with col2:
                p_detal = st.number_input("Precio Detal", min_value=0.0, format="%.2f")
                p_mayor = st.number_input("Precio Mayor", min_value=0.0, format="%.2f")
                m_mayor = st.number_input("Mínimo para Mayor", min_value=1, step=1)
            
            submit = st.form_submit_button("Guardar en Sistema")
            
            if submit:
                if nom:
                    datos = {
                        "nombre": nom, 
                        "stock": sto, 
                        "precio_detal": p_detal, 
                        "precio_mayor": p_mayor, 
                        "min_mayor": m_mayor
                    }
                    try:
                        supabase.table("inventario").insert(datos).execute()
                        st.success(f"✅ ¡{nom} agregado correctamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.warning("Por favor escribe el nombre del producto.")

    # Mostrar la tabla de productos
    st.subheader("Productos Disponibles")
    try:
        res = supabase.table("inventario").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Ordenamos las columnas según tu estructura
            cols = ["nombre", "stock", "precio_detal", "precio_mayor", "min_mayor"]
            # Solo mostramos las columnas si existen en la tabla
            df_mostrar = df[[c for c in cols if c in df.columns]]
            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay productos registrados en el inventario.")
    except Exception as e:
        st.error(f"Error al leer la tabla: {e}")

# --- SECCIÓN VENTAS (Próximo paso) ---
elif menu == "🛒 Ventas":
    st.header("🛒 Módulo de Ventas")
    st.info("Esta sección se conectará con el inventario automáticamente.")

# --- SECCIÓN GASTOS (Próximo paso) ---
elif menu == "💸 Gastos":
    st.header("💸 Registro de Gastos")
    st.write("Aquí podrás llevar el control de tus egresos.")
