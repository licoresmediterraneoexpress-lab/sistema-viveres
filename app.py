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
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []
        st.rerun()

# --- 3. MÓDULO INVENTARIO REFACTORIZADO ---
if opcion == "📦 Inventario":
    st.header("📦 Centro de Control de Inventario")

    # 1. CARGA DE DATOS
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_inv.empty:
        # Limpieza y Formateo de tipos
        for col in ['stock', 'costo', 'precio_detal', 'precio_mayor']:
            df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

        # Cálculos de métricas
        df_inv['valor_costo'] = df_inv['stock'] * df_inv['costo']
        df_inv['valor_venta'] = df_inv['stock'] * df_inv['precio_detal']
        
        # --- FILA DE MÉTRICAS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("🛒 Inversión Total", f"${df_inv['valor_costo'].sum():,.2f}")
        m2.metric("💰 Valor de Venta", f"${df_inv['valor_venta'].sum():,.2f}")
        m3.metric("📈 Ganancia Est.", f"${(df_inv['valor_venta'].sum() - df_inv['valor_costo'].sum()):,.2f}")

        st.divider()

        # --- BUSCADOR INTELIGENTE ---
        busqueda = st.text_input("🔍 Filtro de búsqueda rápida", placeholder="Escriba el nombre del producto...")

        # Filtrado en tiempo real
        df_filtrado = df_inv[df_inv['nombre'].str.contains(busqueda, case=False)] if busqueda else df_inv

        # --- TABLA PROFESIONAL (Treeview Style) ---
        # Renombramos columnas para la vista del usuario
        vista_tabla = df_filtrado.copy()
        vista_tabla = vista_tabla.rename(columns={
            'nombre': 'PRODUCTO',
            'stock': 'STOCK',
            'costo': 'PRECIO COSTO',
            'precio_detal': 'PRECIO VENTA',
            'precio_mayor': 'PRECIO MAYOR'
        })

        # Aplicar formato de divisa para la visualización
        cols_moneda = ['PRECIO COSTO', 'PRECIO VENTA', 'PRECIO MAYOR']
        for col in cols_moneda:
            vista_tabla[col] = vista_tabla[col].apply(lambda x: f"${x:,.2f}")

        # Mostrar tabla principal
        st.subheader("📋 Existencias en Almacén")
        st.dataframe(
            vista_tabla[['PRODUCTO', 'STOCK', 'PRECIO COSTO', 'PRECIO VENTA', 'PRECIO MAYOR']], 
            use_container_width=True, 
            hide_index=True
        )

        # --- LÓGICA DE MODIFICACIÓN (POP-UP) ---
        
        @st.dialog("✏️ Editar Producto")
        def editar_producto_dialog(producto_data):
            st.write(f"Modificando: **{producto_data['nombre']}**")
            
            with st.form("edit_form"):
                new_stock = st.number_input("Cantidad (Stock)", value=int(producto_data['stock']), step=1)
                new_costo = st.number_input("Precio de Costo ($)", value=float(producto_data['costo']), format="%.2f")
                
                c1, c2 = st.columns(2)
                new_detal = c1.number_input("Venta Detal ($)", value=float(producto_data['precio_detal']), format="%.2f")
                new_mayor = c2.number_input("Venta Mayor ($)", value=float(producto_data['precio_mayor']), format="%.2f")
                
                submitted = st.form_submit_button("💾 Guardar Cambios")
                
                if submitted:
                    update_data = {
                        "stock": int(new_stock),
                        "costo": float(new_costo),
                        "precio_detal": float(new_detal),
                        "precio_mayor": float(new_mayor)
                    }
                    try:
                        db.table("inventario").update(update_data).eq("id", producto_data['id']).execute()
                        st.success("¡Actualizado con éxito!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")

        # Botón de acción para abrir el pop-up
        st.write("### Acciones")
        col_sel, col_del = st.columns([2, 1])
        
        with col_sel:
            prod_seleccionado = st.selectbox("Seleccione un producto para editar:", 
                                            options=df_filtrado['nombre'].tolist(),
                                            index=None,
                                            placeholder="Busque y elija un producto...")
            
            if prod_seleccionado:
                # Extraer datos de la fila seleccionada
                datos_fila = df_inv[df_inv['nombre'] == prod_seleccionado].iloc[0]
                if st.button(f"🛠️ Editar {prod_seleccionado}"):
                    editar_producto_dialog(datos_fila)

        with col_del:
            # Sección de eliminación simplificada
            with st.expander("🗑️ Eliminar"):
                prod_borrar = st.selectbox("Eliminar:", options=["---"] + df_inv['nombre'].tolist())
                clave = st.text_input("Seguridad", type="password")
                if st.button("Confirmar Borrado"):
                    if clave == CLAVE_ADMIN and prod_borrar != "---":
                        db.table("inventario").delete().eq("nombre", prod_borrar).execute()
                        st.success("Eliminado.")
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("Aún no hay productos en el inventario.")

    # --- REGISTRO DE NUEVOS PRODUCTOS (FUERA DE LA TABLA) ---
    st.divider()
    with st.expander("➕ REGISTRAR NUEVO PRODUCTO"):
        with st.form("registro_nuevo"):
            nombre_n = st.text_input("Nombre").upper().strip()
            c1, c2, c3 = st.columns(3)
            stock_n = c1.number_input("Stock Inicial", min_value=0)
            costo_n = c2.number_input("Costo ($)", format="%.2f")
            min_m_n = c3.number_input("Mín. Mayorista", value=12)
            
            c4, c5 = st.columns(2)
            detal_n = c4.number_input("P. Detal ($)", format="%.2f")
            mayor_n = c5.number_input("P. Mayor ($)", format="%.2f")
            
            if st.form_submit_button("Registrar en Sistema"):
                if nombre_n:
                    nuevo_p = {
                        "nombre": nombre_n, "stock": stock_n, "costo": costo_n,
                        "precio_detal": detal_n, "precio_mayor": mayor_n, "min_mayor": min_m_n
                    }
                    db.table("inventario").insert(nuevo_p).execute()
                    st.success("Registrado correctamente.")
                    time.sleep(1)
                    st.rerun()

