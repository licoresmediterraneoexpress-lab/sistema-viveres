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

        # Diálogo de Edición Refactorizado
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

    # Registro de nuevos productos (Mantenido funcionalmente)
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

# --- 4. MÓDULO VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    if 'tasa_dia' not in st.session_state: st.session_state.tasa_dia = 60.0
    if 'venta_finalizada' not in st.session_state: st.session_state.venta_finalizada = False
    if 'ultimo_ticket' not in st.session_state: st.session_state.ultimo_ticket = ""

    try:
        res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        if not res_caja.data:
            st.error("🚫 TURNO CERRADO. Debe realizar una apertura en 'Cierre de Caja'.")
            st.stop()
        turno_actual = res_caja.data[0]
    except:
        st.error("Error de conexión"); st.stop()

    st.header("🛒 Ventas Mediterraneo Express")
    
    with st.sidebar:
        st.subheader("⚙️ Configuración")
        st.session_state.tasa_dia = st.number_input("Tasa BCV (Bs/$)", min_value=1.0, value=st.session_state.tasa_dia, format="%.2f")
        if st.button("🧹 Vaciar Carrito"):
            st.session_state.car = []; st.rerun()

    if st.session_state.venta_finalizada:
        st.success("✅ VENTA COMPLETADA")
        st.code(st.session_state.ultimo_ticket, language="text")
        if st.button("🔄 NUEVA VENTA", type="primary"):
            st.session_state.car = []; st.session_state.venta_finalizada = False; st.rerun()
        st.stop()

    st.subheader("🔍 Selección de Productos")
    busc = st.text_input("Buscar producto...", key="txt_busc").strip().lower()

    if busc:
        res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc}%").execute()
        if res_p.data:
            df_f = pd.DataFrame(res_p.data)
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                item_sel = col1.selectbox(f"Resultados ({len(df_f)})", df_f['nombre'].tolist())
                p_data = df_f[df_f['nombre'] == item_sel].iloc[0]
                col2.metric("Stock", f"{p_data['stock']:.0f}")
                cant_sel = col3.number_input("Cantidad", min_value=1, value=1)
                
                if st.button("➕ Añadir al Carrito", type="primary"):
                    p_u = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                    st.session_state.car.append({
                        "p": item_sel, "c": cant_sel, "u": p_u, "t": round(p_u * cant_sel, 2),
                        "costo_u": float(p_data['costo']), "min_m": p_data['min_mayor'],
                        "p_detal": float(p_data['precio_detal']), "p_mayor": float(p_data['precio_mayor'])
                    })
                    st.rerun()

    if st.session_state.car:
        st.divider()
        st.subheader("📋 Resumen del Pedido")
        indices_a_borrar = []
        for i, item in enumerate(st.session_state.car):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
                c1.write(f"**{item['p']}**")
                n_c = c2.number_input("Cant.", min_value=1, value=item['c'], key=f"edit_q_{i}")
                if n_c != item['c']:
                    item['c'] = n_c
                    item['u'] = item['p_mayor'] if n_c >= item['min_m'] else item['p_detal']
                    item['t'] = round(item['u'] * n_c, 2); st.rerun()
                c3.write(f"${item['u']:.2f}"); c4.write(f"**${item['t']:.2f}**")
                if c5.button("🗑️", key=f"del_{i}"): indices_a_borrar.append(i)

        for idx in sorted(indices_a_borrar, reverse=True): st.session_state.car.pop(idx); st.rerun()

        sub_total = sum(item['t'] for item in st.session_state.car)
        tasa = st.session_state.tasa_dia
        st.markdown(f"### Total: ${sub_total:,.2f} / {(sub_total * tasa):,.2f} Bs.")
        
        with st.expander("💳 Registro de Pago", expanded=True):
            p1, p2, p3 = st.columns(3)
            ef_bs = p1.number_input("Efectivo Bs", 0.0)
            pm_bs = p1.number_input("Pago Móvil Bs", 0.0)
            pu_bs = p2.number_input("Punto Bs", 0.0)
            di_usd = p2.number_input("Divisas $", 0.0)
            ze_usd = p3.number_input("Zelle $", 0.0)
            total_pagado_bs = ef_bs + pm_bs + pu_bs + (di_usd * tasa) + (ze_usd * tasa)
            st.metric("Vuelto Bs", f"{max(0, total_pagado_bs - (sub_total * tasa)):,.2f} Bs")

        if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
            if total_pagado_bs < (sub_total * tasa - 0.05):
                st.error("Monto insuficiente")
            else:
                ahora = datetime.now()
                id_tx = f"TX-{ahora.strftime('%y%m%d%H%M%S')}"
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "id_transaccion": id_tx, "producto": x['p'], "cantidad": x['c'], 
                        "total_usd": x['t'], "tasa_cambio": tasa, "pago_efectivo": ef_bs, 
                        "pago_punto": pu_bs, "pago_movil": pm_bs, "pago_zelle": ze_usd, 
                        "pago_divisas": di_usd, "costo_venta": x['costo_u'] * x['c'], "fecha": ahora.isoformat()
                    }).execute()
                    inv = db.table("inventario").select("stock").eq("nombre", x['p']).execute()
                    if inv.data: db.table("inventario").update({"stock": inv.data[0]['stock'] - x['c']}).eq("nombre", x['p']).execute()
                
                ticket = f"MEDITERRANEO EXPRESS\nTicket: {id_tx}\nTotal: ${sub_total:.2f}\nPagado Bs: {total_pagado_bs:.2f}"
                st.session_state.ultimo_ticket = ticket
                st.session_state.venta_finalizada = True; st.balloons(); st.rerun()

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 4. MÓDULO GESTIÓN DE CAJA ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Gestión de Turnos y Arqueo")
    st.markdown("---")

    # 1. Identificar estado del turno (Tabla 'cierres')
    try:
        res_u = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        turno_activo = res_u.data[0] if res_u.data else None
    except:
        turno_activo = None
    
    if not turno_activo:
        st.subheader("🔓 Apertura de Turno")
        with st.form("form_apertura"):
            c1, c2 = st.columns(2)
            f_usd = c1.number_input("Fondo Inicial ($)", min_value=0.0, format="%.2f")
            f_bs = c2.number_input("Fondo Inicial (Bs)", min_value=0.0, format="%.2f")
            t_ref = st.number_input("Tasa de Cambio Apertura", value=60.0)
            
            total_ap_usd = f_usd + (f_bs / t_ref) if t_ref > 0 else f_usd
            if st.form_submit_button("✅ INICIAR JORNADA", use_container_width=True):
                data_ap = {
                    "fecha_apertura": datetime.now().isoformat(),
                    "monto_apertura": total_ap_usd,
                    "estado": "abierto",
                    "total_ventas": 0, "total_costos": 0, "total_ganancias": 0
                }
                db.table("cierres").insert(data_ap).execute()
                st.success("Turno iniciado correctamente."); time.sleep(1); st.rerun()
    else:
        # Lógica de Arqueo en Tiempo Real
        id_cierre = turno_activo['id']
        f_ap = turno_activo['fecha_apertura']
        st.warning(f"🔔 TURNO ACTIVO | Inicio: {pd.to_datetime(f_ap).strftime('%d/%m/%Y %H:%M')}")

        # Diagrama de flujo del proceso de ventas a caja
        

        # Consulta consolidada de ventas desde la apertura
        try:
            res_v = db.table("ventas").select("*").gte("fecha", f_ap).execute()
            df_v = pd.DataFrame(res_v.data) if res_v.data else pd.DataFrame()
        except: df_v = pd.DataFrame()

        if not df_v.empty:
            for col in ['total_usd', 'costo_venta', 'pago_efectivo', 'pago_punto', 'pago_movil', 'pago_zelle', 'pago_divisas']:
                df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0)

            t_ventas = df_v['total_usd'].sum()
            t_costos = df_v['costo_venta'].sum()
            t_ganancia = t_ventas - t_costos

            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Ventas Totales", f"$ {t_ventas:,.2f}")
            m2.metric("📦 Costo de Ventas", f"$ {t_costos:,.2f}")
            m3.metric("💹 Ganancia Neta", f"$ {t_ganancia:,.2f}")

            st.write("#### 💳 Desglose de Cobros en Turno")
            p1, p2, p3 = st.columns(3)
            p1.info(f"**Divisas:** ${df_v['pago_divisas'].sum():,.2f}")
            p2.info(f"**Digital (Bs):** ${ (df_v['pago_punto'].sum() + df_v['pago_movil'].sum()):,.2f}")
            p3.info(f"**Zelle:** ${df_v['pago_zelle'].sum():,.2f}")
        else:
            st.info("Sin transacciones registradas en este turno."); t_ventas = t_costos = t_ganancia = 0

        st.divider()
        if st.button("🔴 CERRAR CAJA Y FINALIZAR TURNO", type="primary", use_container_width=True):
            data_cl = {
                "fecha_cierre": datetime.now().isoformat(),
                "total_ventas": float(t_ventas),
                "total_costos": float(t_costos),
                "total_ganancias": float(t_ganancia),
                "estado": "cerrado"
            }
            try:
                db.table("cierres").update(data_cl).eq("id", id_cierre).execute()
                st.balloons(); st.success("Turno finalizado y guardado."); time.sleep(1.5); st.rerun()
            except Exception as e: st.error(f"Error al cerrar: {e}")

