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

# --- 4. MÓDULO VENTA RÁPIDA (REFACTORIZACIÓN PROFESIONAL) ---
elif opcion == "🛒 Venta Rápida":
    # A. Inicialización de Estados y Validación de Turno
    if 'car' not in st.session_state: st.session_state.car = []
    if 'venta_finalizada' not in st.session_state: st.session_state.venta_finalizada = False
    if 'ultimo_ticket' not in st.session_state: st.session_state.ultimo_ticket = ""
    
    # Validación de Turno Abierto
    try:
        res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        if not res_caja.data:
            st.error("🚫 SISTEMA BLOQUEADO: No hay un turno de caja abierto.")
            st.info("Por favor, inicie jornada en 'Cierre de Caja'.")
            st.stop()
        turno_actual = res_caja.data[0]
        id_turno = turno_actual['id']
        tasa_v = st.session_state.tasa_dia
    except Exception as e:
        st.error(f"Error de conexión: {e}"); st.stop()

    st.markdown(f"<h2 style='color:#0041C2;'>🛒 Terminal de Ventas <span style='font-size:16px; color:grey;'>| Turno Activo: #{id_turno}</span></h2>", unsafe_allow_html=True)

    # B. Pantalla de Éxito Post-Venta
    if st.session_state.venta_finalizada:
        st.balloons()
        c_p1, c_p2 = st.columns([1, 1.5])
        with c_p1:
            st.markdown(st.session_state.ultimo_ticket, unsafe_allow_html=True)
        with c_p2:
            st.success("### ✅ ¡VENTA COMPLETADA!")
            st.info("El stock ha sido actualizado y la venta registrada en el historial.")
            if st.button("🔄 REGISTRAR NUEVA VENTA", type="primary", use_container_width=True):
                st.session_state.car = []
                st.session_state.venta_finalizada = False
                st.rerun()
        st.stop()

    # C. Layout: Buscador e Inventario (Izquierda) | Carrito y Cobro (Derecha)
    col_izq, col_der = st.columns([1.1, 1])

    with col_izq:
        st.subheader("🔍 Selección de Productos")
        busc_term = st.text_input("Buscar por nombre...", placeholder="Escriba aquí para filtrar...", key="search_input").strip()
        
        # Filtro Dinámico de Productos
        if busc_term:
            res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc_term}%").limit(8).execute()
            if res_p.data:
                for p in res_p.data:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 1, 1])
                        c1.markdown(f"**{p['nombre']}**\n\nStock: `{p['stock']}`")
                        c2.markdown(f"<p style='color:green; font-weight:bold; margin-top:10px;'>${p['precio_detal']:.2f}</p>", unsafe_allow_html=True)
                        if c3.button("➕ Agregar", key=f"add_{p['id']}", use_container_width=True):
                            # Evitar duplicados en lista visual, sumar cantidad si ya existe
                            exists = False
                            for item in st.session_state.car:
                                if item['id'] == p['id']:
                                    item['cant'] += 1
                                    exists = True
                                    break
                            if not exists:
                                st.session_state.car.append({
                                    "id": p['id'], "nombre": p['nombre'], "cant": 1.0, 
                                    "u": float(p['precio_detal']), "costo": float(p['costo']), 
                                    "min_m": p['min_mayor'], "p_detal": float(p['precio_detal']), 
                                    "p_mayor": float(p['precio_mayor'])
                                })
                            st.toast(f"Agregado: {p['nombre']}")
                            st.rerun()
            else:
                st.warning("No se encontraron coincidencias.")
        else:
            st.info("Use el buscador para cargar productos al carrito.")

    with col_der:
        st.subheader("📋 Carrito de Compras")
        if not st.session_state.car:
            st.write("Carrito vacío")
        else:
            subtotal_usd = 0.0
            idx_borrar = -1
            
            for i, item in enumerate(st.session_state.car):
                # Lógica de precio al mayor automática
                item['u'] = item['p_mayor'] if item['cant'] >= item['min_m'] else item['p_detal']
                item_total = item['u'] * item['cant']
                subtotal_usd += item_total
                
                with st.container(border=True):
                    r1, r2 = st.columns([3.5, 1])
                    r1.markdown(f"**{item['nombre']}** (${item['u']:.2f} c/u)")
                    if r2.button("🗑️", key=f"del_{i}"): idx_borrar = i
                    
                    # Edición Directa de Cantidad
                    item['cant'] = st.number_input("Cantidad:", min_value=0.1, value=float(item['cant']), step=1.0, key=f"q_{i}")
            
            if idx_borrar > -1:
                st.session_state.car.pop(idx_borrar)
                st.rerun()

            st.divider()
            
            # --- D. Lógica de Cobro y Redondeo Flexible ---
            total_sugerido_bs = subtotal_usd * tasa_v
            
            c_tot1, c_tot2 = st.columns(2)
            c_tot1.metric("Total USD", f"${subtotal_usd:,.2f}")
            c_tot2.metric("Total Sugerido Bs", f"{total_sugerido_bs:,.2f} Bs")

            # Campo de Redondeo / Manual
            monto_final_bs = st.number_input("💵 Total Real a Cobrar (Bs)", value=float(total_sugerido_bs), step=0.1, help="Ajuste aquí para redondeo")
            
            with st.expander("💳 REGISTRO DE PAGOS MIXTOS", expanded=True):
                pc1, pc2 = st.columns(2)
                p_ef_bs = pc1.number_input("Efectivo Bs", 0.0)
                p_pm_bs = pc1.number_input("Pago Móvil Bs", 0.0)
                p_pu_bs = pc1.number_input("Punto Venta Bs", 0.0)
                
                p_di_usd = pc2.number_input("Divisas $", 0.0)
                p_ze_usd = pc2.number_input("Zelle $", 0.0)
                p_ot_usd = pc2.number_input("Otros $", 0.0)

            # Cálculo de Vuelto en Bs
            total_pagado_bs = p_ef_bs + p_pm_bs + p_pu_bs + ((p_di_usd + p_ze_usd + p_ot_usd) * tasa_v)
            vuelto_bs = total_pagado_bs - monto_final_bs
            
            if vuelto_bs >= 0:
                st.success(f"### Vuelto: {vuelto_bs:,.2f} Bs.")
            else:
                st.error(f"### Pendiente: {abs(vuelto_bs):,.2f} Bs.")

            # --- E. Procesamiento de Venta ---
            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
                if total_pagado_bs < (monto_final_bs - 0.01):
                    st.error("El monto pagado es insuficiente.")
                else:
                    try:
                        ahora = datetime.now()
                        id_tx = f"TX-{ahora.strftime('%y%m%d%H%M%S')}"
                        
                        for x in st.session_state.car:
                            # Inserción en tabla Ventas
                            db.table("ventas").insert({
                                "id_transaccion": id_tx,
                                "id_cierre": id_turno,
                                "producto": x['nombre'],
                                "cantidad": x['cant'],
                                "total_usd": x['u'] * x['cant'],
                                "tasa_cambio": tasa_v,
                                "pago_efectivo": p_ef_bs,
                                "pago_punto": p_pu_bs,
                                "pago_movil": p_pm_bs,
                                "pago_zelle": p_ze_usd,
                                "pago_otros": p_ot_usd,
                                "pago_divisas": p_di_usd,
                                "costo_venta": x['costo'] * x['cant'],
                                "monto_cobrado_bs": monto_final_bs,
                                "fecha": ahora.isoformat()
                            }).execute()
                            
                            # Actualización de Stock (Resta)
                            res_inv = db.table("inventario").select("stock").eq("id", x['id']).execute()
                            if res_inv.data:
                                n_stock = res_inv.data[0]['stock'] - x['cant']
                                db.table("inventario").update({"stock": n_stock}).eq("id", x['id']).execute()

                        # Generar Ticket Visual
                        st.session_state.ultimo_ticket = f"""
                        <div style='background-color:white; padding:15px; border:1px solid #ccc; font-family:monospace; color:black;'>
                            <center><b>🚢 MEDITERRANEO EXPRESS</b><br>RIF: J-504621184</center><br>
                            ID: {id_tx}<br>FECHA: {ahora.strftime('%d/%m/%Y %H:%M')}<hr>
                            <p>TOTAL BS: {monto_final_bs:,.2f}<br>TASA: {tasa_v:,.2f}</p>
                            <p>PAGADO: {total_pagado_bs:,.2f} Bs.<br>VUELTO: {vuelto_bs:,.2f} Bs.</p>
                            <center>¡GRACIAS POR SU COMPRA!</center>
                        </div>
                        """
                        st.session_state.venta_finalizada = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error crítico: {e}")

    # --- F. HISTORIAL DEL TURNO ACTUAL (ESTILO EXCEL CON ANULACIÓN) ---
    st.divider()
    st.markdown("### 📊 Historial de Ventas y Anulaciones")
    
    try:
        # Solo ventas del turno activo
        res_h = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        if res_h.data:
            for v in res_h.data:
                dt_obj = datetime.fromisoformat(v['fecha'])
                with st.container(border=True):
                    c_h1, c_h2, c_h3, c_h4, c_h5, c_h6 = st.columns([1, 2.5, 1, 1, 1.5, 1])
                    c_h1.write(dt_obj.strftime('%H:%M'))
                    c_h2.write(f"**{v['producto']}**")
                    c_h3.write(f"x{v['cantidad']}")
                    c_h4.write(f"${v['total_usd']:.2f}")
                    c_h5.write(f"{v['monto_cobrado_bs']:.2f} Bs")
                    
                    # Lógica de Anulación
                    if c_h6.button("🚫 Anular", key=f"anular_{v['id']}"):
                        # 1. Devolver Stock
                        res_stock = db.table("inventario").select("stock").eq("nombre", v['producto']).execute()
                        if res_stock.data:
                            stock_actual = res_stock.data[0]['stock']
                            db.table("inventario").update({"stock": stock_actual + v['cantidad']}).eq("nombre", v['producto']).execute()
                        
                        # 2. Eliminar Registro
                        db.table("ventas").delete().eq("id", v['id']).execute()
                        st.toast(f"Venta {v['id']} Anulada. Stock devuelto.")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No hay ventas registradas en este turno.")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

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