elif opcion == "🛒 Venta Rápida":
    # 1. Inicialización de Estados Críticos
    if 'tasa_dia' not in st.session_state:
        st.session_state.tasa_dia = 60.0
    if 'car' not in st.session_state:
        st.session_state.car = []
    if 'venta_finalizada' not in st.session_state:
        st.session_state.venta_finalizada = False
    if 'ultimo_ticket' not in st.session_state:
        st.session_state.ultimo_ticket = ""

    # 2. Validación de Apertura de Caja
    try:
        res_caja = db.table("gastos").select("*").ilike("descripcion", "APERTURA_%").order("fecha", desc=True).limit(1).execute()
        if not res_caja.data or res_caja.data[0]['estado'] == 'cerrado':
            st.error("🚫 TURNO CERRADO. Debe realizar una apertura en el módulo de Gastos.")
            st.stop()
        ultimo_turno = res_caja.data[0]
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

    st.header("🛒 Ventas Mediterraneo Express")
    
    with st.sidebar:
        st.subheader("⚙️ Configuración")
        st.session_state.tasa_dia = st.number_input("Tasa BCV (Bs/$)", min_value=1.0, value=st.session_state.tasa_dia, format="%.2f")
        st.info(f"📍 Turno: {ultimo_turno['descripcion']}")
        if not st.session_state.venta_finalizada:
            if st.button("🧹 Vaciar Carrito"):
                st.session_state.car = []
                st.rerun()

    tasa = st.session_state.tasa_dia

    # 3. Pantalla de Ticket Finalizado (Persistencia)
    if st.session_state.venta_finalizada:
        st.success("✅ ¡VENTA COMPLETADA CON ÉXITO!")
        st.code(st.session_state.ultimo_ticket, language="text")
        c_p1, c_p2 = st.columns(2)
        c_p1.download_button("📥 Descargar Ticket", st.session_state.ultimo_ticket, file_name="ticket.txt", use_container_width=True)
        if c_p2.button("🔄 NUEVA VENTA", type="primary", use_container_width=True):
            st.session_state.car = []
            st.session_state.venta_finalizada = False
            st.session_state.ultimo_ticket = ""
            st.rerun()
        st.stop()

    # 4. Buscador Inteligente
    st.subheader("🔍 Selección de Productos")
    busc = st.text_input("Buscar producto...", placeholder="Escriba para filtrar...", key="txt_busc").strip().lower()

    if busc:
        res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc}%").execute()
        if res_p.data:
            df_f = pd.DataFrame(res_p.data)
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                item_sel = col1.selectbox(f"Coincidencias ({len(df_f)})", df_f['nombre'].tolist())
                p_data = df_f[df_f['nombre'] == item_sel].iloc[0]
                
                col2.metric("Stock", f"{p_data['stock']:.0f}")
                cant_sel = col3.number_input("Cantidad", min_value=1, max_value=int(p_data['stock']) if p_data['stock'] > 0 else 1, value=1, key="add_qty")
                
                if st.button("➕ Añadir al Carrito", use_container_width=True, type="primary"):
                    # Determinar precio inicial (detal o mayor)
                    p_u = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                    
                    existe = next((item for item in st.session_state.car if item['p'] == item_sel), None)
                    if existe:
                        existe['c'] += cant_sel
                        # Re-evaluar precio por nueva cantidad acumulada
                        p_u = float(p_data['precio_mayor']) if existe['c'] >= p_data['min_mayor'] else float(p_data['precio_detal'])
                        existe['u'], existe['t'] = p_u, round(p_u * existe['c'], 2)
                    else:
                        st.session_state.car.append({
                            "p": item_sel, "c": cant_sel, "u": p_u, "t": round(p_u * cant_sel, 2),
                            "costo_u": float(p_data['costo']), "min_m": p_data['min_mayor'],
                            "p_detal": float(p_data['precio_detal']), "p_mayor": float(p_data['precio_mayor'])
                        })
                    st.rerun()
        else:
            st.info("No hay coincidencias.")

    # 5. Carrito Editable (Resumen Dinámico)
    if st.session_state.car:
        st.divider()
        st.subheader("📋 Resumen del Pedido")
        
        indices_a_borrar = []
        
        for i, item in enumerate(st.session_state.car):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
                
                c1.write(f"**{item['p']}**")
                
                # Input de cantidad editable
                n_c = c2.number_input("Cant.", min_value=1, value=item['c'], key=f"edit_q_{i}")
                
                # Lógica de Recalculo si cambia la cantidad
                if n_c != item['c']:
                    item['c'] = n_c
                    # Aplicar regla de Oro: Detal vs Mayor
                    nuevo_p_u = item['p_mayor'] if n_c >= item['min_m'] else item['p_detal']
                    item['u'] = nuevo_p_u
                    item['t'] = round(nuevo_p_u * n_c, 2)
                    st.rerun()

                c3.write(f"Unit: ${item['u']:.2f}")
                c4.write(f"Subt: **${item['t']:.2f}**")
                
                if c5.button("🗑️", key=f"del_item_{i}"):
                    indices_a_borrar.append(i)

        if indices_a_borrar:
            for idx in sorted(indices_a_borrar, reverse=True):
                st.session_state.car.pop(idx)
            st.rerun()

        # 6. Totales y Pagos
        sub_total_usd = sum(item['t'] for item in st.session_state.car)
        st.markdown(f"### Total Sugerido: **${sub_total_usd:,.2f} / {(sub_total_usd * tasa):,.2f} Bs.**")
        
        monto_final_bs = st.number_input("Monto Final a Cobrar (Bs)", value=float(sub_total_usd * tasa), format="%.2f")
        
        with st.expander("💳 Registro de Pago Mixto", expanded=True):
            p1, p2, p3 = st.columns(3)
            ef_bs = p1.number_input("Efectivo Bs", 0.0)
            pm_bs = p1.number_input("Pago Móvil Bs", 0.0)
            pu_bs = p2.number_input("Punto Bs", 0.0)
            di_usd = p2.number_input("Divisas $", 0.0)
            ze_usd = p3.number_input("Zelle $", 0.0)
            
            total_pagado_bs = ef_bs + pm_bs + pu_bs + (di_usd * tasa) + (ze_usd * tasa)
            vuelto_bs = total_pagado_bs - monto_final_bs
            
            if total_pagado_bs > 0:
                col_v1, col_v2 = st.columns(2)
                col_v1.metric("Vuelto Bs", f"{max(0, vuelto_bs):,.2f} Bs")
                col_v2.metric("Vuelto $", f"${max(0, vuelto_bs/tasa):,.2f}")

        # 7. Finalización de Venta
        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            if total_pagado_bs < (monto_final_bs - 0.05):
                st.error("Monto insuficiente.")
            else:
                try:
                    ahora = datetime.now()
                    id_tx = f"TX-{ahora.strftime('%y%m%d%H%M%S')}"
                    
                    with st.status("Registrando en base de datos...", expanded=True) as status:
                        for x in st.session_state.car:
                            # Insertar en Supabase
                            db.table("ventas").insert({
                                "id_transaccion": id_tx, "producto": x['p'], "cantidad": x['c'], 
                                "total_usd": x['t'], "tasa_cambio": tasa, "pago_efectivo": ef_bs, 
                                "pago_punto": pu_bs, "pago_movil": pm_bs, "pago_zelle": ze_usd, 
                                "pago_divisas": di_usd, "costo_venta": x['costo_u'] * x['c'], "fecha": ahora.isoformat()
                            }).execute()
                            
                            # Descontar Stock
                            inv = db.table("inventario").select("stock").eq("nombre", x['p']).execute()
                            if inv.data:
                                db.table("inventario").update({"stock": inv.data[0]['stock'] - x['c']}).eq("nombre", x['p']).execute()
                        
                        status.update(label="✅ Registrado", state="complete")

                    # Generar Ticket
                    ticket = f"""
==============================
    MEDITERRANEO EXPRESS
    Ticket: {id_tx}
    Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}
==============================
PRODUCTOS:
"""
                    for x in st.session_state.car:
                        ticket += f"{x['p'][:18]:<18} x{x['c']} ${x['t']}\n"
                    
                    ticket += f"""------------------------------
TOTAL BS:     {monto_final_bs:>10.2f}
TOTAL USD:    ${(monto_final_bs/tasa):>10.2f}
TASA:         {tasa:>10.2f}
------------------------------
PAGADO BS:    {total_pagado_bs:>10.2f}
VUELTO BS:    {max(0, vuelto_bs):>10.2f}
==============================
"""
                    st.session_state.ultimo_ticket = ticket
                    st.session_state.venta_finalizada = True
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error crítico: {e}")
                    
