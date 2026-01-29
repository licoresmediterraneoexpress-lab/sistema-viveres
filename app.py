import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time
import streamlit as st
import pandas as pd
from datetime import date, datetime
import time
# ... tus otras importaciones como supabase ...

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
                        st.rerun()

# --- 4. MÓDULO VENTA RÁPIDA (CON HISTORIAL Y ANULACIÓN) ---
elif opcion == "🛒 Venta Rápida":
    from datetime import date, datetime
    import pandas as pd

    # 1. VERIFICACIÓN DE TURNO (CANDADO DINÁMICO)
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
    
    with st.sidebar:
        st.divider()
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)

    # 2. CONSULTA Y SELECCIÓN DE PRODUCTOS
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busc = st.text_input("🔍 Buscar producto...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        if not df_f.empty:
            c1, c2, c3 = st.columns([2, 1, 1])
            item_sel = c1.selectbox("Seleccione Producto", df_f['nombre'])
            
            # --- PROTECCIÓN ANTI-INDEXERROR ---
            p_match = df_p[df_p['nombre'] == item_sel]
            if not p_match.empty:
                p_data = p_match.iloc[0]
                c2.write(f"**Stock:** {p_data['stock']}")
                c2.write(f"**Precio:** ${p_data['precio_detal']}")
                
                cant_max = int(p_data['stock']) if p_data['stock'] > 0 else 1
                cant_sel = c3.number_input("Cantidad a añadir", 1, max_value=cant_max, key="add_cant")
                
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
            else:
                st.warning("Seleccione un producto válido.")
        else:
            st.error("❌ No hay coincidencias.")

    # 3. GESTIÓN DINÁMICA DEL CARRITO
    if st.session_state.car:
        st.subheader("📋 Resumen del Pedido")
        indices_a_borrar = []
        
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

        # 4. TOTALES Y PAGOS
        sub_total_usd = sum(float(x['t']) for x in st.session_state.car)
        total_bs_sugerido = sub_total_usd * tasa
        
        st.divider()
        st.write(f"### Total Sugerido: **{total_bs_sugerido:,.2f} Bs.** (${sub_total_usd:,.2f})")
        total_a_cobrar_bs = st.number_input("MONTO FINAL A COBRAR (Bs)", value=float(total_bs_sugerido))
        
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

        # 5. FINALIZAR VENTA
        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            try:
                propina_usd = (total_a_cobrar_bs / tasa) - sub_total_usd
                ahora_iso = datetime.now().isoformat()
                ahora_print = datetime.now().strftime("%d/%m/%Y %H:%M")
                items_factura = st.session_state.car.copy()
                
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, 
                        "pago_otros": ot, "pago_divisas": di, "costo_venta": x['costo_u'] * x['c'],
                        "propina": propina_usd / len(st.session_state.car), "fecha": ahora_iso
                    }).execute()
                    
                    p_inv_res = db.table("inventario").select("stock").eq("nombre", x['p']).execute()
                    if p_inv_res.data:
                        nuevo_stk = int(p_inv_res.data[0]['stock'] - x['c'])
                        db.table("inventario").update({"stock": nuevo_stk}).eq("nombre", x['p']).execute()
                
                st.success("🎉 VENTA REGISTRADA")
                
                ticket_html = f"""
                <div style="background-color: #fff; padding: 20px; color: #000; font-family: monospace; border: 2px solid #000; width: 280px; margin: auto;">
                    <center><h3 style="margin:0;">MEDITERRANEO EXPRESS</h3><p style="font-size:10px;">{ahora_print}</p><hr></center>
                    <table style="width: 100%; font-size: 11px;">
                        {"".join([f"<tr><td>{i['c']}x {i['p'][:15]}</td><td style='text-align:right;'>${i['t']:.2f}</td></tr>" for i in items_factura])}
                    </table>
                    <hr>
                    <table style="width: 100%;">
                        <tr><td><b>TOTAL USD:</b></td><td style="text-align:right;"><b>${sub_total_usd:.2f}</b></td></tr>
                        <tr><td><b>TOTAL BS:</b></td><td style="text-align:right;"><b>{total_a_cobrar_bs:,.2f}</b></td></tr>
                    </table>
                    <center><br><p style="font-size:10px;">Vuelto: {vuelto_bs:,.2f} Bs</p><p style="font-size:10px;">*** Gracias por su compra ***</p></center>
                </div>
                """
                st.markdown(ticket_html, unsafe_allow_html=True)
                st.session_state.car = [] 
                
                if st.button("🔄 HACER NUEVA VENTA"):
                    st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # --- 6. HISTORIAL CON BOTÓN DE ANULACIÓN ---
    st.divider()
    with st.expander("🕒 Últimas 5 Ventas (Historial y Anulaciones)"):
        res_h = db.table("ventas").select("id, fecha, producto, cantidad, total_usd").order("fecha", desc=True).limit(5).execute()
        if res_h.data:
            for v in res_h.data:
                h_col1, h_col2, h_col3, h_col4 = st.columns([1, 3, 1, 1])
                h_hora = datetime.fromisoformat(v['fecha']).strftime('%H:%M')
                h_col1.write(f"**{h_hora}**")
                h_col2.write(f"{v['cantidad']}x {v['producto']}")
                h_col3.write(f"${v['total_usd']}")
                
                # Botón para anular venta individual
                if h_col4.button("❌", key=f"rev_{v['id']}", help="Anular esta venta y devolver stock"):
                    try:
                        # 1. Recuperar stock actual
                        p_inv = db.table("inventario").select("stock").eq("nombre", v['producto']).execute()
                        if p_inv.data:
                            stock_actual = p_inv.data[0]['stock']
                            # 2. Devolver cantidad al inventario
                            db.table("inventario").update({"stock": stock_actual + v['cantidad']}).eq("nombre", v['producto']).execute()
                            # 3. Borrar la venta
                            db.table("ventas").delete().eq("id", v['id']).execute()
                            st.toast(f"Anulada: {v['producto']} (+{v['cantidad']} al stock)")
                            st.rerun()
                    except Exception as ex:
                        st.error(f"No se pudo anular: {ex}")
        else:
            st.info("No hay ventas recientes.")

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 6. MÓDULO DE CAJA: TURNOS MÚLTIPLES (SIN ERRORES DE SINTAXIS) ---
elif opcion == "📊 Cierre de Caja":
    import time
    from datetime import date, datetime
    import pandas as pd

    st.header("📊 Gestión de Turnos y Arqueo")
    
    # 1. BUSCAR EL ÚLTIMO REGISTRO DE CAJA (Ordenado por fecha descendente)
    try:
        res_ultimo = db.table("gastos").select("*").ilike("descripcion", "APERTURA_%").order("fecha", desc=True).limit(1).execute()
        ultimo_registro = res_ultimo.data[0] if res_ultimo.data else None
    except Exception as e:
        ultimo_registro = None
        st.error(f"Error al conectar con la base de datos: {e}")
    
    # Determinamos si hay un turno abierto (Variable corregida sin espacios)
    caja_abierta_actual = ultimo_registro is not None and ultimo_registro.get('estado') == 'abierto'

    # --- BLOQUE A: APERTURA DE NUEVO TURNO ---
    if not caja_abierta_actual:
        st.info("🔓 No hay turnos activos. Inicie un nuevo turno para poder registrar ventas.")
        with st.form("form_apertura_turno"):
            st.subheader("🔑 Apertura de Turno")
            col1, col2, col3 = st.columns(3)
            tasa_ap = col1.number_input("Tasa del Día", min_value=1.0, value=60.0)
            f_bs = col2.number_input("Fondo Inicial Bs", min_value=0.0)
            f_usd = col3.number_input("Fondo Inicial $", min_value=0.0)
            
            # Generamos un ID único usando Fecha y Hora
            id_turno = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if st.form_submit_button("✅ ABRIR NUEVO TURNO", use_container_width=True):
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{id_turno}",
                    "monto_usd": f_usd + (f_bs / tasa_ap),
                    "monto_bs_extra": f_bs,
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success(f"🚀 Turno {id_turno} abierto con éxito.")
                time.sleep(1)
                st.rerun()

    # --- BLOQUE B: CIERRE DE TURNO ACTIVO ---
    else:
        id_turno_actual = ultimo_registro['descripcion']
        fecha_inicio_turno = ultimo_registro['fecha']
        f_bs_ini = float(ultimo_registro.get('monto_bs_extra', 0.0))
        # Calculamos fondo USD restando el equivalente en Bs
        f_usd_ini = float(ultimo_registro.get('monto_usd', 0.0)) - (f_bs_ini / 60)

        st.warning(f"🔔 Turno Activo: **{id_turno_actual}**")
        st.caption(f"Abierto desde: {fecha_inicio_turno}")

        # 2. CONSULTAR VENTAS SOLO DESDE QUE SE ABRIÓ ESTE TURNO
        v_res = db.table("ventas").select("*").gte("fecha", fecha_inicio_turno).execute()
        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()

        if not df_v.empty:
            s_ef_bs = df_v['pago_efectivo'].sum()
            s_di_usd = df_v['pago_divisas'].sum()
            s_pm_bs = df_v['pago_movil'].sum()
            s_pu_bs = df_v['pago_punto'].sum()
            total_ingreso = df_v['total_usd'].sum()
        else:
            s_ef_bs = s_di_usd = s_pm_bs = s_pu_bs = total_ingreso = 0.0

        # Métricas del Sistema
        st.subheader("💳 Ventas del Turno (Sistema)")
        c_sys = st.columns(4)
        c_sys[0].metric("Efectivo Bs", f"{s_ef_bs:,.2f}")
        c_sys[1].metric("Efectivo $", f"{s_di_usd:,.2f}")
        c_sys[2].metric("Pago Móvil", f"{s_pm_bs:,.2f}")
        c_sys[3].metric("Punto", f"{s_pu_bs:,.2f}")

        # Arqueo Físico
        st.divider()
        st.subheader("📝 Ingresar Dinero Real en Caja")
        with st.container(border=True):
            col_r1, col_r2 = st.columns(2)
            r_ef_bs = col_r1.number_input("Total Efectivo Bs Real", 0.0)
            r_ef_usd = col_r1.number_input("Total Efectivo $ Real", 0.0)
            r_pm_bs = col_r2.number_input("Total Pago Móvil Real", 0.0)
            r_pu_bs = col_r2.number_input("Total Punto Real", 0.0)

        if st.button("🏮 CERRAR TURNO Y BLOQUEAR VENTAS", use_container_width=True, type="primary"):
            try:
                # 1. CERRAR EL TURNO
                db.table("gastos").update({"estado": "cerrado"}).eq("descripcion", id_turno_actual).execute()
                
                # 2. CÁLCULOS DE CUADRE
                esp_bs = s_ef_bs + f_bs_ini
                esp_usd = s_di_usd + f_usd_ini
                dif_bs = r_ef_bs - esp_bs
                dif_usd = r_ef_usd - esp_usd

                st.balloons()
                st.success("✅ Turno cerrado exitosamente.")

                reporte_html = f"""
                <div style="background: white; color: black; padding: 20px; border: 3px solid black; font-family: monospace;">
                    <center><h2>REPORTE DE CIERRE</h2></center>
                    <hr>
                    <b>TURNO:</b> {id_turno_actual}<br>
                    <b>VENTAS TOTALES:</b> ${total_ingreso:,.2f}<br>
                    <hr>
                    <b>DIFERENCIA BS:</b> {dif_bs:,.2f}<br>
                    <b>DIFERENCIA $:</b> {dif_usd:,.2f}<br>
                    <hr>
                    <center>Ventas pausadas hasta nueva apertura</center>
                </div>
                """
                st.markdown(reporte_html, unsafe_allow_html=True)
                time.sleep(5)
                st.rerun()
            except Exception as e:
                st.error(f"Error al cerrar turno: {e}")






