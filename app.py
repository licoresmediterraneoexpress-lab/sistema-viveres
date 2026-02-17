import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta
import time
import json
import hashlib
import base64
from io import BytesIO

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
st.set_page_config(
    page_title="BODEGÓN Y LICORERÍA MEDITERRANEO EXPRESS",
    page_icon="🥂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SISTEMA DE TEMA (OSCURO/CLARO)
# ============================================
if 'tema' not in st.session_state:
    st.session_state.tema = 'claro'

def aplicar_tema():
    if st.session_state.tema == 'oscuro':
        return """
            <style>
            .stApp {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            .main-header {
                color: #ffffff !important;
            }
            .stMarkdown, .stText, p, span, label, h1, h2, h3, h4 {
                color: #ffffff !important;
            }
            .stDataFrame {
                background-color: #2d2d2d;
            }
            </style>
        """
    else:
        return """
            <style>
            .stApp {
                background-color: #f8f9fa;
            }
            .main-header {
                color: #1e3c72 !important;
            }
            </style>
        """

st.markdown(aplicar_tema(), unsafe_allow_html=True)

# ============================================
# ESTILOS PERSONALIZADOS BASE
# ============================================
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
    }
    .product-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .badge-stock-bajo {
        background-color: #dc3545;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# SISTEMA OFFLINE (ALMACENAMIENTO LOCAL)
# ============================================
class OfflineManager:
    """Gestiona el almacenamiento local para modo offline"""
    
    @staticmethod
    def guardar_datos_local(tabla, datos):
        """Guarda datos en session_state como caché local"""
        if 'offline_data' not in st.session_state:
            st.session_state.offline_data = {}
        st.session_state.offline_data[tabla] = {
            'datos': datos,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def obtener_datos_local(tabla):
        """Obtiene datos de la caché local"""
        if 'offline_data' in st.session_state and tabla in st.session_state.offline_data:
            return st.session_state.offline_data[tabla]['datos']
        return None
    
    @staticmethod
    def sincronizar_pendientes(db):
        """Sincroniza operaciones pendientes con Supabase"""
        if 'operaciones_pendientes' not in st.session_state:
            return
        
        pendientes = st.session_state.operaciones_pendientes.copy()
        for op in pendientes:
            try:
                if op['tipo'] == 'insert':
                    db.table(op['tabla']).insert(op['datos']).execute()
                elif op['tipo'] == 'update':
                    db.table(op['tabla']).update(op['datos']).eq(op['id_field'], op['id_value']).execute()
                st.session_state.operaciones_pendientes.remove(op)
            except:
                pass  # Si falla, queda pendiente

# ============================================
# CONEXIÓN A SUPABASE
# ============================================
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

# Verificar conexión
try:
    db = create_client(URL, KEY)
    # Probar conexión
    db.table("inventario").select("*").limit(1).execute()
    st.session_state.db_connected = True
    st.session_state.online_mode = True
except Exception as e:
    st.session_state.db_connected = False
    st.session_state.online_mode = False
    st.warning("⚠️ Modo offline activado. Los cambios se guardarán localmente.")

# ============================================
# SISTEMA DE USUARIOS (RÁPIDO)
# ============================================
USUARIOS = {
    'admin': {'nombre': 'Administrador', 'clave': '1234', 'rol': 'admin'},
    'empleada': {'nombre': 'Empleada', 'clave': '5678', 'rol': 'empleado'}
}

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

def login(usuario, clave):
    if usuario in USUARIOS and USUARIOS[usuario]['clave'] == clave:
        st.session_state.usuario_actual = USUARIOS[usuario]
        return True
    return False

def logout():
    st.session_state.usuario_actual = None

# ============================================
# VERIFICAR TURNO ACTIVO
# ============================================
if st.session_state.online_mode:
    try:
        response = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        turno_activo = response.data[0] if response.data else None
        if turno_activo:
            st.session_state.id_turno = turno_activo['id']
            st.session_state.tasa_dia = turno_activo.get('tasa_apertura', 1.0)
            st.session_state.fondo_bs = turno_activo.get('fondo_bs', 0)
            st.session_state.fondo_usd = turno_activo.get('fondo_usd', 0)
        else:
            st.session_state.id_turno = None
    except Exception as e:
        st.session_state.id_turno = None
else:
    # Modo offline: usar datos locales
    if 'id_turno' not in st.session_state:
        st.session_state.id_turno = None
    if 'tasa_dia' not in st.session_state:
        st.session_state.tasa_dia = 60.0

# ============================================
# MENÚ LATERAL (REDISEÑADO)
# ============================================
with st.sidebar:
    # Logo y nombre (azul marino con letras blancas)
    st.markdown("""
        <div style="background: linear-gradient(135deg, #0a1929 0%, #1a2b3c 100%); 
                    padding: 2rem 1rem; 
                    border-radius: 0 0 20px 20px; 
                    text-align: center; 
                    margin-top: -1rem;
                    margin-bottom: 1rem;">
            <h1 style="color: white; margin: 0; font-size: 2.2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                🥂 BODEGÓN Y LICORERÍA
            </h1>
            <h2 style="color: #ffd700; margin: 0; font-size: 1.8rem; letter-spacing: 2px;">
                MEDITERRANEO EXPRESS
            </h2>
            <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem; font-style: italic;">
                Desde 2020 sirviendo con calidad
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Selector de tema
    col_tema1, col_tema2 = st.columns(2)
    with col_tema1:
        if st.button("☀️ Claro", use_container_width=True):
            st.session_state.tema = 'claro'
            st.rerun()
    with col_tema2:
        if st.button("🌙 Oscuro", use_container_width=True):
            st.session_state.tema = 'oscuro'
            st.rerun()
    
    st.divider()
    
    # Login rápido (si no hay usuario)
    if not st.session_state.usuario_actual:
        with st.expander("🔐 Acceso al sistema", expanded=True):
            col_user1, col_user2 = st.columns(2)
            with col_user1:
                usuario_sel = st.selectbox("Usuario", ["admin", "empleada"])
            with col_user2:
                clave_input = st.text_input("Clave", type="password")
            
            if st.button("✅ Ingresar", use_container_width=True):
                if login(usuario_sel, clave_input):
                    st.success(f"Bienvenido {st.session_state.usuario_actual['nombre']}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Clave incorrecta")
    else:
        st.success(f"👤 Usuario: {st.session_state.usuario_actual['nombre']}")
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()
    
    st.divider()
    
    # Tasa del día (EDITABLE)
    with st.container(border=True):
        st.markdown("**💱 TASA BCV**")
        nueva_tasa = st.number_input(
            "Bs/USD",
            min_value=1.0,
            max_value=999.0,
            value=float(st.session_state.get('tasa_dia', 60.0)),
            step=0.5,
            format="%.2f",
            key="tasa_input"
        )
        if st.button("Actualizar tasa", use_container_width=True):
            st.session_state.tasa_dia = nueva_tasa
            if st.session_state.online_mode and st.session_state.id_turno:
                try:
                    db.table("cierres").update({"tasa_apertura": nueva_tasa}).eq("id", st.session_state.id_turno).execute()
                except:
                    pass
            st.success("Tasa actualizada")
            time.sleep(1)
            st.rerun()
    
    st.divider()
    
    # Módulos
    opcion = st.radio(
        "MÓDULOS",
        ["📦 INVENTARIO", "🛒 PUNTO DE VENTA", "💸 GASTOS", "📜 HISTORIAL", "📊 CIERRE DE CAJA"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Estado del sistema
    if st.session_state.online_mode:
        st.success("✅ Conectado a Internet")
    else:
        st.warning("⚠️ Modo offline")
    
    if st.session_state.id_turno:
        st.info(f"📍 Turno activo: #{st.session_state.id_turno}")
    else:
        st.error("🔴 Caja cerrada")

# ============================================
# FUNCIONES AUXILIARES MEJORADAS
# ============================================
def requiere_turno():
    """Verifica si hay turno activo"""
    if not st.session_state.id_turno:
        st.warning("⚠️ No hay un turno activo. Debe abrir caja en el módulo 'Cierre de Caja'.")
        st.stop()

def requiere_usuario():
    """Verifica si hay usuario logueado"""
    if not st.session_state.usuario_actual:
        st.warning("⚠️ Debe iniciar sesión para acceder a este módulo.")
        st.stop()

def formatear_usd(valor):
    return f"${valor:,.2f}"

def formatear_bs(valor):
    return f"{valor:,.2f} Bs"

def exportar_excel(df, nombre_archivo):
    """Convierte DataFrame a Excel para descargar"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{nombre_archivo}.xlsx">📥 Descargar Excel</a>'
    return href
