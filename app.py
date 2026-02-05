import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time

# --- 1. CONFIGURACIÓN INICIAL Y CONEXIÓN ---
st.set_page_config(page_title="Mediterraneo Express - Pro", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# Inicialización de estados globales
if 'car' not in st.session_state:
    st.session_state.car = []
if 'tasa_dia' not in st.session_state:
    st.session_state.tasa_dia = 60.0

# Estilos de Interfaz
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {border-radius: 8px; font-weight: bold; width: 100%;}
    .main-header {color: #0041C2; font-weight: bold; border-bottom: 2px solid #FF8C00;}
    .card {background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #FF8C00;}
</style>
""", unsafe_allow_html=True)

# --- 2. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO EXPRESS</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    st.info(f"Tasa Actual: {st.session_state.tasa_dia} Bs/$")

# --- 3. MÓDULO INVENTARIO (RESTAURADO) ---
if opcion == "📦 Inventario":
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    try:
        res = db.table("inventario").select("*").order("nombre").execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error DB: {e}")
        df_inv = pd.DataFrame()

    if not df_inv.empty:
        # Buscador Inteligente
        busc = st.text_input("🔍 Buscador de Productos", placeholder="Escriba el nombre del producto...")
        df_f = df_inv[df_inv['nombre'].str.contains(busc, case=False, na=False)] if busc else df_inv

        # Tabla de Existencias
        st.dataframe(
            df_f.rename(columns={
                'nombre': 'Producto', 'stock': 'Stock', 'costo': 'Costo',
                'precio_detal': 'Precio Detal', 'precio_mayor': 'Precio Mayor', 'min_mayor': 'Mín. Mayor'
            })[['Producto', 'Stock', 'Costo', 'Precio Detal', 'Precio Mayor', 'Mín. Mayor']],
            use_container_width=True, hide_index=True
        )

        # Acciones: Modificar / Eliminar
        st.markdown("### ⚙️ Panel de Modificación")
        col_mod1, col_mod2 = st.columns([2, 1])
        
        with col_mod1:
            prod_edit = st.selectbox("Seleccione Producto para editar:", df_f['nombre'].tolist(), index=None)
            if prod_edit:
                item = df_inv[df_inv['nombre'] == prod_edit].iloc[0]
                with st.form("edit_form"):
                    c1, c2, c3 = st.columns(3)
                    n_stock = c1.number_input("Stock Actual", value=float(item['stock']))
                    n_costo = c2.number_input("Costo $", value=float(item['costo']))
                    n_min = c3.number_input("Mín. Mayor", value=int(item['min_mayor']))
                    
                    c4, c5 = st.columns(2)
                    n_detal = c4.number_input("Precio Detal $", value=float(item['precio_detal']))
                    n_mayor = c5.number_input("Precio Mayor $", value=float(item['precio_mayor']))
                    
                    if st.form_submit_button("💾 ACTUALIZAR PRODUCTO"):
                        db.table("inventario").update({
                            "stock": n_stock, "costo": n_costo, "precio_detal": n_detal,
                            "precio_mayor": n_mayor, "min_mayor": n_min
                        }).eq("id", item['id']).execute()
                        st.success("Actualizado"); time.sleep(1); st.rerun()
