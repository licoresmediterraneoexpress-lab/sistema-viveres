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

elif opcion == "🛒 Venta Rápida":
    # 1. Validación de Apertura de Caja
    try:
        res_caja = db.table("gastos").select("*").ilike("descripcion", "APERTURA_%").order("fecha", desc=True).limit(1).execute()
        if not res_caja.data or res_caja.data[0]['estado'] == 'cerrado':
            st.error("🚫 TURNO CERRADO O INEXISTENTE. Debe realizar una apertura en el módulo de Gastos/Caja.")
            st.stop()
        ultimo_turno = res_caja.data[0]
    except Exception as e:
        st.error(f"Error al verificar turno: {e}")
        st.stop()

    # 2. Configuración de Tasa Persistente
    if 'tasa_dia' not in st.session_state:
        st.session_state.tasa_dia = 60.0  # Valor por defecto inicial
    if 'car' not in st.session_state:
        st.session_state.car = []

    st.header("🛒 Ventas Mediterraneo Express")
    
    # Sidebar para Tasa y Estado de Caja
    with st.sidebar:
        st.subheader("⚙️ Configuración de Venta")
        st.session_state.tasa_dia = st.number_input("Tasa BCV del Día (Bs/$)", min_value=1.0, value=st.session_state.tasa_dia, format="%.2f")
        st.info(f"📍 Turno: {ultimo_turno['descripcion']}")
        if st.button("🧹 Vaciar Carrito Completo"):
            st.session_state.car = []
            st.rerun()

    tasa = st.session_state.tasa_dia

    # 3. Buscador Inteligente de Productos
    st.subheader("🔍 Selección de Productos")
    busc = st.text_input("Escriba nombre del producto...", placeholder="Ej: Harina, Refresco...", key="main_search").strip().lower()

    if busc:
        res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc}%").execute()
        if res_p.data:
            df_f = pd.DataFrame(res_p.data)
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                item_sel = col1.selectbox(f"Coincidencias ({len(df_f)})", df_f['nombre'].tolist())
                p_data = df_f[df_f['nombre'] == item_sel].iloc[0]
                
                stock_actual = p_data['stock']
                col2.metric("Stock", f"{stock_actual:.0f}")
                col2.write(f"**Precio:** ${p_data['precio_detal']:.2f}")
                
                cant_sel = col3.number_input("Cantidad", min_value=1, max_value=int(stock_actual) if stock_actual > 0 else 1, value=1)
                
                if stock_actual <= 0:
                    st.error("Producto sin existencia.")
                elif st.button("➕ Añadir al Carrito", use_container_width=True, type="primary"):
                    # Lógica de precios (Detal vs Mayor)
                    precio_u = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                    
                    # Verificar si ya está en carrito
                    existe = next((item for item in st.session_state.car if item['p'] == item_sel), None)
                    if existe:
                        existe['c'] += cant_sel
                        # Recalcular precio por si ahora aplica precio al mayor
                        precio_u = float(p_data['precio_mayor']) if existe['c'] >= p_data['min_mayor'] else float(p_data['precio_detal'])
                        existe['u'] = precio_u
                        existe['t'] = round(precio_u * existe['c'], 2)
                    else:
                        st.session_state.car.append({
                            "p": item_sel, "c": cant_sel, "u": precio_u, 
                            "t": round(precio_u * cant_sel, 2),
                            "costo_u": float(p_data['costo']),
                            "min_m": p_data['min_mayor'],
                            "p_detal": p_data['precio_detal'],
                            "p_mayor": p_data['precio_mayor']
                        })
                    st.toast(f"✅ {item_sel} añadido")
                    st.rerun()
        else:
            st.info("No se encontraron productos.")
    else:
        st.caption("Use el buscador arriba para ver productos disponibles.")

    # 4. Gestión de Carrito y Resumen
    if st.session_state.car:
        st.divider()
        st.subheader("📋 Resumen del Pedido")
        
        for i, item in enumerate(st.session_state.car):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
                c1.write(f"**{item['p']}**")
                n_c = c2.number_input("Cant", 1, 500, value=item['c'], key=f"q_{i}")
                if n_c != item['c']:
                    item['c'] = n_c
                    item['u'] = float(item['p_mayor']) if n_c >= item['min_m'] else float(item['p_detal'])
                    item['t'] = round(item['u'] * n_c, 2)
                    st.rerun()
                
                c3.write(f"Unit: ${item['u']:.2f}")
                c4.write(f"Subt: **${item['t']:.2f}**")
                if c5.button("🗑️", key=f"del_{i}"):
                    st.session_state.car.pop(i)
                    st.rerun()

        # 5. Cálculos Multimoneda y Pagos
        sub_total_usd = sum(item['t'] for item in st.session_state.car)
        total_sugerido_bs = sub_total_usd * tasa
        
        st.success(f"### TOTAL A PAGAR: ${sub_total_usd:,.2f} / {total_sugerido_bs:,.2f} Bs.")
        
        with st.expander("💳 Registrar Pago Mixto / Multimoneda", expanded=True):
            col_p1, col_p2, col_p3 = st.columns(3)
            ef_bs = col_p1.number_input("Efectivo Bs", min_value=0.0, format="%.2f")
            pm_bs = col_p1.number_input("Pago Móvil Bs", min_value=0.0, format="%.2f")
            pu_bs = col_p2.number_input("Punto de Venta Bs", min_value=0.0, format="%.2f")
            di_usd = col_p2.number_input("Divisas $ (Efectivo)", min_value=0.0, format="%.2f")
            ze_usd = col_p3.number_input("Zelle / Otros $", min_value=0.0, format="%.2f")
            
            total_pagado_bs = ef_bs + pm_bs + pu_bs + (di_usd * tasa) + (ze_usd * tasa)
            vuelto_bs = total_pagado_bs - total_sugerido_bs
            
            if total_pagado_bs > 0:
                if vuelto_bs >= 0:
                    st.metric("Vuelto al Cliente (Bs)", f"{vuelto_bs:,.2f} Bs", delta_color="normal")
                    st.caption(f"Equivalente a: ${(vuelto_bs/tasa):,.2f}")
                else:
                    st.warning(f"Faltan: {abs(vuelto_bs):,.2f} Bs")

        # 6. Finalización y Generación de Ticket
        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            if total_pagado_bs < (total_sugerido_bs - 0.01): # Margen de error decimal
                st.error("Error: Monto pagado insuficiente.")
            else:
                try:
                    ahora = datetime.now()
                    id_tx = f"TX-{ahora.strftime('%y%m%d%H%M%S')}"
                    
                    with st.status("Procesando transacción...", expanded=True) as status:
                        for x in st.session_state.car:
                            # Registro en Ventas
                            db.table("ventas").insert({
                                "id_transaccion": id_tx,
                                "producto": x['p'],
                                "cantidad": x['c'],
                                "total_usd": x['t'],
                                "tasa_cambio": tasa,
                                "pago_efectivo": ef_bs,
                                "pago_punto": pu_bs,
                                "pago_movil": pm_bs,
                                "pago_zelle": ze_usd,
                                "pago_divisas": di_usd,
                                "costo_venta": x['costo_u'] * x['c'],
                                "fecha": ahora.isoformat()
                            }).execute()
                            
                            # Descontar Stock
                            inv_data = db.table("inventario").select("stock").eq("nombre", x['p']).execute()
                            if inv_data.data:
                                n_stk = inv_data.data[0]['stock'] - x['c']
                                db.table("inventario").update({"stock": n_stk}).eq("nombre", x['p']).execute()
                        
                        status.update(label="✅ Venta Exitosa", state="complete")
                    
                    st.balloons()
                    
                    # Generación de Ticket POS
                    ticket_txt = f"""
{'='*30}
MEDITERRANEO EXPRESS
RIF: J-123456789
Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}
Ticket: {id_tx}
{'='*30}
PRODUCTOS:
"""
                    for x in st.session_state.car:
                        ticket_txt += f"{x['p'][:18]:<18} x{x['c']} ${x['t']}\n"
                    
                    ticket_txt += f"""{'-'*30}
TOTAL USD:    ${sub_total_usd:>10.2f}
TOTAL BS:     {total_sugerido_bs:>10.2f}
TASA:         {tasa:>10.2f}
{'-'*30}
PAGADO BS:    {total_pagado_bs:>10.2f}
VUELTO BS:    {max(0, vuelto_bs):>10.2f}
{'='*30}
¡Gracias por su compra!
"""
                    st.code(ticket_txt)
                    st.download_button("📥 Descargar Ticket", ticket_txt, file_name=f"Ticket_{id_tx}.txt", use_container_width=True)
                    
                    # Reset
                    time.sleep(2)
                    st.session_state.car = []
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










