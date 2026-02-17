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

# ============================================
# MÓDULO 1: INVENTARIO MEJORADO
# ============================================
if opcion == "📦 INVENTARIO":
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    # Categorías predefinidas
    CATEGORIAS = [
        "Licores", "Cervezas", "Vinos", "Refrescos", "Aguas",
        "Víveres", "Confitería", "Snacks", "Lácteos", "Otros"
    ]
    
    try:
        # Cargar datos (con soporte offline)
        if st.session_state.online_mode:
            response = db.table("inventario").select("*").order("nombre").execute()
            df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
            OfflineManager.guardar_datos_local('inventario', df.to_dict('records'))
        else:
            datos_local = OfflineManager.obtener_datos_local('inventario')
            df = pd.DataFrame(datos_local) if datos_local else pd.DataFrame()
        
        # Verificar si existe columna categoria, si no, agregarla
        if not df.empty and 'categoria' not in df.columns:
            df['categoria'] = 'Otros'
        
        # Pestañas principales
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Ver Inventario", "➕ Agregar Producto", "📊 Estadísticas", "📥 Respaldos"])
        
        # ============================================
        # TAB 1: VER INVENTARIO (MEJORADO)
        # ============================================
        with tab1:
            # Filtros avanzados
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1])
            
            with col_f1:
                busqueda = st.text_input("🔍 Buscar producto", placeholder="Nombre o código...")
            
            with col_f2:
                categoria_filtro = st.selectbox("Categoría", ["Todas"] + CATEGORIAS)
            
            with col_f3:
                ver_bajo_stock = st.checkbox("⚠️ Solo stock bajo")
            
            with col_f4:
                if st.button("📤 Exportar a Excel", use_container_width=True):
                    if not df.empty:
                        export_df = df[['nombre', 'categoria', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']].copy()
                        export_df.columns = ['Producto', 'Categoría', 'Stock', 'Costo $', 'Precio Detal $', 'Precio Mayor $', 'Min. Mayor']
                        href = exportar_excel(export_df, f"inventario_{datetime.now().strftime('%Y%m%d')}")
                        st.markdown(href, unsafe_allow_html=True)
            
            if not df.empty:
                # Aplicar filtros
                df_filtrado = df.copy()
                
                if busqueda:
                    df_filtrado = df_filtrado[
                        df_filtrado['nombre'].str.contains(busqueda, case=False, na=False) |
                        df_filtrado.get('codigo_barras', '').astype(str).str.contains(busqueda, case=False, na=False)
                    ]
                
                if categoria_filtro != "Todas":
                    df_filtrado = df_filtrado[df_filtrado['categoria'] == categoria_filtro]
                
                if ver_bajo_stock:
                    df_filtrado = df_filtrado[df_filtrado['stock'] < 5]
                    st.warning(f"⚠️ Hay {len(df_filtrado)} productos con stock bajo")
                
                # Mostrar tabla con colores según stock
                def colorear_stock(val):
                    if val < 5:
                        return 'color: red; font-weight: bold; background-color: #ffe6e6'
                    elif val < 10:
                        return 'color: orange; font-weight: bold;'
                    return 'color: green; font-weight: bold;'
                
                # Preparar DataFrame para mostrar
                df_mostrar = df_filtrado[['nombre', 'categoria', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']].copy()
                df_mostrar.columns = ['Producto', 'Categoría', 'Stock', 'Costo $', 'Detal $', 'Mayor $', 'Mín. Mayor']
                
                # Aplicar estilo
                styled_df = df_mostrar.style.applymap(colorear_stock, subset=['Stock'])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Mostrar total de productos
                st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} productos")
                
                # ============================================
                # EDITAR PRODUCTO
                # ============================================
                st.divider()
                st.subheader("✏️ Editar producto")
                
                if not df_filtrado.empty:
                    producto_editar = st.selectbox("Seleccionar producto", df_filtrado['nombre'].tolist(), key="editar")
                    if producto_editar:
                        prod = df[df['nombre'] == producto_editar].iloc[0]
                        with st.form("form_editar"):
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                nuevo_nombre = st.text_input("Nombre", value=prod['nombre'])
                                nueva_categoria = st.selectbox("Categoría", CATEGORIAS, 
                                                              index=CATEGORIAS.index(prod.get('categoria', 'Otros')) if prod.get('categoria', 'Otros') in CATEGORIAS else 9)
                                nuevo_stock = st.number_input("Stock", value=float(prod['stock']), min_value=0.0, step=1.0)
                                nuevo_costo = st.number_input("Costo $", value=float(prod['costo']), min_value=0.0, step=0.01)
                                nuevo_codigo = st.text_input("Código de barras", value=prod.get('codigo_barras', ''))
                            with col_e2:
                                nuevo_detal = st.number_input("Precio Detal $", value=float(prod['precio_detal']), min_value=0.0, step=0.01)
                                nuevo_mayor = st.number_input("Precio Mayor $", value=float(prod['precio_mayor']), min_value=0.0, step=0.01)
                                nuevo_min = st.number_input("Mín. Mayor", value=int(prod['min_mayor']), min_value=1, step=1)
                            
                            if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                                try:
                                    datos_actualizados = {
                                        "nombre": nuevo_nombre,
                                        "categoria": nueva_categoria,
                                        "stock": nuevo_stock,
                                        "costo": nuevo_costo,
                                        "precio_detal": nuevo_detal,
                                        "precio_mayor": nuevo_mayor,
                                        "min_mayor": nuevo_min
                                    }
                                    if nuevo_codigo:
                                        datos_actualizados["codigo_barras"] = nuevo_codigo
                                    
                                    if st.session_state.online_mode:
                                        db.table("inventario").update(datos_actualizados).eq("id", prod['id']).execute()
                                    else:
                                        # Modo offline: guardar operación pendiente
                                        if 'operaciones_pendientes' not in st.session_state:
                                            st.session_state.operaciones_pendientes = []
                                        st.session_state.operaciones_pendientes.append({
                                            'tipo': 'update',
                                            'tabla': 'inventario',
                                            'datos': datos_actualizados,
                                            'id_field': 'id',
                                            'id_value': prod['id']
                                        })
                                    
                                    st.success("✅ Producto actualizado")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                
                # ============================================
                # ELIMINAR PRODUCTO
                # ============================================
                st.divider()
                st.subheader("🗑️ Eliminar producto")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    producto_eliminar = st.selectbox("Seleccionar producto", [""] + df['nombre'].tolist(), key="eliminar")
                with col_d2:
                    clave = st.text_input("Clave Admin", type="password", key="clave_eliminar")
                
                if producto_eliminar and st.button("❌ Eliminar", type="primary", use_container_width=True):
                    if clave == CLAVE_ADMIN:
                        try:
                            if st.session_state.online_mode:
                                db.table("inventario").delete().eq("nombre", producto_eliminar).execute()
                            else:
                                # Modo offline: marcar para eliminar
                                if 'operaciones_pendientes' not in st.session_state:
                                    st.session_state.operaciones_pendientes = []
                                st.session_state.operaciones_pendientes.append({
                                    'tipo': 'delete',
                                    'tabla': 'inventario',
                                    'id_field': 'nombre',
                                    'id_value': producto_eliminar
                                })
                            
                            st.success(f"Producto '{producto_eliminar}' eliminado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Clave incorrecta")
            else:
                st.info("No hay productos en el inventario")
        
        # ============================================
        # TAB 2: AGREGAR PRODUCTO (MEJORADO)
        # ============================================
        with tab2:
            with st.form("nuevo_producto", clear_on_submit=True):
                st.markdown("### 📝 Datos del nuevo producto")
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    nombre = st.text_input("Nombre del producto *").upper()
                    categoria = st.selectbox("Categoría", CATEGORIAS)
                    stock = st.number_input("Stock inicial *", min_value=0.0, step=1.0, format="%.2f")
                    costo = st.number_input("Costo $ *", min_value=0.0, step=0.01, format="%.2f")
                    codigo_barras = st.text_input("Código de barras (opcional)")
                
                with col_a2:
                    precio_detal = st.number_input("Precio Detal $ *", min_value=0.0, step=0.01, format="%.2f")
                    precio_mayor = st.number_input("Precio Mayor $ *", min_value=0.0, step=0.01, format="%.2f")
                    min_mayor = st.number_input("Mínimo para Mayor *", min_value=1, value=6, step=1)
                
                st.markdown("---")
                
                if st.form_submit_button("📦 Registrar Producto", use_container_width=True):
                    if not nombre:
                        st.error("El nombre es obligatorio")
                    elif stock < 0 or costo < 0 or precio_detal <= 0:
                        st.error("Verifique los valores ingresados")
                    else:
                        try:
                            # Verificar si ya existe
                            if st.session_state.online_mode:
                                existe = db.table("inventario").select("*").eq("nombre", nombre).execute()
                                if existe.data:
                                    st.error(f"Ya existe un producto con el nombre '{nombre}'")
                                    st.stop()
                            
                            datos_nuevos = {
                                "nombre": nombre,
                                "categoria": categoria,
                                "stock": stock,
                                "costo": costo,
                                "precio_detal": precio_detal,
                                "precio_mayor": precio_mayor,
                                "min_mayor": min_mayor
                            }
                            if codigo_barras:
                                datos_nuevos["codigo_barras"] = codigo_barras
                            
                            if st.session_state.online_mode:
                                db.table("inventario").insert(datos_nuevos).execute()
                            else:
                                # Modo offline: guardar operación pendiente
                                if 'operaciones_pendientes' not in st.session_state:
                                    st.session_state.operaciones_pendientes = []
                                st.session_state.operaciones_pendientes.append({
                                    'tipo': 'insert',
                                    'tabla': 'inventario',
                                    'datos': datos_nuevos
                                })
                            
                            st.success(f"✅ Producto '{nombre}' registrado exitosamente")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar: {e}")
        
        # ============================================
        # TAB 3: ESTADÍSTICAS (MEJORADAS)
        # ============================================
        with tab3:
            if not df.empty:
                # Métricas generales
                valor_inv = (df['stock'] * df['costo']).sum()
                valor_venta = (df['stock'] * df['precio_detal']).sum()
                bajo_stock = len(df[df['stock'] < 5])
                total_productos = len(df)
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Total productos", total_productos)
                col_m2.metric("Valor inventario (costo)", formatear_usd(valor_inv))
                col_m3.metric("Valor venta potencial", formatear_usd(valor_venta))
                col_m4.metric("Stock bajo", bajo_stock, delta_color="inverse")
                
                # Ganancia potencial
                ganancia_potencial = valor_venta - valor_inv
                st.metric("💰 Ganancia potencial total", formatear_usd(ganancia_potencial),
                         delta=f"{(ganancia_potencial/valor_inv*100):.1f}%" if valor_inv else "")
                
                # Estadísticas por categoría
                st.subheader("📊 Productos por categoría")
                if 'categoria' in df.columns:
                    cat_stats = df.groupby('categoria').agg({
                        'nombre': 'count',
                        'stock': 'sum',
                        'costo': lambda x: (x * df.loc[x.index, 'stock']).sum()
                    }).round(2)
                    cat_stats.columns = ['Cantidad', 'Stock total', 'Valor total $']
                    st.dataframe(cat_stats, use_container_width=True)
                
                # Top 10 productos más valiosos
                st.subheader("💰 Top 10 productos por valor en inventario")
                df['valor_total'] = df['stock'] * df['costo']
                df_top = df.nlargest(10, 'valor_total')[['nombre', 'categoria', 'stock', 'costo', 'valor_total']]
                df_top.columns = ['Producto', 'Categoría', 'Stock', 'Costo unitario', 'Valor total']
                st.dataframe(df_top, use_container_width=True, hide_index=True)
                
                # Productos con stock bajo
                st.subheader("⚠️ Productos con stock bajo (<5)")
                df_bajo = df[df['stock'] < 5][['nombre', 'categoria', 'stock', 'costo']]
                if not df_bajo.empty:
                    df_bajo.columns = ['Producto', 'Categoría', 'Stock', 'Costo unitario']
                    st.dataframe(df_bajo, use_container_width=True, hide_index=True)
                else:
                    st.success("No hay productos con stock bajo")
            else:
                st.info("No hay datos para mostrar estadísticas")
        
        # ============================================
        # TAB 4: RESPALDOS
        # ============================================
        with tab4:
            st.subheader("📥 Respaldo de inventario")
            st.markdown("""
                <div style='background-color: #e7f3ff; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                    <p>Desde aquí puedes exportar todo tu inventario para tener un respaldo físico.</p>
                    <p>Recomendación: Haz un respaldo diario antes de cerrar.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if not df.empty:
                col_r1, col_r2 = st.columns(2)
                
                with col_r1:
                    st.markdown("**📊 Respaldo completo**")
                    if st.button("📥 Exportar inventario completo", use_container_width=True):
                        export_df = df[['nombre', 'categoria', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']].copy()
                        export_df.columns = ['Producto', 'Categoría', 'Stock', 'Costo $', 'Precio Detal $', 'Precio Mayor $', 'Min. Mayor']
                        export_df = export_df.sort_values('Producto')
                        href = exportar_excel(export_df, f"inventario_completo_{datetime.now().strftime('%Y%m%d_%H%M')}")
                        st.markdown(href, unsafe_allow_html=True)
                
                with col_r2:
                    st.markdown("**📋 Lista de precios**")
                    if st.button("📥 Exportar lista de precios", use_container_width=True):
                        precio_df = df[['nombre', 'categoria', 'precio_detal', 'precio_mayor', 'min_mayor']].copy()
                        precio_df.columns = ['Producto', 'Categoría', 'Precio Detal $', 'Precio Mayor $', 'Mín. Mayor']
                        precio_df = precio_df.sort_values('Categoría')
                        href = exportar_excel(precio_df, f"lista_precios_{datetime.now().strftime('%Y%m%d')}")
                        st.markdown(href, unsafe_allow_html=True)
                
                # Información del respaldo
                st.divider()
                st.markdown(f"""
                    **📌 Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}  
                    **📦 Total de productos:** {len(df)}  
                    **🏷️ Categorías:** {df['categoria'].nunique() if 'categoria' in df.columns else 0}
                """)
            else:
                st.info("No hay productos para respaldar")
                
    except Exception as e:
        st.error(f"Error en inventario: {e}")
        st.exception(e)
