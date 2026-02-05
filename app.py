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
    
    # Obtener Turno Activo (id_cierre)
    try:
        res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        if not res_caja.data:
            st.error("🚫 SISTEMA BLOQUEADO: No hay un turno de caja abierto.")
            st.info("Por favor, vaya al módulo 'Cierre de Caja' e inicie una nueva jornada.")
            st.stop()
        turno_actual = res_caja.data[0]
        id_turno = turno_actual['id']
        tasa_v = st.session_state.tasa_dia
    except Exception as e:
        st.error(f"Error Crítico de Base de Datos: {e}"); st.stop()

    st.markdown(f"<h1 style='color:#0041C2;'>🛒 Terminal de Ventas <span style='font-size:18px; color:grey;'>| Turno #{id_turno}</span></h1>", unsafe_allow_html=True)

    # B. Lógica de "Nueva Venta" (Pantalla de Éxito)
    if st.session_state.venta_finalizada:
        st.balloons()
        c_p1, c_p2 = st.columns([1, 2])
        with c_p1:
            st.markdown(st.session_state.ultimo_ticket, unsafe_allow_html=True)
        with c_p2:
            st.success("### ✅ ¡VENTA REGISTRADA CON ÉXITO!")
            if st.button("🔄 REGISTRAR NUEVA VENTA", type="primary", use_container_width=True):
                st.session_state.car = []
                st.session_state.venta_finalizada = False
                st.rerun()
        st.stop()

    # C. Layout Principal (Buscador y Carrito)
    col_izq, col_der = st.columns([1.2, 1])

    with col_izq:
        st.subheader("🔍 Buscador Inteligente")
        busc_term = st.text_input("Escriba el nombre del producto...", placeholder="Ej: Harina, Arroz...", key="main_search").strip()
        
        if busc_term:
            res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc_term}%").limit(5).execute()
            if res_p.data:
                for p in res_p.data:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{p['nombre']}**\n\nStock: `{p['stock']}`")
                        c2.markdown(f"<p style='color:green; font-weight:bold;'>${p['precio_detal']:.2f}</p>", unsafe_allow_html=True)
                        if c3.button("➕ Añadir", key=f"add_{p['id']}", use_container_width=True):
                            # Lógica de precio según stock/mayor
                            p_unit = float(p['precio_detal'])
                            st.session_state.car.append({
                                "id": p['id'], "nombre": p['nombre'], "cant": 1, 
                                "u": p_unit, "costo": float(p['costo']), "min_m": p['min_mayor'],
                                "p_detal": float(p['precio_detal']), "p_mayor": float(p['precio_mayor'])
                            })
                            st.rerun()
            else:
                st.warning("Producto no encontrado.")

    with col_der:
        st.subheader("📋 Detalle del Pedido")
        if not st.session_state.car:
            st.info("El carrito está vacío.")
        else:
            subtotal_usd = 0
            idx_to_remove = -1
            
            for i, item in enumerate(st.session_state.car):
                # Calcular precio dinámico según cantidad
                item['u'] = item['p_mayor'] if item['cant'] >= item['min_m'] else item['p_detal']
                item_total = item['u'] * item['cant']
                subtotal_usd += item_total
                
                with st.container(border=True):
                    row1, row2 = st.columns([3, 1])
                    row1.markdown(f"**{item['nombre']}**")
                    if row2.button("🗑️", key=f"del_{i}"): idx_to_remove = i
                    
                    c_a, c_b, c_c = st.columns([1.5, 2, 1.5])
                    if c_a.button("➖", key=f"min_{i}"):
                        if item['cant'] > 1: item['cant'] -= 1; st.rerun()
                    c_b.markdown(f"<h4 style='text-align:center;'>{item['cant']}</h4>", unsafe_allow_html=True)
                    if c_c.button("➕", key=f"pls_{i}"):
                        item['cant'] += 1; st.rerun()
                    st.caption(f"Precio: ${item['u']:.2f} | Subtotal: ${item_total:.2f}")

            if idx_to_remove > -1:
                st.session_state.car.pop(idx_to_remove); st.rerun()

            st.divider()
            
            # D. Totales y Caja Mixta
            total_factura = st.number_input("Total a Cobrar ($)", value=float(subtotal_usd), step=0.01)
            total_bs = total_factura * tasa_v
            
            st.markdown(f"### Total: `{total_factura:,.2f}$` / `{total_bs:,.2f} Bs.`")
            
            with st.expander("💳 REGISTRO DE PAGOS MIXTOS", expanded=True):
                p_col1, p_col2 = st.columns(2)
                v_ef_bs = p_col1.number_input("Efectivo Bs", min_value=0.0)
                v_pm_bs = p_col1.number_input("Pago Móvil Bs", min_value=0.0)
                v_pu_bs = p_col1.number_input("Punto Venta Bs", min_value=0.0)
                
                v_di_usd = p_col2.number_input("Divisas $", min_value=0.0)
                v_ze_usd = p_col2.number_input("Zelle $", min_value=0.0)
                v_ot_usd = p_col2.number_input("Otros $", min_value=0.0)

            # E. Monitor de Pago en Tiempo Real
            pagado_usd = v_di_usd + v_ze_usd + v_ot_usd + ((v_ef_bs + v_pm_bs + v_pu_bs) / tasa_v)
            pendiente = total_factura - pagado_usd
            
            if pendiente > 0.01:
                st.metric("Monto Pendiente", f"${pendiente:,.2f}", delta=f"-{pendiente*tasa_v:,.2f} Bs", delta_color="inverse")
            else:
                st.metric("Vuelto / Cambio", f"${abs(pendiente):,.2f}", delta=f"{abs(pendiente)*tasa_v:,.2f} Bs")

            # F. Finalización de Venta
            if st.button("🚀 FINALIZAR Y FACTURAR", type="primary", use_container_width=True):
                if pendiente > 0.05:
                    st.error(f"Faltan ${pendiente:,.2f} para completar el pago.")
                else:
                    try:
                        ahora = datetime.now()
                        id_tx = f"TX-{ahora.strftime('%y%m%d%H%M%S')}"
                        
                        # Guardar cada item en la tabla ventas
                        for x in st.session_state.car:
                            db.table("ventas").insert({
                                "id_transaccion": id_tx,
                                "id_cierre": id_turno,
                                "producto": x['nombre'],
                                "cantidad": x['cant'],
                                "total_usd": x['u'] * x['cant'],
                                "total_pagado_real": total_factura,
                                "tasa_cambio": tasa_v,
                                "pago_efectivo": v_ef_bs,
                                "pago_punto": v_pu_bs,
                                "pago_movil": v_pm_bs,
                                "pago_zelle": v_ze_usd,
                                "pago_divisas": v_di_usd,
                                "pago_otros": v_ot_usd,
                                "costo_venta": x['costo'] * x['cant'],
                                "fecha": ahora.isoformat()
                            }).execute()
                            
                            # Descuento de Stock
                            res_inv = db.table("inventario").select("stock").eq("id", x['id']).execute()
                            if res_inv.data:
                                nuevo_stock = res_inv.data[0]['stock'] - x['cant']
                                db.table("inventario").update({"stock": nuevo_stock}).eq("id", x['id']).execute()

                        # Generar Ticket
                        st.session_state.ultimo_ticket = f"""
                        <div style='background-color:#f0f0f0; padding:20px; border-radius:10px; font-family:monospace; border:1px dashed #333;'>
                            <h3 style='text-align:center;'>🚢 MEDITERRANEO EXPRESS</h3>
                            <p style='text-align:center;'>Ticket: {id_tx}<br>Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}</p>
                            <hr>
                            <p><b>Total Cobrado: ${total_factura:,.2f}</b><br>
                            Tasa: {tasa_v:,.2f} Bs/$<br>
                            Pagado en Bs: {(v_ef_bs + v_pm_bs + v_pu_bs):,.2f}<br>
                            Pagado en USD: {(v_di_usd + v_ze_usd + v_ot_usd):,.2f}</p>
                            <p style='text-align:center;'>*** Gracias por su compra ***</p>
                        </div>
                        """
                        st.session_state.venta_finalizada = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

    # --- SECCIÓN: HISTORIAL DEL TURNO ACTUAL ---
    st.divider()
    st.markdown("### 📊 Historial de Ventas - Turno Actual")
    
    try:
        res_hist = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        if res_hist.data:
            df_hist = pd.DataFrame(res_hist.data)
            
            # Formatear para visualización
            df_hist['Hora'] = pd.to_datetime(df_hist['fecha']).dt.strftime('%H:%M')
            
            # Agrupar por transacción para mostrar limpio
            df_view = df_hist.groupby('id_transaccion').agg({
                'Hora': 'first',
                'producto': lambda x: ", ".join(x),
                'total_usd': 'sum',
                'pago_efectivo': 'first',
                'pago_punto': 'first',
                'pago_movil': 'first',
                'pago_divisas': 'first',
                'pago_zelle': 'first'
            }).reset_index()

            st.dataframe(
                df_view.rename(columns={
                    'id_transaccion': 'Ticket',
                    'producto': 'Productos',
                    'total_usd': 'Monto ($)'
                })[['Hora', 'Ticket', 'Productos', 'Monto ($)']],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Aún no hay ventas registradas en este turno.")
    except Exception as e:
        st.error(f"No se pudo cargar el historial: {e}")

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



