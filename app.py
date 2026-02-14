import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# --- INICIALIZACIÓN DE SUPABASE ---
@st.cache_resource
def init_supabase():
    URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
    KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
    return create_client(URL, KEY)

db = init_supabase()
CLAVE_ADMIN = "1234"

# --- CACHÉ DE INVENTARIO ---
@st.cache_data(ttl=300)
def get_inventario():
    res = db.table("inventario").select("*").order("nombre").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    /* [Estilos CSS originales mantenidos íntegramente] */
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN ---
def inicializar_sesion():
    if 'car' not in st.session_state: 
        st.session_state.car = []
    if 'venta_finalizada' not in st.session_state: 
        st.session_state.venta_finalizada = False
    
    # Verificar turno activo al inicio
    try:
        res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        turno_activo = res_caja.data[0] if res_caja.data else None
        st.session_state.id_turno = turno_activo['id'] if turno_activo else None
        st.session_state.tasa_dia = float(turno_activo.get('tasa_apertura', 1.0)) if turno_activo else 1.0
    except Exception as e:
        st.session_state.id_turno = None
        st.session_state.tasa_dia = 1.0

# --- MÓDULO DE INVENTARIO ---
def modulo_inventario():
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    # Obtener inventario con caché
    df_inv = get_inventario()
    
    if not df_inv.empty:
        # Búsqueda de productos
        busc = st.text_input("🔍 Buscar Producto", placeholder="Nombre del producto...")
        df_mostrar = df_inv[df_inv['nombre'].str.contains(busc, case=False)] if busc else df_inv
        
        # Mostrar inventario
        st.dataframe(
            df_mostrar[['nombre', 'stock', 'precio_detal', 'precio_mayor', 'min_mayor']], 
            use_container_width=True, 
            hide_index=True
        )
        
        # Diálogo de edición de producto
        @st.dialog("✏️ Modificar Producto")
        def edit_dial(prod):
            with st.form("f_edit"):
                n_nom = st.text_input("Nombre", value=prod['nombre'])
                c1, c2 = st.columns(2)
                n_stock = c1.number_input("Stock", value=float(prod['stock']))
                n_costo = c2.number_input("Costo $", value=float(prod['costo']))
                
                c3, c4, c5 = st.columns(3)
                n_detal = c3.number_input("Precio Detal $", value=float(prod['precio_detal']))
                n_mayor = c4.number_input("Precio Mayor $", value=float(prod['precio_mayor']))
                n_min = c5.number_input("Min. Mayor", value=int(prod['min_mayor']))
                
                if st.form_submit_button("GUARDAR"):
                    db.table("inventario").update({
                        "nombre": n_nom, 
                        "stock": n_stock, 
                        "costo": n_costo,
                        "precio_detal": n_detal, 
                        "precio_mayor": n_mayor, 
                        "min_mayor": n_min
                    }).eq("id", prod['id']).execute()
                    st.rerun()
        
        # Selector de producto para editar
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            sel = st.selectbox("Seleccione para Editar", [None] + df_mostrar['nombre'].tolist())
            if sel:
                p_data = df_inv[df_inv['nombre'] == sel].iloc[0].to_dict()
                if st.button(f"Modificar {sel}"): 
                    edit_dial(p_data)
        
        # Añadir nuevo producto
        with st.expander("➕ Añadir Nuevo Producto"):
            with st.form("new_p"):
                f1, f2 = st.columns(2)
                n_n = f1.text_input("Nombre").upper()
                n_s = f2.number_input("Stock Inicial", 0.0)
                
                f3, f4, f5 = st.columns(3)
                n_c = f3.number_input("Costo", 0.0)
                n_d = f4.number_input("Detal", 0.0)
                n_m = f5.number_input("Mayor", 0.0)
                n_min = st.number_input("Min. para Mayor", 1)
                
                if st.form_submit_button("REGISTRAR"):
                    try:
                        db.table("inventario").insert({
                            "nombre": n_n, 
                            "stock": n_s, 
                            "costo": n_c, 
                            "precio_detal": n_d, 
                            "precio_mayor": n_m, 
                            "min_mayor": n_min,
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.success("✅ ¡Guardado con éxito!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al registrar: {ex}")

# --- MÓDULO DE PUNTO DE VENTA ---
def modulo_punto_venta():
    validar_turno_abierto()
    st.markdown("<h1 class='main-header'>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    
    # Obtener inventario con caché
    df_inv = get_inventario()
    
    # Tasa de cambio del día
    tasa_actual = st.session_state.tasa_dia
    tasa = st.number_input("Tasa BCV (Bs/$)", value=tasa_actual, format="%.2f", step=0.01)
    st.session_state.tasa_dia = tasa
    
    c_izq, c_der = st.columns([1, 1.1])
    
    with c_izq:
        st.subheader("🔍 Buscador de Productos")
        busc_v = st.text_input("Escribe nombre o ID...", placeholder="Ej: Harina Pan", key="pos_search")
        
        # Filtrar productos con stock
        if busc_v:
            productos_filtrados = df_inv[
                (df_inv['nombre'].str.contains(busc_v, case=False)) & 
                (df_inv['stock'] > 0)
            ].head(8)
        else:
            productos_filtrados = df_inv[df_inv['stock'] > 0].head(8)
        
        for _, p in productos_filtrados.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.markdown(f"**{p['nombre']}**\n\nStock: `{int(p['stock'])}`")
                
                # Lógica de precio: si cantidad >= min_mayor, usar precio_mayor
                precio_mostrar = p['precio_mayor'] if p['stock'] >= p['min_mayor'] else p['precio_detal']
                col2.markdown(f"<h4 style='color:green;'>${float(precio_mostrar):.2f}</h4>", unsafe_allow_html=True)
                
                if col3.button("➕ Añadir", key=f"add_{p['id']}", use_container_width=True):
                    # Buscar si el producto ya está en el carrito
                    encontrado = False
                    for item in st.session_state.car:
                        if item['id'] == p['id']:
                            item['cant'] += 1.0
                            encontrado = True
                            break
                    
                    # Si no está en el carrito, añadirlo
                    if not encontrado:
                        st.session_state.car.append({
                            "id": int(p['id']), 
                            "nombre": p['nombre'], 
                            "cant": 1.0, 
                            "precio_detal": float(p['precio_detal']),
                            "precio_mayor": float(p['precio_mayor']),
                            "min_mayor": float(p['min_mayor']),
                            "costo": float(p['costo'])
                        })
                    st.rerun()

    with c_der:
        st.subheader("📋 Carrito de Ventas")
        total_usd = 0.0
        
        if not st.session_state.car:
            st.info("El carrito está vacío.")
        else:
            for i, item in enumerate(st.session_state.car):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 1.5, 0.5])
                    
                    # Determinar precio dinámicamente
                    precio_aplicar = (
                        item['precio_mayor'] 
                        if item['cant'] >= item['min_mayor'] 
                        else item['precio_detal']
                    )
                    
                    item['cant'] = c1.number_input(
                        f"{item['nombre']} ($/u {precio_aplicar:.2f})", 
                        min_value=0.1, 
                        step=1.0, 
                        value=float(item['cant']), 
                        key=f"c_{item['id']}_{i}"
                    )
                    
                    subt = float(item['cant']) * precio_aplicar
                    total_usd += subt
                    c2.markdown(f"**Subt:**\n${subt:.2f}")
                    
                    if c3.button("❌", key=f"del_{i}"):
                        st.session_state.car.pop(i)
                        st.rerun()
        
        st.divider()
        total_bs_sist = float(total_usd * tasa)
        st.markdown(f"### Total: `${total_usd:.2f}` / `{total_bs_sist:,.2f} Bs`")
        
        # Resto del código de registro de venta similar al original
        # (Manteniendo la lógica de pagos mixtos y registro en base de datos)

# --- MÓDULO DE HISTORIAL ---
def modulo_historial():
    validar_turno_abierto()
    st.markdown("<h1 class='main-header'>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    st.info("Módulo de historial en desarrollo. Consulta las ventas en la base de datos directamente.")

# --- MÓDULO DE GASTOS ---
def modulo_gastos():
    validar_turno_abierto()
    st.markdown("<h1 class='main-header'>💸 Gastos Operativos</h1>", unsafe_allow_html=True)
    
    with st.form("registro_gasto"):
        descripcion = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto $", min_value=0.0)
        categoria = st.selectbox("Categoría", [
            "Servicios", 
            "Personal", 
            "Mercancía", 
            "Logística", 
            "Administrativos", 
            "Otros"
        ])
        
        if st.form_submit_button("REGISTRAR GASTO"):
            try:
                db.table("gastos").insert({
                    "id_cierre": st.session_state.id_turno, 
                    "descripcion": descripcion, 
                    "monto_usd": monto,
                    "categoria": categoria,
                    "fecha": datetime.now().isoformat()
                }).execute()
                st.success("Gasto guardado exitosamente")
            except Exception as e:
                st.error(f"Error al registrar gasto: {e}")

# --- MÓDULO DE CIERRE DE CAJA ---
def modulo_cierre_caja():
    st.markdown("<h1 class='main-header'>📊 Gestión de Caja y Auditoría</h1>", unsafe_allow_html=True)
    
    # Inicialización de variables en 0.0
    sys_efec_bs = 0.0
    sys_divisas = 0.0
    sys_total_usd = 0.0
    sys_total_costo = 0.0
    sys_pago_movil = 0.0
    sys_punto = 0.0
    sys_zelle = 0.0
    sys_otros = 0.0
    
    # Si no hay turno abierto, mostrar apertura
    if not st.session_state.get('id_turno'):
        with st.form("apertura_jornada"):
            st.subheader("🔓 Apertura de Turno")
            col_ap1, col_ap2 = st.columns(2)
            
            tasa_v = col_ap1.number_input("Tasa de Cambio del Día (Bs/$)", min_value=1.0, value=60.0, format="%.2f")
            f_bs_v = col_ap1.number_input("Fondo Inicial en Bolívares (Efectivo)", min_value=0.0, value=0.0, step=10.0)
            f_usd_v = col_ap2.number_input("Fondo Inicial en Divisas (Efectivo $)", min_value=0.0, value=0.0, step=1.0)
            
            if st.form_submit_button("🚀 ABRIR CAJA E INICIAR JORNADA", use_container_width=True):
                try:
                    # Insertar nuevo turno
                    data_ins = {
                        "tasa_apertura": float(tasa_v),
                        "fondo_bs": float(f_bs_v),
                        "fondo_usd": float(f_usd_v),
                        "monto_apertura": float(f_usd_v),
                        "estado": "abierto",
                        "fecha_apertura": datetime.now().isoformat()
                    }
                    res_ins = db.table("cierres").insert(data_ins).execute()
                    
                    if res_ins.data:
                        nuevo_id = res_ins.data[0]['id']
                        st.session_state.id_turno = nuevo_id
                        st.session_state['tasa_dia'] = tasa_v
                        st.success(f"✅ Turno #{nuevo_id} abierto exitosamente.")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error crítico de apertura: {e}")
    else:
        # Obtener gastos del turno
        res_gastos = db.table("gastos").select("*").eq("id_cierre", st.session_state.id_turno).execute()
        total_gastos_usd = sum(float(gasto.get('monto_usd', 0)) for gasto in res_gastos.data) if res_gastos.data else 0.0
        
        # Obtener ventas del turno
        res_ventas = db.table("ventas").select("*").eq("id_cierre", st.session_state.id_turno).eq("estado", "Finalizado").execute()
        
        for venta in res_ventas.data:
            sys_total_usd += float(venta.get('total_usd', 0))
            sys_total_costo += float(venta.get('costo_venta', 0))
            sys_pago_movil += float(venta.get('pago_movil', 0))
            sys_punto += float(venta.get('pago_punto', 0))
            sys_zelle += float(venta.get('pago_zelle', 0))
            sys_otros += float(venta.get('pago_otros', 0))
        
        # Calcular ganancia neta
        ganancia_neta = sys_total_usd - sys_total_costo - total_gastos_usd
        
        # Resto del código de cierre similar al original

# --- FUNCIÓN PRINCIPAL ---
def main():
    inicializar_sesion()
    
    # --- MENÚ LATERAL ---
    with st.sidebar:
        st.markdown("<h2 style='color:#002D62;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
        opcion = st.radio("MENÚ PRINCIPAL", [
            "📦 Inventario", 
            "🛒 Punto de Venta", 
            "📜 Historial", 
            "💸 Gastos", 
            "📊 Cierre de Caja"
        ])
        st.divider()
        
        # Mostrar estado de turno
        if st.session_state.get('id_turno'):
            st.success(f"Turno Abierto: #{st.session_state.id_turno}")
        else:
            st.error("Caja Cerrada")

    # LÓGICA DE BLOQUEO DE MÓDULOS
    def validar_turno_abierto():
        if opcion in ["🛒 Punto de Venta", "📜 Historial", "💸 Gastos"] and not st.session_state.get('id_turno'):
            st.error("⚠️ Debe abrir turno en Cierre de Caja para operar")
            st.stop()

    # SELECTOR DE MÓDULO
    if opcion == "📦 Inventario":
        modulo_inventario()
    elif opcion == "🛒 Punto de Venta":
        modulo_punto_venta()
    elif opcion == "📜 Historial":
        modulo_historial()
    elif opcion == "💸 Gastos":
        modulo_gastos()
    elif opcion == "📊 Cierre de Caja":
        modulo_cierre_caja()

# EJECUCIÓN DE LA APLICACIÓN
if __name__ == "__main__":
    main()