# // INICIO NUEVA FUNCIÓN: Centro de Gestión Administrativa (REPARADO)
    st.divider()
    st.header("📊 Centro de Control de Ventas")

    # 1. Filtros Inteligentes
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 2])
        fecha_filtro = f_col1.date_input("📅 Fecha de Reporte", date.today())
        busc_general = f_col2.text_input("🔍 Filtro rápido", placeholder="Buscar por Cliente, Producto o Ticket...", key="admin_search")

    # 2. Extracción de Datos Directa (Persistencia MySQL/Supabase)
    res_h = db.table("ventas").select("*").gte("fecha", fecha_filtro.isoformat()).order("fecha", desc=True).execute()

    if res_h.data:
        df_raw = pd.DataFrame(res_h.data)
        
        # Normalización y Limpieza
        df_raw['id_transaccion'] = df_raw['id_transaccion'].fillna(df_raw['id'].astype(str))
        df_raw['cliente'] = df_raw.get('cliente', 'Cliente General').fillna('Cliente General')
        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'])
        df_raw = df_raw[df_raw['fecha_dt'].dt.date == fecha_filtro]

        if not df_raw.empty:
            # Lógica de Agrupación para UI
            def summarize_products(prods):
                items = list(prods)
                primero = items[0]
                extras = len(items) - 1
                return f"{primero} (+{extras} más)" if extras > 0 else primero

            v_maestra = df_raw.groupby('id_transaccion').agg({
                'fecha_dt': 'first',
                'cliente': 'first',
                'producto': summarize_products,
                'total_usd': 'sum',
                'tasa_cambio': 'first'
            }).reset_index()

            v_maestra['Total Bs'] = v_maestra['total_usd'] * v_maestra['tasa_cambio']
            v_maestra['Hora'] = v_maestra['fecha_dt'].dt.strftime('%H:%M')
            v_maestra = v_maestra.rename(columns={'id_transaccion': 'Ticket', 'cliente': 'Cliente', 'producto': 'Productos', 'total_usd': 'Total $'})

            # Filtro en Tiempo Real
            if busc_general:
                q = busc_general.lower()
                v_maestra = v_maestra[v_maestra.apply(lambda x: q in str(x).lower(), axis=1)]

            v_maestra['Anular'] = False

            # --- VISTA DE TABLA ---
            st.subheader("📋 Relación Diaria")
            edited_df = st.data_editor(
                v_maestra[['Ticket', 'Hora', 'Cliente', 'Productos', 'Total $', 'Total Bs', 'Anular']],
                column_config={
                    "Anular": st.column_config.CheckboxColumn("🗑️", help="Marque para eliminar permanentemente"),
                    "Total $": st.column_config.NumberColumn(format="$ %.2f"),
                    "Total Bs": st.column_config.NumberColumn(format="Bs %.2f")
                },
                use_container_width=True, hide_index=True, key="editor_ventas_fix"
            )

            # --- LÓGICA DE ELIMINACIÓN REAL Y PERSISTENTE ---
            tickets_para_borrar = edited_df[edited_df['Anular'] == True]['Ticket'].tolist()

            if tickets_para_borrar:
                tx_id = tickets_para_borrar[0]
                st.error(f"⚠️ ¿Eliminar permanentemente el Ticket **{tx_id}**?")
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("🔥 CONFIRMAR: BORRAR Y DEVOLVER STOCK", use_container_width=True):
                    with st.spinner("Procesando cambios en Base de Datos..."):
                        try:
                            # 1. Obtener los productos vinculados a esa transacción antes de borrar
                            # Filtramos del df_raw original para tener el detalle preciso
                            items_de_esta_venta = df_raw[df_raw['id_transaccion'] == tx_id]
                            
                            for _, fila in items_de_esta_venta.iterrows():
                                # 2. Recuperar Stock
                                prod_nombre = fila['producto']
                                cant_vendida = fila['cantidad']
                                
                                inv_res = db.table("inventario").select("stock").eq("nombre", prod_nombre).execute()
                                if inv_res.data:
                                    stock_actual = inv_res.data[0]['stock']
                                    db.table("inventario").update({"stock": stock_actual + cant_vendida}).eq("nombre", prod_nombre).execute()
                            
                            # 3. Borrar de la Base de Datos definitivamente
                            db.table("ventas").delete().eq("id_transaccion", tx_id).execute()
                            
                            st.success(f"Venta {tx_id} eliminada. Inventario actualizado.")
                            time.sleep(1)
                            # Limpiar estados de selección para evitar bucles
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error de persistencia: {str(e)}")
                
                if c_btn2.button("❌ CANCELAR", use_container_width=True):
                    st.rerun()

            # 6. Exportación (Intacta)
            st.divider()
            csv = v_maestra.drop(columns=['Anular']).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Reporte Excel", csv, f"ventas_{fecha_filtro}.csv", "text/csv", use_container_width=True)

        else:
            st.info("No hay registros para este filtro.")
    else:
        st.info(f"Sin ventas el {fecha_filtro}.")
    # // FIN NUEVA FUNCIÓN    

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 6. MÓDULO DE CAJA ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Gestión de Turnos y Arqueo")
    res_ultimo = db.table("gastos").select("*").ilike("descripcion", "APERTURA_%").order("fecha", desc=True).limit(1).execute()
    ultimo_registro = res_ultimo.data[0] if res_ultimo.data else None
    caja_abierta_actual = ultimo_registro is not None and ultimo_registro.get('estado') == 'abierto'

    if not caja_abierta_actual:
        st.info("🔓 No hay turnos activos.")
        with st.form("form_apertura"):
            tasa_ap = st.number_input("Tasa del Día", value=60.0)
            f_bs = st.number_input("Fondo Inicial Bs", 0.0)
            f_usd = st.number_input("Fondo Inicial $", 0.0)
            if st.form_submit_button("✅ ABRIR NUEVO TURNO"):
                id_turno = datetime.now().strftime("%Y%m%d_%H%M%S")
                db.table("gastos").insert({"descripcion": f"APERTURA_{id_turno}", "monto_usd": f_usd + (f_bs / tasa_ap), "monto_bs_extra": f_bs, "fecha": datetime.now().isoformat(), "estado": "abierto"}).execute()
                st.success("Turno abierto.")
                st.rerun()
    else:
        st.warning(f"🔔 Turno Activo: {ultimo_registro['descripcion']}")
        if st.button("🏮 CERRAR TURNO", type="primary"):
            db.table("gastos").update({"estado": "cerrado"}).eq("descripcion", ultimo_registro['descripcion']).execute()
            st.success("Turno cerrado.")
            st.rerun()














