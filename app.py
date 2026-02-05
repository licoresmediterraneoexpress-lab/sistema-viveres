import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# Inicialización de estado del carrito
if 'car' not in st.session_state:
    st.session_state.car = []

# Estilos Personalizados
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold; width: 100%;}
    .metric-container {background-color: #f8f9fa; border-radius: 10px; padding: 15px; border: 1px solid #e0e0e0;}
</style>
""", unsafe_allow_html=True)

# --- 2. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO EXPRESS</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()

# --- 3. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Centro de Control de Inventario")
    st.markdown("---")

    # 1. CARGA Y PREPARACIÓN DE DATOS
    try:
        res = db.table("inventario").select("*").execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
        df_inv = pd.DataFrame()

    if not df_inv.empty:
        # Estandarización de tipos de datos
        numeric_cols = ['stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']
        for col in numeric_cols:
            df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

        # Cálculo de Métricas
        df_inv['valor_costo'] = df_inv['stock'] * df_inv['costo']
        df_inv['valor_venta'] = df_inv['stock'] * df_inv['precio_detal']
        
        m1, m2, m3 = st.columns(3)
        m1.metric("🛒 Inversión Total", f"${df_inv['valor_costo'].sum():,.2f}")
        m2.metric("💰 Valor de Venta", f"${df_inv['valor_venta'].sum():,.2f}")
        m3.metric("📈 Ganancia Est.", f"${(df_inv['valor_venta'].sum() - df_inv['valor_costo'].sum()):,.2f}")

        st.markdown("### 📋 Listado de Existencias")

        # Buscador Inteligente
        busqueda = st.text_input("🔍 Buscar producto por nombre...", placeholder="Ej: Harina Pan, Refresco...")
        df_filtrado = df_inv[df_inv['nombre'].str.contains(busqueda, case=False, na=False)] if busqueda else df_inv

        # Tabla Visual
        vista_tabla = df_filtrado.copy()
        for col in ['costo', 'precio_detal', 'precio_mayor']:
            vista_tabla[col] = vista_tabla[col].apply(lambda x: f"$ {x:,.2f}")

        st.dataframe(
            vista_tabla.rename(columns={
                'nombre': 'PRODUCTO', 'stock': 'STOCK', 'costo': 'PRECIO COSTO',
                'precio_detal': 'PRECIO VENTA', 'precio_mayor': 'VENTA MAYOR', 'min_mayor': 'MIN. MAYOR'
            })[['PRODUCTO', 'STOCK', 'PRECIO COSTO', 'PRECIO VENTA', 'VENTA MAYOR', 'MIN. MAYOR']], 
            use_container_width=True, hide_index=True, height=400
        )

        # Diálogo de Edición
        @st.dialog("✏️ Editar Información del Producto")
        def editar_producto_dialog(item_data):
            id_producto = item_data['id']
            st.write(f"Editando: **{item_data['nombre']}**")
            with st.form("form_edicion"):
                col_a, col_b, col_min = st.columns([1.5, 1.5, 1])
                new_stock = col_a.number_input("Cantidad en Stock", value=int(item_data['stock']), step=1)
                new_costo = col_b.number_input("Costo Unitario ($)", value=float(item_data['costo']), format="%.2f")
                new_min_mayor = col_min.number_input("Mín. Mayor", value=int(item_data['min_mayor']), step=1)
                
                col_c, col_d = st.columns(2)
                new_detal = col_c.number_input("Precio Venta Detal ($)", value=float(item_data['precio_detal']), format="%.2f")
                new_mayor = col_d.number_input("Precio Venta Mayor ($)", value=float(item_data['precio_mayor']), format="%.2f")
                
                if st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                    upd = {
                        "stock": int(new_stock), "costo": float(new_costo),
                        "precio_detal": float(new_detal), "precio_mayor": float(new_mayor),
                        "min_mayor": int(new_min_mayor)
                    }
                    try:
                        db.table("inventario").update(upd).eq("id", id_producto).execute()
                        st.success("✅ Cambios guardados correctamente")
                        if hasattr(st, 'cache_data'): st.cache_data.clear()
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error de actualización: {e}")

        # Panel de Acciones
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("🛠️ Gestión Directa")
            seleccion = st.selectbox("Selecciona un producto para modificar:", options=df_filtrado['nombre'].tolist(), index=None)
            if seleccion:
                fila_datos = df_inv[df_inv['nombre'] == seleccion].iloc[0].to_dict()
                if st.button(f"Modificar {seleccion}", icon="✏️"):
                    editar_producto_dialog(fila_datos)

        with c2:
            st.subheader("🗑️ Eliminar")
            with st.expander("Zona de Peligro"):
                prod_del = st.selectbox("Producto a eliminar:", options=["---"] + df_inv['nombre'].tolist())
                password = st.text_input("Clave Administrativa", type="password")
                if st.button("Eliminar Permanentemente", type="primary"):
                    if password == CLAVE_ADMIN and prod_del != "---":
                        db.table("inventario").delete().eq("nombre", prod_del).execute()
                        st.rerun()

    # Registro de nuevos productos
    with st.expander("➕ REGISTRAR NUEVO PRODUCTO EN EL SISTEMA"):
        with st.form("nuevo_registro", clear_on_submit=True):
            f1, f2, f_m = st.columns([2, 1, 1])
            n_nombre = f1.text_input("Nombre del Producto").upper().strip()
            n_stock = f2.number_input("Stock Inicial", min_value=0, step=1)
            n_min_m = f_m.number_input("Mín. para Mayor", min_value=1, value=1)
            f3, f4, f5 = st.columns(3)
            n_costo = f3.number_input("Costo ($)", min_value=0.0, format="%.2f")
            n_detal = f4.number_input("Precio Detal ($)", min_value=0.0, format="%.2f")
            n_mayor = f5.number_input("Precio Mayor ($)", min_value=0.0, format="%.2f")
            if st.form_submit_button("🚀 Registrar en Base de Datos"):
                if n_nombre:
                    try:
                        db.table("inventario").insert({"nombre": n_nombre, "stock": n_stock, "costo": n_costo, "precio_detal": n_detal, "precio_mayor": n_mayor, "min_mayor": n_min_m}).execute()
                        st.success(f"¡{n_nombre} registrado!"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

# --- 4. MÓDULO VENTA RÁPIDA (REFACTORIZACIÓN PROFESIONAL POS) ---
elif opcion == "🛒 Venta Rápida":
    # A. Inicialización de Estados y Validación de Turno
    if 'car' not in st.session_state: st.session_state.car = []
    if 'venta_finalizada' not in st.session_state: st.session_state.venta_finalizada = False
    if 'ultimo_ticket' not in st.session_state: st.session_state.ultimo_ticket = ""
    
    # Inicialización de Tasa Dinámica
    if 'tasa_pos' not in st.session_state:
        st.session_state.tasa_pos = float(st.session_state.get('tasa_dia', 1.0))

    # Obtener Turno Activo
    try:
        res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        if not res_caja.data:
            st.error("🚫 SISTEMA BLOQUEADO: No hay un turno de caja abierto.")
            st.info("Por favor, vaya al módulo 'Cierre de Caja' e inicie una nueva jornada.")
            st.stop()
        turno_actual = res_caja.data[0]
        id_turno = turno_actual['id']
    except Exception as e:
        st.error(f"Error de Conexión DB: {e}"); st.stop()

    # --- CONTROLADOR DINÁMICO DE TASA ---
    t_col1, t_col2 = st.columns([2, 1])
    with t_col1:
        st.markdown(f"## 🛒 Terminal de Ventas <span style='font-size:16px; color:gray;'>| Turno #{id_turno}</span>", unsafe_allow_html=True)
    with t_col2:
        st.session_state.tasa_pos = st.number_input("💱 Tasa (Bs/$)", 
                                                   value=float(st.session_state.tasa_pos), 
                                                   step=0.01)
    
    tasa_v = float(st.session_state.tasa_pos)

    # B. Pantalla de Éxito (Post-Venta)
    if st.session_state.venta_finalizada:
        st.balloons()
        c_p1, c_p2 = st.columns([1, 1.5])
        with c_p1:
            st.markdown(st.session_state.ultimo_ticket, unsafe_allow_html=True)
        with c_p2:
            st.success("### ✅ VENTA REGISTRADA")
            if st.button("🔄 REGISTRAR NUEVA VENTA", type="primary", use_container_width=True):
                st.session_state.car = []
                st.session_state.venta_finalizada = False
                st.rerun()
        st.stop()

    # C. Layout POS
    col_izq, col_der = st.columns([1.1, 1])

    with col_izq:
        st.subheader("🔍 Selección de Productos")
        busc_term = st.text_input("Filtrar inventario...", placeholder="Nombre del producto...", key="pos_search").strip()
        
        if busc_term:
            res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc_term}%").gt("stock", 0).limit(8).execute()
            if res_p.data:
                for p in res_p.data:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 1, 1])
                        c1.markdown(f"**{p['nombre']}**\n\nStock: `{p['stock']}`")
                        c2.markdown(f"<p style='color:green; font-weight:bold; margin-top:10px;'>${p['precio_detal']:.2f}</p>", unsafe_allow_html=True)
                        if c3.button("➕", key=f"add_{p['id']}", use_container_width=True):
                            exists = False
                            for item in st.session_state.car:
                                if item['id'] == p['id']:
                                    item['cant'] += 1.0
                                    exists = True
                                    break
                            if not exists:
                                st.session_state.car.append({
                                    "id": p['id'], "nombre": p['nombre'], "cant": 1.0, 
                                    "precio": float(p['precio_detal']), "stock": p['stock']
                                })
                            st.rerun()

    with col_der:
        st.subheader("📋 Carrito")
        if not st.session_state.car:
            st.info("Agregue productos para comenzar.")
        else:
            total_usd = 0.0
            for idx, item in enumerate(st.session_state.car):
                with st.container(border=True):
                    r1, r2, r3, r4 = st.columns([2, 1.2, 1, 0.5])
                    r1.write(f"**{item['nombre']}**")
                    nueva_cant = r2.number_input("Cant.", min_value=0.1, max_value=float(item['stock']), 
                                                 value=float(item['cant']), key=f"cant_{item['id']}")
                    item['cant'] = nueva_cant
                    subtotal = item['precio'] * item['cant']
                    total_usd += subtotal
                    r3.write(f"${subtotal:.2f}")
                    if r4.button("🗑️", key=f"del_{idx}"):
                        st.session_state.car.pop(idx)
                        st.rerun()

            st.divider()
            
# --- SECCIÓN DE PAGOS ---
            total_vef = total_usd * tasa_v
            st.markdown(f"### Total: `${total_usd:.2f}` / `{total_vef:,.2f} Bs`")
            
            # Monto a cobrar modificable en BOLÍVARES
            monto_cobrar_bs_input = st.number_input("Monto a Cobrar (Bs)", value=float(total_vef), step=1.0)
            monto_cobrar_usd = float(monto_cobrar_bs_input / tasa_v)
            
            with st.expander("💳 Registrar Pagos Mixtos", expanded=True):
                px1, px2 = st.columns(2)
                p_divisas = px1.number_input("Efectivo $ (Divisas)", min_value=0.0, key="p_div")
                p_efectivo = px2.number_input("Efectivo Bs", min_value=0.0, key="p_efe")
                p_zelle = px1.number_input("Zelle $", min_value=0.0, key="p_zel")
                p_movil = px2.number_input("Pago Móvil Bs", min_value=0.0, key="p_mov")
                p_punto = px1.number_input("Punto Bs", min_value=0.0, key="p_pun")
                p_otros = px2.number_input("Otros $", min_value=0.0, key="p_otr")

            # Cálculos de Totales y Balance (Blindaje de tipos Float)
            total_pagado_usd = float(p_divisas + p_zelle + p_otros + ((p_efectivo + p_movil + p_punto) / tasa_v))
            total_pagado_vef = float(total_pagado_usd * tasa_v)
            balance_usd = float(total_pagado_usd - monto_cobrar_usd)
            
            if balance_usd < -0.01:
                st.error(f"Faltante: ${abs(balance_usd):.2f} / {abs(balance_usd*tasa_v):,.2f} Bs")
            else:
                st.success(f"Vuelto: ${balance_usd:.2f} / {balance_usd*tasa_v:,.2f} Bs")

            # --- FINALIZAR VENTA (BOTÓN) ---
            if st.button("🚀 FINALIZAR Y GENERAR TICKET", type="primary", use_container_width=True, disabled=(total_pagado_usd < (monto_cobrar_usd - 0.01))):
                try:
                    # 1. Preparar datos del carrito (JSONB) y sumar unidades totales
                    items_json = []
                    unidades_totales_float = 0.0
                    costo_total_venta = 0.0
                    
                    for i in st.session_state.car:
                        unidades_totales_float += float(i['cant'])
                        costo_total_venta += (float(i.get('costo', 0)) * float(i['cant']))
                        items_json.append({
                            "id": i['id'],
                            "nombre": i['nombre'],
                            "cantidad": i['cant'],
                            "precio_u": i['precio'],
                            "subtotal": round(float(i['cant'] * i['precio']), 2)
                        })

                    # Generación de ID único entero para id_transaccion
                    ts_id = int(datetime.now().timestamp())

                    # 2. Registrar en DB 'ventas' (Mapeo Estricto y Conversión Forzada)
                    venta_data = {
                        "id_cierre": int(float(id_turno)),                   # Forzado a INT
                        "fecha": datetime.now().isoformat(),
                        "producto": f"Venta de {len(items_json)} ítems",
                        "cantidad": int(float(unidades_totales_float)),      # Forzado a INT (Resuelve error 4.0)
                        "total_usd": round(float(total_usd), 2),
                        "tasa_cambio": float(tasa_v),
                        "pago_punto": float(p_punto),
                        "pago_efectivo": float(p_efectivo),
                        "pago_movil": float(p_movil),
                        "pago_zelle": float(p_zelle),
                        "pago_otros": float(p_otros),
                        "pago_divisas": float(p_divisas),
                        "costo_venta": round(float(costo_total_venta), 2),
                        "propina": 0.0,
                        "id_transaccion": ts_id,                              # INT puro
                        "cliente": "Mostrador",
                        "estado": "finalizado",
                        "total_pagado_real": round(float(total_pagado_usd), 2),
                        "monto_cobrado_bs": round(float(monto_cobrar_bs_input), 2),
                        "monto_real_vef": round(float(total_pagado_vef), 2),
                        "items": items_json
                    }
                    
                    # Ejecución del Insert
                    db.table("ventas").insert(venta_data).execute()

                    # 3. Actualización de Stock en Inventario
                    for item in st.session_state.car:
                        nuevo_stock = float(item['stock']) - float(item['cant'])
                        db.table("inventario").update({"stock": nuevo_stock}).eq("id", item['id']).execute()

                    # 4. Generación de Ticket Visual
                    filas_html = "".join([f"<div style='display:flex; justify-content:space-between; font-size:12px;'><span>{it['cantidad']}x {it['nombre'][:15]}</span><span>${it['subtotal']:.2f}</span></div>" for it in items_json])
                    
                    st.session_state.ultimo_ticket = f"""
                    <div style="border:1px solid #ddd; padding:15px; border-radius:10px; font-family:monospace; background-color: #fff; color: black;">
                        <h4 style="text-align:center; margin:0;">TICKET DE VENTA</h4>
                        <p style="text-align:center; font-size:10px;">Turno: {id_turno} | Trans: {ts_id}</p>
                        <hr>
                        {filas_html}
                        <hr>
                        <div style="display:flex; justify-content:space-between; font-weight:bold;"><span>TOTAL USD:</span><span>${total_usd:.2f}</span></div>
                        <div style="display:flex; justify-content:space-between;"><span>PAGO Bs:</span><span>{monto_cobrar_bs_input:,.2f}</span></div>
                        <p style="font-size:10px; text-align:center; margin-top:10px;">¡Gracias por su compra!</p>
                    </div>
                    """
                    st.session_state.venta_finalizada = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Error de Integridad de Datos: {str(e)}")

# --- MÓDULO: HISTORIAL DE VENTAS PRO ---
if opcion == "📜 Historial de Ventas":
    st.markdown("## 📜 Historial de Ventas Pro")

    # 1. Obtener Turno Activo para el Filtro Inicial
    id_turno_actual = st.session_state.get('id_cierre_activo') # Ajustar según tu nombre de variable
    
    # 2. Carga de Datos con Blindaje
    try:
        # Traemos todas las ventas para permitir búsqueda global, luego filtramos
        res = db.table("ventas").select("*").order("fecha", desc=True).execute()
        df_raw = pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"❌ Error de conexión con Supabase: {e}")
        st.stop()

    if df_raw.empty:
        st.info("No hay ventas registradas aún.")
        st.stop()

    # 3. Formateo y Extracción de Datos
    # Extraer Fecha y Hora de la columna ISO 'fecha'
    df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'])
    df_raw['Fecha'] = df_raw['fecha_dt'].dt.strftime('%d/%m/%Y')
    df_raw['Hora'] = df_raw['fecha_dt'].dt.strftime('%I:%M %p')

    # 4. Buscador Inteligente y Filtros
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        busqueda = st.text_input("🔍 Buscador inteligente", placeholder="Buscar por producto, cliente o ID...")
    with col_f2:
        solo_turno_actual = st.checkbox("Filtrar por Turno Activo", value=True)

    # Lógica de filtrado
    mask = df_raw.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
    df_filtrado = df_raw[mask]

    if solo_turno_actual and id_turno_actual:
        df_filtrado = df_filtrado[df_filtrado['id_cierre'] == int(id_turno_actual)]

    # 5. Visualización Estilo Excel
    st.markdown("---")
    
    # Encabezados de la tabla
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7 = st.columns([1, 1.5, 2, 1, 1.5, 1.5, 1.5])
    h_col1.bold("ID")
    h_col2.bold("Fecha/Hora")
    h_col3.bold("Resumen")
    h_col4.bold("Cant.")
    h_col5.bold("Monto Bs")
    h_col6.bold("Monto $")
    h_col7.bold("Acciones")

    for _, fila in df_filtrado.iterrows():
        # Determinar color según estado
        es_anulado = fila['estado'] == 'Anulado'
        color_texto = "gray" if es_anulado else "inherit"
        opacidad = 0.5 if es_anulado else 1.0
        
        with st.container():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1.5, 2, 1, 1.5, 1.5, 1.5])
            
            # Formateo de montos
            monto_bs = f"{fila['monto_cobrado_bs']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            monto_usd = f"${fila['total_usd']:,.2f}"
            
            c1.markdown(f"<span style='color:{color_texto}'>{int(fila['id'])}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color:{color_texto}; font-size:12px;'>{fila['Fecha']}<br>{fila['Hora']}</span>", unsafe_allow_html=True)
            c3.markdown(f"<span style='color:{color_texto}'>{fila['producto']}</span>", unsafe_allow_html=True)
            c4.markdown(f"<span style='color:{color_texto}'>{int(fila['cantidad'])}</span>", unsafe_allow_html=True)
            c5.markdown(f"<span style='color:{color_texto}'>{monto_bs}</span>", unsafe_allow_html=True)
            c6.markdown(f"<span style='color:{color_texto}'>{monto_usd}</span>", unsafe_allow_html=True)
            
            # Botones de Acción
            btn_col1, btn_col2 = c7.columns(2)
            
            # Botón Reimprimir
            if btn_col1.button("📋", key=f"reimp_{fila['id']}", help="Reimprimir Ticket"):
                st.session_state.ultimo_ticket = f"Reimpresión Venta #{fila['id']}" # Aquí llamarías a tu generador de HTML
                st.info(f"Reabriendo ticket de la venta #{fila['id']}...")

            # Botón Anular
            if not es_anulado:
                if btn_col2.button("🚫", key=f"anul_{fila['id']}", help="Anular Venta"):
                    st.warning(f"¿Confirmar anulación de la Venta #{fila['id']}?")
                    if st.button("SÍ, ANULAR", key=f"conf_{fila['id']}"):
                        try:
                            # --- LÓGICA DE REVERSIÓN DE STOCK ---
                            items_a_revertir = fila['items'] # Es una lista de dicts (JSONB)
                            
                            for item in items_a_revertir:
                                # 1. Buscar stock actual del producto
                                res_inv = db.table("inventario").select("stock").eq("id", item['id']).single().execute()
                                if res_inv.data:
                                    stock_actual = float(res_inv.data['stock'])
                                    nuevo_stock = stock_actual + float(item['cantidad'])
                                    
                                    # 2. Actualizar inventario
                                    db.table("inventario").update({"stock": nuevo_stock}).eq("id", item['id']).execute()
                            
                            # 3. Cambiar estado de la venta
                            db.table("ventas").update({"estado": "Anulado"}).eq("id", int(fila['id'])).execute()
                            
                            st.success(f"Venta #{fila['id']} anulada y stock devuelto.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al anular: {ex}")
            else:
                btn_col2.write("❌")

    # 6. Resumen de Totales (Dashboard Inferior)
    st.markdown("---")
    # Solo sumamos las ventas que NO están anuladas
    df_activos = df_filtrado[df_filtrado['estado'] != 'Anulado']
    
    total_usd_sum = df_activos['total_usd'].sum()
    total_bs_sum = df_activos['monto_cobrado_bs'].sum()
    total_items = df_activos['cantidad'].sum()

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Total Ventas ($)", f"${total_usd_sum:,.2f}")
    m_col2.metric("Total Ventas (Bs)", f"{total_bs_sum:,.2f} Bs")
    m_col3.metric("Productos Vendidos", f"{int(total_items)} Und")

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 6. MÓDULO GESTIÓN DE CAJA ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Gestión de Turnos y Auditoría de Caja")
    st.markdown("---")

    try:
        res_u = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        turno_activo = res_u.data[0] if res_u.data else None
    except Exception as e:
        st.error(f"Error al consultar base de datos: {e}")
        turno_activo = None
    
    if not turno_activo:
        st.subheader("🔓 Apertura de Nuevo Turno")
        with st.form("form_apertura"):
            c1, c2, c3 = st.columns(3)
            t_ref = c1.number_input("Tasa del Día (Ref)", min_value=1.0, value=60.0, step=0.1)
            f_bs = c2.number_input("Fondo Inicial Bs (Efectivo)", min_value=0.0, format="%.2f")
            f_usd = c3.number_input("Fondo Inicial Divisas (Efectivo)", min_value=0.0, format="%.2f")
            
            total_ap_usd = f_usd + (f_bs / t_ref) if t_ref > 0 else f_usd
            
            if st.form_submit_button("✅ INICIAR JORNADA", use_container_width=True):
                data_ap = {
                    "fecha_apertura": datetime.now().isoformat(),
                    "monto_apertura": float(total_ap_usd),
                    "tasa_apertura": float(t_ref),
                    "estado": "abierto",
                    "total_ventas": 0, "total_costos": 0, "total_ganancias": 0
                }
                try:
                    db.table("cierres").insert(data_ap).execute()
                    st.success("¡Turno abierto con éxito!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    
    else:
        id_cierre = turno_activo['id']
        f_ap = turno_activo['fecha_apertura']
        fondo_inicial_usd = float(turno_activo['monto_apertura'])
        tasa_actual = float(turno_activo.get('tasa_apertura', 60.0))

        st.warning(f"🔔 TURNO ACTIVO | Iniciado el: {pd.to_datetime(f_ap).strftime('%d/%m/%Y %H:%M')}")

        try:
            res_v = db.table("ventas").select("*").gte("fecha", f_ap).execute()
            df_v = pd.DataFrame(res_v.data) if res_v.data else pd.DataFrame()
        except:
            df_v = pd.DataFrame()

        if not df_v.empty:
            cols_fin = ['total_usd', 'costo_ventas', 'pago_efectivo', 'pago_punto', 'pago_movil', 'pago_zelle', 'pago_divisas', 'pago_otros']
            for col in cols_fin:
                if col in df_v.columns:
                    df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0)
                else:
                    df_v[col] = 0.0

            t_ventas_sistema = df_v['total_usd'].sum()
            t_costos_sistema = df_v['costo_ventas'].sum()
            t_ganancia_neta = t_ventas_sistema - t_costos_sistema
            
            st.subheader("📈 Rentabilidad del Turno")
            r1, r2, r3 = st.columns(3)
            r1.metric("Monto Total Facturado", f"$ {t_ventas_sistema:,.2f}")
            r2.metric("Costo de Mercancía", f"$ {t_costos_sistema:,.2f}")
            r3.metric("Ganancia Neta", f"$ {t_ganancia_neta:,.2f}")
            
            st.divider()
            st.subheader("🔎 Auditoría de Caja Física")
            with st.container(border=True):
                c_aud1, c_aud2, c_aud3 = st.columns(3)
                d_divisas = c_aud1.number_input("Efectivo Divisas ($)", 0.0, format="%.2f")
                d_bs_efec = c_aud2.number_input("Efectivo Bs (Monto)", 0.0, format="%.2f")
                d_punto = c_aud3.number_input("Punto de Venta ($)", 0.0, format="%.2f")
                d_pmovil = c_aud1.number_input("Pago Móvil ($)", 0.0, format="%.2f")
                d_zelle = c_aud2.number_input("Zelle ($)", 0.0, format="%.2f")
                d_otros = c_aud3.number_input("Otros ($)", 0.0, format="%.2f")

                d_bs_en_usd = d_bs_efec / tasa_actual if tasa_actual > 0 else 0
                total_declarado = d_divisas + d_bs_en_usd + d_punto + d_pmovil + d_zelle + d_otros
                esperado_en_caja = t_ventas_sistema + fondo_inicial_usd
                diferencia = total_declarado - esperado_en_caja

                st.markdown("### Resultado del Arqueo")
                res1, res2 = st.columns(2)
                res1.write(f"**Total Declarado + Fondos:** ${total_declarado:,.2f}")
                res1.write(f"**Esperado en Sistema:** ${esperado_en_caja:,.2f}")
                
                if diferencia < -0.01:
                    res2.markdown(f"<h2 style='color: #ff4b4b;'>Faltante: ${abs(diferencia):,.2f}</h2>", unsafe_allow_html=True)
                elif diferencia > 0.01:
                    res2.markdown(f"<h2 style='color: #28a745;'>Sobrante: ${diferencia:,.2f}</h2>", unsafe_allow_html=True)
                else:
                    res2.markdown(f"<h2 style='color: #28a745;'>Caja Cuadrada</h2>", unsafe_allow_html=True)

            if st.button("🔴 CERRAR CAJA", type="primary", use_container_width=True):
                data_cl = {
                    "fecha_cierre": datetime.now().isoformat(),
                    "total_ventas": float(t_ventas_sistema),
                    "total_costos": float(t_costos_sistema),
                    "total_ganancias": float(t_ganancia_neta),
                    "estado": "cerrado"
                }
                try:
                    db.table("cierres").update(data_cl).eq("id", id_cierre).execute()
                    st.success("✅ Turno finalizado."); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        else:
            st.info("No hay ventas registradas.")
            if st.button("Cerrar Turno (Sin Ventas)"):
                db.table("cierres").update({"estado": "cerrado", "fecha_cierre": datetime.now().isoformat()}).eq("id", id_cierre).execute()
                st.rerun()

















