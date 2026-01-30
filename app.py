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

# --- 3. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Centro de Control de Inventario")
    
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_inv.empty:
        for col in ['stock', 'costo', 'precio_detal', 'precio_mayor']:
            df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)
        
        df_inv['valor_costo'] = df_inv['stock'] * df_inv['costo']
        df_inv['valor_venta'] = df_inv['stock'] * df_inv['precio_detal']
        df_inv['ganancia_estimada'] = df_inv['valor_venta'] - df_inv['valor_costo']

        m1, m2, m3 = st.columns(3)
        m1.metric("🛒 Inversión Total", f"${df_inv['valor_costo'].sum():,.2f}")
        m2.metric("💰 Valor de Venta", f"${df_inv['valor_venta'].sum():,.2f}")
        m3.metric("📈 Ganancia Proyectada", f"${df_inv['ganancia_estimada'].sum():,.2f}")

        st.divider()
        bus_inv = st.text_input("🔍 Buscar producto...", placeholder="Escriba nombre del producto...")
        df_m = df_inv[df_inv['nombre'].str.contains(bus_inv, case=False)] if bus_inv else df_inv
        
        def alert_stock(stk):
            return "❌ Agotado" if stk <= 0 else "⚠️ Bajo" if stk <= 10 else "✅ OK"
        
        df_m['Estado'] = df_m['stock'].apply(alert_stock)
        st.subheader("📋 Existencias en Almacén")
        st.dataframe(df_m[['Estado', 'nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)

    st.divider()
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        with st.expander("📝 REGISTRAR O ACTUALIZAR PRODUCTO", expanded=True):
            with st.form("form_registro_final", clear_on_submit=False):
                n_prod = st.text_input("Nombre del Producto").strip().upper()
                c1, c2 = st.columns(2)
                s_prod = c1.number_input("Cantidad en Stock", min_value=0.0, step=1.0)
                cost_p = c2.number_input("Costo Compra ($)", min_value=0.0, format="%.2f")
                c3, c4 = st.columns(2)
                detal_p = c3.number_input("Venta Detal ($)", min_value=0.0, format="%.2f")
                mayor_p = c4.number_input("Venta Mayor ($)", min_value=0.0, format="%.2f")
                m_mayor = st.number_input("Mínimo para Mayorista", min_value=1, value=12)
                btn_guardar = st.form_submit_button("💾 GUARDAR CAMBIOS EN INVENTARIO")
                
                if btn_guardar:
                    if n_prod:
                        data_p = {
                            "nombre": n_prod, "stock": int(s_prod), "costo": float(cost_p),
                            "precio_detal": float(detal_p), "precio_mayor": float(mayor_p), "min_mayor": int(m_mayor)
                        }
                        try:
                            check = db.table("inventario").select("id").eq("nombre", n_prod).execute()
                            if check.data:
                                db.table("inventario").update(data_p).eq("nombre", n_prod).execute()
                                st.success(f"✅ '{n_prod}' actualizado.")
                            else:
                                db.table("inventario").insert(data_p).execute()
                                st.success(f"✨ '{n_prod}' registrado.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    with col_der:
        with st.expander("🗑️ ELIMINAR PRODUCTO"):
            if not df_inv.empty:
                prod_a_borrar = st.selectbox("Seleccione para eliminar", ["---"] + df_inv['nombre'].tolist(), key="select_del")
                pass_admin = st.text_input("Clave de Seguridad", type="password", key="del_pass")
                if st.button("❌ ELIMINAR DEFINITIVAMENTE"):
                    if pass_admin == CLAVE_ADMIN and prod_a_borrar != "---":
                        db.table("inventario").delete().eq("nombre", prod_a_borrar).execute()
                        st.success(f"Producto {prod_a_borrar} eliminado")
                        time.sleep(1)
                        st.rerun()

# --- 4. MÓDULO VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    res_caja = db.table("gastos").select("*").ilike("descripcion", "APERTURA_%").order("fecha", desc=True).limit(1).execute()
    
    if not res_caja.data:
        st.warning("⚠️ No hay turnos registrados. Debe realizar una apertura primero.")
        st.stop()
    
    ultimo_turno = res_caja.data[0]
    if ultimo_turno['estado'] == 'cerrado':
        st.error(f"🚫 TURNO CERRADO ({ultimo_turno['descripcion']}). Abra un nuevo turno para vender.")
        st.stop()

    st.header("🛒 Ventas Mediterraneo Express")
    st.caption(f"Turno Activo: {ultimo_turno['descripcion']}")
    
    # // INICIO NUEVA FUNCIÓN: Precios y Tasa Persistente
    with st.sidebar:
        st.divider()
        # La tasa se mantiene durante la sesión
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, st.session_state.get('tasa_dia', 60.0))
        st.session_state.tasa_dia = tasa
    # // FIN NUEVA FUNCIÓN

    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # // INICIO NUEVA FUNCIÓN: Buscador inteligente en tiempo real
        busc = st.text_input("🔍 Buscar producto por nombre o categoría...", placeholder="Escriba aquí...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        # // FIN NUEVA FUNCIÓN
        
        if not df_f.empty:
            c1, c2, c3 = st.columns([2, 1, 1])
            item_sel = c1.selectbox("Seleccione Producto", df_f['nombre'])
            p_match = df_p[df_p['nombre'] == item_sel]
            
            if not p_match.empty:
                p_data = p_match.iloc[0]
                c2.write(f"**Stock:** {p_data['stock']}")
                c2.write(f"**Precio:** ${p_data['precio_detal']}")
                
                cant_max = int(p_data['stock']) if p_data['stock'] > 0 else 1
                cant_sel = c3.number_input("Cantidad a añadir", 1, max_value=cant_max, key="add_cant")
                
                # // INICIO NUEVA FUNCIÓN: Lógica Carrito (Añadir/Modificar)
                if st.button("➕ AÑADIR AL CARRITO", use_container_width=True):
                    existe = False
                    for item in st.session_state.car:
                        if item['p'] == item_sel:
                            item['c'] += cant_sel
                            precio_u = float(p_data['precio_mayor']) if item['c'] >= p_data['min_mayor'] else float(p_data['precio_detal'])
                            item['u'] = precio_u
                            item['t'] = round(precio_u * item['c'], 2)
                            existe = True
                            break
                    
                    if not existe:
                        precio_u = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                        st.session_state.car.append({
                            "p": item_sel, "c": cant_sel, "u": precio_u, 
                            "t": round(precio_u * cant_sel, 2), 
                            "costo_u": float(p_data['costo']),
                            "min_m": p_data['min_mayor'],
                            "p_detal": p_data['precio_detal'],
                            "p_mayor": p_data['precio_mayor']
                        })
                    st.rerun()
                # // FIN NUEVA FUNCIÓN

    if st.session_state.car:
        st.subheader("📋 Resumen del Pedido")
        indices_a_borrar = []
        
        # // INICIO NUEVA FUNCIÓN: Carrito (Modificar Cantidades y Eliminar)
        for i, item in enumerate(st.session_state.car):
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                col1.write(f"**{item['p']}**")
                nueva_cant = col2.number_input("Cant.", 1, 9999, value=item['c'], key=f"edit_{i}")
                
                if nueva_cant != item['c']:
                    item['c'] = nueva_cant
                    precio_u = float(item['p_mayor']) if nueva_cant >= item['min_m'] else float(item['p_detal'])
                    item['u'] = precio_u
                    item['t'] = round(precio_u * nueva_cant, 2)
                    st.rerun()
                
                col3.write(f"Unit: ${item['u']}")
                col4.write(f"Subt: **${item['t']}**")
                if col5.button("🗑️", key=f"del_{i}"):
                    indices_a_borrar.append(i)

        if indices_a_borrar:
            for index in sorted(indices_a_borrar, reverse=True):
                st.session_state.car.pop(index)
            st.rerun()
        # // FIN NUEVA FUNCIÓN

        sub_total_usd = sum(float(x['t']) for x in st.session_state.car)
        total_bs_sugerido = sub_total_usd * tasa
        st.divider()
        st.write(f"### Total Sugerido: **{total_bs_sugerido:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        # // INICIO NUEVA FUNCIÓN: Pagos Multimoneda y Vuelto Automático
        total_a_cobrar_bs = st.number_input("MONTO FINAL A COBRAR (Bs)", value=float(total_bs_sugerido))
        
        st.info("💳 Registre los métodos de pago:")
        col_p1, col_p2, col_p3 = st.columns(3)
        ef = col_p1.number_input("Efectivo Bs", 0.0); pm = col_p1.number_input("Pago Móvil Bs", 0.0)
        pu = col_p2.number_input("Punto Bs", 0.0); ot = col_p2.number_input("Otros Bs", 0.0)
        ze = col_p3.number_input("Zelle $", 0.0); di = col_p3.number_input("Divisas $", 0.0)
        
        total_pagado_bs = ef + pm + pu + ot + (ze * tasa) + (di * tasa)
        vuelto_bs = total_pagado_bs - total_a_cobrar_bs
        
        if vuelto_bs > 0:
            st.success(f"💰 Vuelto al cliente: **{vuelto_bs:,.2f} Bs.** (${vuelto_bs/tasa:,.2f})")
        elif vuelto_bs < 0:
            st.warning(f"⚠️ Faltan: {abs(vuelto_bs):,.2f} Bs.")
        # // FIN NUEVA FUNCIÓN

        # // INICIO NUEVA FUNCIÓN: Finalización y Ticket PDF
        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            if total_pagado_bs < total_a_cobrar_bs:
                st.error("❌ El monto pagado es insuficiente.")
            else:
                try:
                    propina_usd = (total_a_cobrar_bs / tasa) - sub_total_usd
                    ahora = datetime.now()
                    id_tx = f"TX-{ahora.strftime('%Y%m%d%H%M%S')}"
                    
                    st.info(f"🧾 **GENERANDO TICKET: {id_tx}**")
                    for x in st.session_state.car:
                        db.table("ventas").insert({
                            "id_transaccion": id_tx, "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                            "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, 
                            "pago_otros": ot, "pago_divisas": di, "costo_venta": x['costo_u'] * x['c'],
                            "propina": propina_usd / len(st.session_state.car), "fecha": ahora.isoformat()
                        }).execute()
                        
                        p_inv_res = db.table("inventario").select("stock").eq("nombre", x['p']).execute()
                        if p_inv_res.data:
                            nuevo_stk = int(p_inv_res.data[0]['stock'] - x['c'])
                            db.table("inventario").update({"stock": nuevo_stk}).eq("nombre", x['p']).execute()
                    
                    st.balloons()
                    st.success(f"✅ VENTA FINALIZADA: {id_tx}")
                    
                    # Lógica simplificada de Ticket PDF (Simulada en texto para visualización rápida)
                    with st.expander("📄 Ver Ticket Digital"):
                        ticket_data = f"""
                        MEDITERRANEO EXPRESS
                        Ticket: {id_tx}
                        Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}
                        --------------------------------
                        Total: {total_a_cobrar_bs:,.2f} Bs
                        Ref: ${total_a_cobrar_bs/tasa:,.2f}
                        Vuelto: {vuelto_bs:,.2f} Bs
                        --------------------------------
                        ¡Gracias por su compra!
                        """
                        st.code(ticket_data)
                        st.download_button("📥 Descargar Ticket (.txt)", ticket_data, file_name=f"ticket_{id_tx}.txt")

                    time.sleep(4)
                    st.session_state.car = [] 
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        # // FIN NUEVA FUNCIÓN

# // INICIO NUEVA FUNCIÓN: Historial Administrativo con UX Avanzada
    st.divider()
    st.header("📊 Centro de Gestión de Ventas")

    # Contenedor de Filtros
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 2])
        fecha_filtro = f_col1.date_input("📅 Fecha", date.today())
        # Buscador que ahora es para Ticket, Cliente o Producto
        busc_general = f_col2.text_input("🔍 Buscar por Ticket, Cliente o Producto...", placeholder="Ej: Luis, Café, TX-123...", key="filtro_global_admin")

    # Carga de datos
    res_h = db.table("ventas").select("*").gte("fecha", fecha_filtro.isoformat()).order("fecha", desc=True).execute()

    if res_h.data:
        df_raw = pd.DataFrame(res_h.data)
        
        # 1. Normalización y Limpieza
        df_raw['id_transaccion'] = df_raw['id_transaccion'].fillna(df_raw['id'].astype(str))
        df_raw['cliente'] = df_raw.get('cliente', 'Cliente General').fillna('Cliente General')
        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha']).dt.date
        df_raw = df_raw[df_raw['fecha_dt'] == fecha_filtro]

        if not df_raw.empty:
            # 2. Lógica de Identificación UX (Agrupación para Resumen)
            # Agrupamos para saber qué productos tiene cada ticket
            resumen_productos = df_raw.groupby('id_transaccion')['producto'].apply(list).reset_index()
            
            def generar_etiqueta(row):
                prods = row['producto']
                primero = prods[0]
                extras = len(prods) - 1
                return f"{primero} (+{extras} más)" if extras > 0 else primero

            resumen_productos['identificador_prod'] = resumen_productos.apply(generar_etiqueta, axis=1)

            # 3. Agrupación Maestra para la Tabla
            v_maestra = df_raw.groupby('id_transaccion').agg({
                'fecha': 'first',
                'cliente': 'first',
                'total_usd': 'sum',
                'tasa_cambio': 'first',
                'pago_efectivo': 'sum', # Sumamos por si hay registros parciales
                'pago_divisas': 'sum'
            }).reset_index()

            # Unimos el resumen de productos a la maestra
            v_maestra = v_maestra.merge(resumen_productos[['id_transaccion', 'identificador_prod']], on='id_transaccion')
            
            # Columna combinada para el Buscador y Visualización
            v_maestra['Info Venta'] = v_maestra['cliente'] + " - " + v_maestra['identificador_prod']
            v_maestra['total_bs'] = v_maestra['total_usd'] * v_maestra['tasa_cambio']

            # 4. Filtro Multicriterio (UX)
            if busc_general:
                mask = (
                    v_maestra['id_transaccion'].str.contains(busc_general, case=False) |
                    v_maestra['Info Venta'].str.contains(busc_general, case=False)
                )
                v_maestra = v_maestra[mask]

            # --- VISTA TABLA ---
            st.subheader("📋 Relación de Ingresos")
            df_display = v_maestra.copy()
            df_display['Hora'] = pd.to_datetime(df_display['fecha']).dt.strftime('%H:%M')
            
            st.dataframe(
                df_display[['id_transaccion', 'Hora', 'Info Venta', 'total_usd', 'total_bs']], 
                column_config={
                    "id_transaccion": "Ticket",
                    "Hora": "Hora",
                    "Info Venta": "Identificación (Cliente - Producto)",
                    "total_usd": st.column_config.NumberColumn("Total $", format="$ %.2f"),
                    "total_bs": st.column_config.NumberColumn("Total Bs", format="Bs %.2f"),
                },
                use_container_width=True, hide_index=True
            )

            # --- GESTIÓN Y DETALLE ---
            st.subheader("🔍 Detalle de Transacción")
            sel_ticket = st.selectbox("Operar Ticket:", ["-- Seleccione --"] + v_maestra['id_transaccion'].tolist())

            if sel_ticket != "-- Seleccione --":
                detalle_items = df_raw[df_raw['id_transaccion'] == sel_ticket]
                malla = v_maestra[v_maestra['id_transaccion'] == sel_ticket].iloc[0]

                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Cliente:** {malla['cliente']}")
                    c1.write(f"**Ticket:** {sel_ticket}")
                    
                    st.write("**Desglose de productos:**")
                    for _, item in detalle_items.iterrows():
                        st.caption(f"• {item['producto']} x{item['cantidad']} — ${item['total_usd']:.2f}")

                    st.divider()
                    # Botón de Anulación con Confirmación
                    if st.button(f"🚨 ANULAR VENTA {sel_ticket}", type="primary", use_container_width=True):
                        st.session_state[f"confirm_del_{sel_ticket}"] = True
                    
                    if st.session_state.get(f"confirm_del_{sel_ticket}"):
                        st.error("¿CONFIRMA LA ANULACIÓN? Esta acción devolverá el stock y eliminará el registro.")
                        col_an1, col_an2 = st.columns(2)
                        if col_an1.button("SÍ, ANULAR", key=f"yes_{sel_ticket}", use_container_width=True):
                            try:
                                for _, row in detalle_items.iterrows():
                                    # Devolver Stock
                                    r_inv = db.table("inventario").select("stock").eq("nombre", row['producto']).execute()
                                    if r_inv.data:
                                        db.table("inventario").update({"stock": r_inv.data[0]['stock'] + row['cantidad']}).eq("nombre", row['producto']).execute()
                                # Borrar Venta
                                db.table("ventas").delete().eq("id_transaccion", sel_ticket).execute()
                                st.success("Venta anulada con éxito.")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        if col_an2.button("NO, CANCELAR", key=f"no_{sel_ticket}", use_container_width=True):
                            st.session_state[f"confirm_del_{sel_ticket}"] = False
                            st.rerun()

            # --- EXPORTACIÓN ---
            st.divider()
            col_exp1, col_exp2 = st.columns(2)
            csv = v_maestra.to_csv(index=False).encode('utf-8')
            col_exp1.download_button("📥 Exportar Excel (CSV)", csv, f"reporte_{fecha_filtro}.csv", "text/csv", use_container_width=True)
            col_exp2.button("📄 Generar PDF (Disponible en Pro)", use_container_width=True, disabled=True)

        else:
            st.info("No hay ventas para los criterios seleccionados.")
    else:
        st.info(f"No hay registros para la fecha: {fecha_filtro}")
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






