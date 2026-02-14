import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

# --- 2. INYECCIÓN DE ESTILOS ---
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #F8F9FA;
    }

    /* BARRA LATERAL (MENU) - AZUL CLARO */
    [data-testid="stSidebar"] {
        background-color: #ADD8E6 !important;
        border-right: 1px solid #90C3D4;
    }

    /* LETRAS DEL MENU (Negras) */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #000000 !important;
        font-weight: 500;
    }

    /* TEXTOS GENERALES EN NEGRO */
    h1, h2, h3, h4, p, span, label {
        color: #000000 !important;
    }

    /* BOTÓN FINALIZAR (Azul Oscuro con Letras Blancas) */
    .stButton > button[kind="primary"] {
        background-color: #002D62 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* BOTONES DE ANULACIÓN (Rojo con Letras Blancas) */
    .stButton > button:contains("Anular"), 
    .stButton > button:contains("Eliminar") {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
    }

    /* TARJETAS DE CONTENEDORES (Blancas con sombra suave) */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }
    
    /* INPUTS (Cuadros de texto) */
    input {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN DE CONEXIÓN ---
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

db = create_client(URL, KEY)

# --- 4. FUNCIÓN GLOBAL PARA VALIDAR TURNO ---
def validar_turno_abierto(opcion_actual):
    """Verifica si hay un turno abierto."""
    if not st.session_state.get('id_turno'):
        st.warning(f"⚠️ ACCESO RESTRINGIDO A '{opcion_actual}'")
        st.info("Debe abrir la caja en el módulo 'Cierre de Caja' para operar.")
        st.stop()
    return True

# --- 5. ESTADO DE SESIÓN ---
if 'car' not in st.session_state:
    st.session_state.car = []
if 'venta_finalizada' not in st.session_state:
    st.session_state.venta_finalizada = False

# --- 6. VERIFICAR TURNO ACTIVO ---
try:
    res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
    turno_activo = res_caja.data[0] if res_caja.data else None
    id_turno = turno_activo['id'] if turno_activo else None
    st.session_state.id_turno = id_turno
    if turno_activo:
        st.session_state.tasa_dia = turno_activo.get('tasa_apertura', 1.0)
except Exception as e:
    turno_activo = None
    id_turno = None
    st.session_state.id_turno = None

# --- 7. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:#002D62;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MENÚ PRINCIPAL", ["📦 Inventario", "🛒 Punto de Venta", "📜 Historial", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    if id_turno:
        st.success(f"✅ Turno Activo: #{id_turno}")
        if turno_activo:
            st.info(f"Tasa: Bs {turno_activo.get('tasa_apertura', 1.0):.2f}/$")
    else:
        st.error("🔴 Caja Cerrada")

# ============================================
# MÓDULO 1: INVENTARIO
# ============================================
if opcion == "📦 Inventario":
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    try:
        res = db.table("inventario").select("*").order("nombre").execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        if not df_inv.empty:
            # Buscador
            busc = st.text_input("🔍 Buscar Producto", placeholder="Nombre del producto...")
            df_mostrar = df_inv[df_inv['nombre'].str.contains(busc, case=False)] if busc else df_inv

            # Mostrar inventario
            st.subheader("📋 Existencias Actuales")
            st.dataframe(
                df_mostrar[['nombre', 'stock', 'precio_detal', 'precio_mayor', 'min_mayor']], 
                use_container_width=True, 
                hide_index=True
            )

            # Editar producto
            col1, col2 = st.columns(2)
            with col1:
                sel = st.selectbox("✏️ Seleccionar para Editar", [None] + df_mostrar['nombre'].tolist())
                if sel:
                    p_data = df_inv[df_inv['nombre'] == sel].iloc[0].to_dict()
                    with st.form("editar_producto"):
                        st.subheader(f"Editando: {sel}")
                        nuevo_nombre = st.text_input("Nombre", value=p_data['nombre'])
                        stock_nuevo = st.number_input("Stock", value=float(p_data['stock']), min_value=0.0, step=1.0)
                        costo_nuevo = st.number_input("Costo $", value=float(p_data['costo']), min_value=0.0, step=0.01)
                        detal_nuevo = st.number_input("Precio Detal $", value=float(p_data['precio_detal']), min_value=0.0, step=0.01)
                        mayor_nuevo = st.number_input("Precio Mayor $", value=float(p_data['precio_mayor']), min_value=0.0, step=0.01)
                        min_mayor_nuevo = st.number_input("Mínimo para Mayor", value=int(p_data['min_mayor']), min_value=1, step=1)
                        
                        if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                            try:
                                db.table("inventario").update({
                                    "nombre": nuevo_nombre,
                                    "stock": stock_nuevo,
                                    "costo": costo_nuevo,
                                    "precio_detal": detal_nuevo,
                                    "precio_mayor": mayor_nuevo,
                                    "min_mayor": min_mayor_nuevo
                                }).eq("id", p_data['id']).execute()
                                st.success("✅ Producto actualizado")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            # Eliminar producto
            with col2:
                del_sel = st.selectbox("🗑️ Seleccionar para Eliminar", [None] + df_mostrar['nombre'].tolist(), key="del_select")
                clave = st.text_input("Clave Admin", type="password", key="del_key")
                if st.button("❌ ELIMINAR PRODUCTO", type="primary") and clave == CLAVE_ADMIN and del_sel:
                    try:
                        db.table("inventario").delete().eq("nombre", del_sel).execute()
                        st.success(f"✅ Producto '{del_sel}' eliminado")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Agregar nuevo producto
        with st.expander("➕ AGREGAR NUEVO PRODUCTO"):
            with st.form("nuevo_producto"):
                col1, col2 = st.columns(2)
                nombre = col1.text_input("Nombre del Producto").upper()
                stock = col2.number_input("Stock Inicial", min_value=0.0, step=1.0)
                
                col3, col4, col5 = st.columns(3)
                costo = col3.number_input("Costo $", min_value=0.0, step=0.01)
                detal = col4.number_input("Precio Detal $", min_value=0.0, step=0.01)
                mayor = col5.number_input("Precio Mayor $", min_value=0.0, step=0.01)
                min_mayor = st.number_input("Cantidad Mínima para Precio Mayor", min_value=1, value=6, step=1)
                
                if st.form_submit_button("📦 REGISTRAR PRODUCTO"):
                    if nombre:
                        try:
                            db.table("inventario").insert({
                                "nombre": nombre,
                                "stock": stock,
                                "costo": costo,
                                "precio_detal": detal,
                                "precio_mayor": mayor,
                                "min_mayor": min_mayor
                            }).execute()
                            st.success(f"✅ Producto '{nombre}' registrado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("⚠️ El nombre es obligatorio")

    except Exception as e:
        st.error(f"Error de conexión: {e}")

# ============================================
# MÓDULO 2: PUNTO DE VENTA
# ============================================
elif opcion == "🛒 Punto de Venta":
    validar_turno_abierto("Punto de Venta")
    
    id_turno = int(st.session_state.id_turno)
    tasa = float(st.session_state.get('tasa_dia', 1.0))
    
    st.markdown("<h1 class='main-header'>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    
    col_izq, col_der = st.columns([1, 1.2])
    
    # Columna Izquierda: Productos
    with col_izq:
        st.subheader("🔍 Productos Disponibles")
        busqueda = st.text_input("Buscar producto...", placeholder="Ej: Harina Pan", key="buscar_pos")
        
        try:
            if busqueda:
                productos = db.table("inventario").select("*").ilike("nombre", f"%{busqueda}%").gt("stock", 0).limit(10).execute()
            else:
                productos = db.table("inventario").select("*").gt("stock", 0).limit(10).execute()
            
            for prod in productos.data:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**{prod['nombre']}**")
                    c1.caption(f"Stock: {prod['stock']:.0f}")
                    c2.markdown(f"**${prod['precio_detal']:.2f}**")
                    
                    if c3.button("➕ Añadir", key=f"add_{prod['id']}", use_container_width=True):
                        encontrado = False
                        for item in st.session_state.car:
                            if item['id'] == prod['id']:
                                item['cant'] += 1.0
                                encontrado = True
                                break
                        if not encontrado:
                            st.session_state.car.append({
                                "id": prod['id'],
                                "nombre": prod['nombre'],
                                "cant": 1.0,
                                "precio": float(prod['precio_detal']),
                                "costo": float(prod['costo'])
                            })
                        st.rerun()
        except Exception as e:
            st.error(f"Error cargando productos: {e}")
    
    # Columna Derecha: Carrito
    with col_der:
        st.subheader("🛒 Carrito de Compras")
        
        if not st.session_state.car:
            st.info("El carrito está vacío")
        else:
            total_usd = 0.0
            total_costo = 0.0
            
            for i, item in enumerate(st.session_state.car):
                with st.container(border=True):
                    cols = st.columns([2.5, 1.5, 0.5])
                    
                    # Cantidad
                    nueva_cant = cols[0].number_input(
                        f"{item['nombre']}",
                        min_value=0.1,
                        max_value=1000.0,
                        value=float(item['cant']),
                        step=1.0,
                        key=f"cant_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if nueva_cant != item['cant']:
                        if nueva_cant == 0:
                            st.session_state.car.pop(i)
                        else:
                            item['cant'] = nueva_cant
                        st.rerun()
                    
                    # Subtotal
                    subtotal = item['cant'] * item['precio']
                    total_usd += subtotal
                    total_costo += item['cant'] * item['costo']
                    
                    cols[1].markdown(f"**${subtotal:.2f}**")
                    
                    # Botón eliminar
                    if cols[2].button("❌", key=f"del_{i}"):
                        st.session_state.car.pop(i)
                        st.rerun()
            
            st.divider()
            
            # Totales
            total_bs = total_usd * tasa
            st.markdown(f"### Total: `${total_usd:.2f}` / `{total_bs:,.2f} Bs`")
            
            # Monto a cobrar (permite redondeo)
            monto_cobrar_bs = st.number_input("Monto a cobrar (Bs)", value=float(total_bs), format="%.2f")
            
            # Pagos
            with st.expander("💳 DETALLE DE PAGOS", expanded=True):
                col_p1, col_p2 = st.columns(2)
                
                with col_p1:
                    st.markdown("**Pagos en Divisas ($)**")
                    pago_divisas = st.number_input("Efectivo $", min_value=0.0, format="%.2f", key="pago_usd_efectivo")
                    pago_zelle = st.number_input("Zelle $", min_value=0.0, format="%.2f", key="pago_zelle")
                    pago_otros = st.number_input("Otros $", min_value=0.0, format="%.2f", key="pago_otros_usd")
                
                with col_p2:
                    st.markdown("**Pagos en Bolívares**")
                    pago_efectivo = st.number_input("Efectivo Bs", min_value=0.0, format="%.2f", key="pago_bs_efectivo")
                    pago_movil = st.number_input("Pago Móvil Bs", min_value=0.0, format="%.2f", key="pago_movil")
                    pago_punto = st.number_input("Punto de Venta Bs", min_value=0.0, format="%.2f", key="pago_punto")
                
                # Calcular total pagado
                total_pagado_usd = pago_divisas + pago_zelle + pago_otros
                total_pagado_bs = pago_efectivo + pago_movil + pago_punto
                total_pagado_usd_equivalente = total_pagado_usd + (total_pagado_bs / tasa if tasa > 0 else 0)
                
                monto_esperado_usd = monto_cobrar_bs / tasa if tasa > 0 else 0
                vuelto_usd = total_pagado_usd_equivalente - monto_esperado_usd
                
                # Mostrar resumen
                st.info(f"Total pagado: ${total_pagado_usd_equivalente:.2f} equivalente")
                
                if vuelto_usd >= -0.01:
                    st.success(f"✅ Vuelto: ${vuelto_usd:.2f} / {(vuelto_usd * tasa):,.2f} Bs")
                else:
                    st.error(f"❌ Faltante: ${abs(vuelto_usd):.2f} / {(abs(vuelto_usd) * tasa):,.2f} Bs")
            
            # Botón finalizar venta
            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True, 
                        disabled=(vuelto_usd < -0.01 or not st.session_state.car)):
                
                try:
                    # Preparar datos
                    items_resumen = []
                    for item in st.session_state.car:
                        items_resumen.append(f"{item['cant']:.0f}x {item['nombre']}")
                        
                        # Actualizar stock
                        db.table("inventario").update({
                            "stock": db.table("inventario").select("stock").eq("id", item['id']).execute().data[0]['stock'] - item['cant']
                        }).eq("id", item['id']).execute()
                    
                    # Insertar venta
                    venta_data = {
                        "id_cierre": id_turno,
                        "producto": ", ".join(items_resumen),
                        "cantidad": len(st.session_state.car),
                        "total_usd": round(total_usd, 2),
                        "monto_cobrado_bs": round(monto_cobrar_bs, 2),
                        "tasa_cambio": tasa,
                        "pago_divisas": round(pago_divisas, 2),
                        "pago_zelle": round(pago_zelle, 2),
                        "pago_otros": round(pago_otros, 2),
                        "pago_efectivo": round(pago_efectivo, 2),
                        "pago_movil": round(pago_movil, 2),
                        "pago_punto": round(pago_punto, 2),
                        "costo_venta": round(total_costo, 2),
                        "estado": "Finalizado",
                        "items": st.session_state.car,
                        "id_transaccion": int(datetime.now().timestamp()),
                        "fecha": datetime.now().isoformat()
                    }
                    
                    db.table("ventas").insert(venta_data).execute()
                    
                    # Mostrar ticket
                    st.balloons()
                    st.markdown(f"""
                        <div style="background:white; padding:20px; border-radius:10px; border:1px solid #ccc;">
                            <h3 style="text-align:center;">TICKET DE VENTA</h3>
                            <p><b>Fecha:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
                            <p><b>Turno:</b> #{id_turno}</p>
                            <hr>
                            {chr(10).join(['• ' + r for r in items_resumen])}
                            <hr>
                            <p><b>TOTAL:</b> ${total_usd:.2f} / {monto_cobrar_bs:,.2f} Bs</p>
                            <p style="text-align:center;">¡Gracias por su compra!</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.car = []
                    
                    if st.button("🔄 NUEVA VENTA"):
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error al procesar venta: {e}")

# ============================================
# MÓDULO 3: HISTORIAL
# ============================================
elif opcion == "📜 Historial":
    validar_turno_abierto("Historial")
    
    id_turno = st.session_state.id_turno
    st.markdown("<h1 class='main-header'>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    st.info(f"🔍 Mostrando ventas del Turno #{id_turno}")
    
    try:
        ventas = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        
        if ventas.data:
            df = pd.DataFrame(ventas.data)
            
            # Formatear fechas
            df['fecha_dt'] = pd.to_datetime(df['fecha'])
            df['hora'] = df['fecha_dt'].dt.strftime('%H:%M')
            df['fecha_corta'] = df['fecha_dt'].dt.strftime('%d/%m/%Y')
            
            # Filtros
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                buscar = st.text_input("🔍 Buscar", placeholder="Producto o ID...")
            with col_f2:
                fecha_filtro = st.text_input("📅 Fecha (DD/MM/AAAA)", placeholder="Ej: 15/02/2024")
            with col_f3:
                estado_filtro = st.selectbox("Estado", ["Todos", "Finalizado", "Anulado"])
            
            # Aplicar filtros
            df_filtrado = df.copy()
            if buscar:
                df_filtrado = df_filtrado[
                    df_filtrado['producto'].str.contains(buscar, case=False, na=False) |
                    df_filtrado['id'].astype(str).str.contains(buscar, case=False)
                ]
            if fecha_filtro:
                df_filtrado = df_filtrado[df_filtrado['fecha_corta'].str.contains(fecha_filtro, na=False)]
            if estado_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['estado'] == estado_filtro]
            
            # Mostrar ventas
            for _, venta in df_filtrado.iterrows():
                es_anulado = venta['estado'] == 'Anulado'
                color = "#888" if es_anulado else "inherit"
                tachado = "line-through" if es_anulado else "none"
                
                with st.container(border=True):
                    cols = st.columns([1, 1, 3, 1.5, 1.5, 1])
                    
                    cols[0].markdown(f"<span style='color:{color}; text-decoration:{tachado};'>#{venta['id']}</span>", unsafe_allow_html=True)
                    cols[1].markdown(f"<span style='color:{color}; text-decoration:{tachado};'>{venta['hora']}</span>", unsafe_allow_html=True)
                    
                    # Productos (resumidos)
                    productos = venta['producto'][:50] + "..." if len(venta['producto']) > 50 else venta['producto']
                    cols[2].markdown(f"<span style='color:{color}; text-decoration:{tachado};' title='{venta['producto']}'>{productos}</span>", unsafe_allow_html=True)
                    
                    cols[3].markdown(f"<span style='color:{color}; text-decoration:{tachado};'>${venta['total_usd']:,.2f}</span>", unsafe_allow_html=True)
                    cols[4].markdown(f"<span style='color:{color}; text-decoration:{tachado};'>{venta['monto_cobrado_bs']:,.2f} Bs</span>", unsafe_allow_html=True)
                    
                    # Botón anular (solo si no está anulado)
                    if not es_anulado:
                        if cols[5].button("🚫 Anular", key=f"anular_{venta['id']}"):
                            try:
                                # Revertir stock
                                items = venta.get('items', [])
                                if isinstance(items, str):
                                    items = json.loads(items)
                                
                                for item in items:
                                    db.table("inventario").update({
                                        "stock": db.table("inventario").select("stock").eq("id", item['id']).execute().data[0]['stock'] + item['cant']
                                    }).eq("id", item['id']).execute()
                                
                                # Marcar como anulada
                                db.table("ventas").update({"estado": "Anulado"}).eq("id", venta['id']).execute()
                                st.success(f"Venta #{venta['id']} anulada")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al anular: {e}")
                    else:
                        cols[5].markdown("❌ Anulado")
            
            # Totales
            df_activas = df_filtrado[df_filtrado['estado'] != 'Anulado']
            if not df_activas.empty:
                st.markdown("---")
                col_t1, col_t2, col_t3 = st.columns(3)
                col_t1.metric("Total USD", f"${df_activas['total_usd'].sum():,.2f}")
                col_t2.metric("Total Bs", f"{df_activas['monto_cobrado_bs'].sum():,.2f} Bs")
                col_t3.metric("Costo Total", f"${df_activas['costo_venta'].sum():,.2f}")
        else:
            st.info("No hay ventas en este turno")
            
    except Exception as e:
        st.error(f"Error cargando historial: {e}")

# ============================================
# MÓDULO 4: GASTOS
# ============================================
elif opcion == "💸 Gastos":
    validar_turno_abierto("Gastos")
    
    st.markdown("<h1 class='main-header'>💸 Gastos Operativos</h1>", unsafe_allow_html=True)
    
    # Mostrar gastos existentes
    try:
        gastos = db.table("gastos").select("*").eq("id_cierre", st.session_state.id_turno).order("fecha", desc=True).execute()
        
        if gastos.data:
            df_gastos = pd.DataFrame(gastos.data)
            st.subheader("📋 Gastos del Turno")
            
            # Formatear fechas si existen
            if 'fecha' in df_gastos.columns:
                df_gastos['fecha'] = pd.to_datetime(df_gastos['fecha']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(
                df_gastos[['fecha', 'descripcion', 'monto_usd', 'categoria', 'estado']] 
                if 'categoria' in df_gastos.columns 
                else df_gastos[['fecha', 'descripcion', 'monto_usd', 'estado']],
                use_container_width=True,
                hide_index=True
            )
            
            st.metric("Total Gastos USD", f"${df_gastos['monto_usd'].sum():,.2f}")
    
    except Exception as e:
        st.warning(f"No se pudieron cargar gastos anteriores: {e}")
    
    st.divider()
    
    # Formulario para nuevo gasto
    with st.form("formulario_gastos"):
        st.subheader("➕ Registrar Nuevo Gasto")
        
        col1, col2 = st.columns(2)
        with col1:
            descripcion = st.text_input("Descripción del Gasto*", placeholder="Ej: Pago de luz, compra de hielo...")
            monto = st.number_input("Monto en USD $*", min_value=0.01, step=0.01, format="%.2f")
        
        with col2:
            categoria = st.selectbox(
                "Categoría (opcional)",
                ["", "Servicios", "Insumos", "Mantenimiento", "Personal", "Otros"]
            )
            monto_bs_extra = st.number_input("Monto extra en Bs (opcional)", min_value=0.0, step=10.0, format="%.2f")
        
        submitted = st.form_submit_button("✅ REGISTRAR GASTO", use_container_width=True)
        
        if submitted:
            if descripcion and monto > 0:
                try:
                    gasto_data = {
                        "id_cierre": st.session_state.id_turno,
                        "descripcion": descripcion,
                        "monto_usd": monto,
                        "estado": "activo",
                        "fecha": datetime.now().isoformat()
                    }
                    
                    # Agregar campos opcionales si existen en la tabla
                    if categoria:
                        try:
                            gasto_data["categoria"] = categoria
                        except:
                            pass
                    
                    if monto_bs_extra > 0:
                        try:
                            gasto_data["monto_bs_extra"] = monto_bs_extra
                        except:
                            pass
                    
                    db.table("gastos").insert(gasto_data).execute()
                    st.success("✅ Gasto registrado exitosamente!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error al registrar gasto: {e}")
            else:
                st.warning("⚠️ Complete los campos obligatorios (*)")

# ============================================
# MÓDULO 5: CIERRE DE CAJA
# ============================================
elif opcion == "📊 Cierre de Caja":
    st.markdown("<h1 class='main-header'>📊 Cierre de Caja</h1>", unsafe_allow_html=True)
    
    # Si no hay turno activo, mostrar formulario de apertura
    if not st.session_state.get('id_turno'):
        st.warning("🔓 No hay turno activo. Complete para abrir caja:")
        
        with st.form("apertura_caja"):
            col1, col2 = st.columns(2)
            
            with col1:
                tasa_apertura = st.number_input("Tasa de Cambio del Día (Bs/$)", min_value=1.0, value=60.0, step=0.5, format="%.2f")
                fondo_bs = st.number_input("Fondo Inicial en Bolívares (Efectivo)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
            
            with col2:
                fondo_usd = st.number_input("Fondo Inicial en Divisas (Efectivo $)", min_value=0.0, value=0.0, step=5.0, format="%.2f")
                monto_apertura = st.number_input("Monto de Apertura (USD)", min_value=0.0, value=fondo_usd, format="%.2f", disabled=True)
            
            if st.form_submit_button("🚀 ABRIR CAJA", type="primary", use_container_width=True):
                try:
                    apertura_data = {
                        "tasa_apertura": tasa_apertura,
                        "fondo_bs": fondo_bs,
                        "fondo_usd": fondo_usd,
                        "monto_apertura": fondo_usd,
                        "estado": "abierto",
                        "fecha_apertura": datetime.now().isoformat()
                    }
                    
                    result = db.table("cierres").insert(apertura_data).execute()
                    
                    if result.data:
                        st.session_state.id_turno = result.data[0]['id']
                        st.session_state.tasa_dia = tasa_apertura
                        st.success(f"✅ Turno #{result.data[0]['id']} abierto exitosamente!")
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error al abrir caja: {e}")
    
    # Si hay turno activo, mostrar cierre
    else:
        id_turno = st.session_state.id_turno
        st.success(f"📍 Turno Activo: #{id_turno}")
        
        # Obtener datos del turno
        try:
            # Datos de ventas
            ventas = db.table("ventas").select("*").eq("id_cierre", id_turno).eq("estado", "Finalizado").execute()
            total_ventas_usd = sum(v['total_usd'] for v in ventas.data) if ventas.data else 0
            total_costos = sum(v['costo_venta'] for v in ventas.data) if ventas.data else 0
            ganancia_neta = total_ventas_usd - total_costos
            
            # Datos de gastos
            gastos = db.table("gastos").select("*").eq("id_cierre", id_turno).execute()
            total_gastos = sum(g['monto_usd'] for g in gastos.data) if gastos.data else 0
            
            # Resumen
            st.subheader("📈 Resumen del Turno")
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Ventas Totales", f"${total_ventas_usd:,.2f}")
            col_r2.metric("Costo de Ventas", f"${total_costos:,.2f}")
            col_r3.metric("Ganancia Bruta", f"${ganancia_neta:,.2f}")
            col_r4.metric("Gastos", f"${total_gastos:,.2f}")
            
            st.metric("Ganancia Neta", f"
