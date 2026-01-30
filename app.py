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
    
    with st.sidebar:
        st.divider()
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)

    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busc = st.text_input("🔍 Buscar producto...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
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

        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            try:
                propina_usd = (total_a_cobrar_bs / tasa) - sub_total_usd
                ahora = datetime.now()
                id_tx = f"TX-{ahora.strftime('%Y%m%d%H%M%S')}"
                
                # --- GENERACIÓN DE TICKET EN PANTALLA ---
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
                
                # Mensaje detallado de éxito
                st.balloons()
                st.success(f"""
                ✅ **VENTA FINALIZADA CON ÉXITO**
                - **Ticket ID:** {id_tx}
                - **Total Cobrado:** {total_a_cobrar_bs:,.2f} Bs.
                - **Total USD:** ${total_a_cobrar_bs/tasa:,.2f}
                """)
                
                # Pausa para ver el ticket antes de resetear
                time.sleep(3)
                st.session_state.car = [] 
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # Historial
    st.divider()
    st.subheader("🕒 Historial de Ventas del Día")
    res_h = db.table("ventas").select("*").gte("fecha", date.today().isoformat()).order("fecha", desc=True).execute()
    if res_h.data:
        df_historial = pd.DataFrame(res_h.data)
        df_historial['grupo'] = df_historial['id_transaccion'].fillna(df_historial['id'].astype(str))
        v_agrupadas = df_historial.groupby('grupo').agg({'fecha': 'first', 'total_usd': 'sum', 'producto': lambda x: ", ".join(x.astype(str))}).reset_index()
        for _, fila in v_agrupadas.iterrows():
            with st.expander(f"💰 Venta - Total: ${fila['total_usd']:.2f}"):
                st.write(f"Productos: {fila['producto']}")
    else:
        st.info("No hay ventas hoy.")

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

