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
                        st.rerun()

# --- 4. MÓDULO VENTA RÁPIDA (CORREGIDO: AHORA EN SU PROPIA SECCIÓN) ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Ventas Mediterraneo Express")
    
    with st.sidebar:
        st.divider()
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)

    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        busc = st.text_input("🔍 Buscar producto...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        c1, c2, c3 = st.columns([2, 1, 1])
        item_sel = c1.selectbox("Producto", df_f['nombre'])
        p_data = df_p[df_p['nombre'] == item_sel].iloc[0]
        c2.write(f"**Stock:** {p_data['stock']}")
        c2.write(f"**Precio:** ${p_data['precio_detal']}")
        cant_sel = c3.number_input("Cantidad", 1, max_value=int(p_data['stock']) if p_data['stock'] > 0 else 1)
        
        if st.button("➕ AÑADIR AL CARRITO"):
            if p_data['stock'] >= cant_sel:
                precio = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                st.session_state.car.append({
                    "p": item_sel, "c": cant_sel, "u": precio, 
                    "t": round(float(precio) * int(cant_sel), 2), 
                    "costo_u": float(p_data['costo'])
                })
                st.rerun()

    if st.session_state.car:
        st.divider()
        df_car = pd.DataFrame(st.session_state.car)
        st.table(df_car[['p', 'c', 'u', 't']].rename(columns={'p':'Producto','c':'Cant','u':'Precio $','t':'Total $'}))
        
        sub_total_usd = sum(float(x['t']) for x in st.session_state.car)
        total_bs_sugerido = sub_total_usd * tasa
        st.write(f"### Total Sugerido: **{total_bs_sugerido:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        total_a_cobrar_bs = st.number_input("MONTO FINAL A COBRAR", value=float(total_bs_sugerido))
        
        col_p1, col_p2, col_p3 = st.columns(3)
        ef = col_p1.number_input("Efectivo Bs", 0.0); pm = col_p1.number_input("Pago Móvil Bs", 0.0)
        pu = col_p2.number_input("Punto Bs", 0.0); ot = col_p2.number_input("Otros Bs", 0.0)
        ze = col_p3.number_input("Zelle $", 0.0); di = col_p3.number_input("Divisas $", 0.0)
        
        if st.button("🚀 FINALIZAR VENTA"):
            try:
                propina_usd = (total_a_cobrar_bs / tasa) - sub_total_usd
                items_ticket = st.session_state.car.copy()
                ahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, 
                        "pago_otros": ot, "pago_divisas": di, "costo_venta": x['costo_u'] * x['c'],
                        "propina": propina_usd / len(st.session_state.car), "fecha": datetime.now().isoformat()
                    }).execute()
                    stk_actual = df_p[df_p['nombre'] == x['p']].iloc[0]['stock']
                    db.table("inventario").update({"stock": int(stk_actual - x['c'])}).eq("nombre", x['p']).execute()
                
                st.success("🎉 VENTA REGISTRADA")
                st.session_state.car = []
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 6. MÓDULO DE CAJA: CONTROL TOTAL Y CIERRE ---
elif opcion == "📊 Cierre de Caja":
    import time
    st.header("📊 Gestión de Caja y Arqueo Integral")
    hoy = date.today().isoformat()
    
    # 1. VERIFICACIÓN DE ESTADO DE CAJA (Apertura y si ya fue cerrada)
    res_caja = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{hoy}").execute()
    caja_datos = res_caja.data[0] if res_caja.data else None
    caja_abierta = caja_datos is not None
    esta_cerrada = caja_datos['estado'] == 'cerrado' if caja_abierta else False

    # --- BLOQUE A: APERTURA (Solo si no hay registro de hoy) ---
    if not caja_abierta:
        st.warning("⚠️ La caja se encuentra cerrada. Por favor, registre el fondo inicial para operar.")
        with st.form("form_apertura"):
            st.subheader("🔑 Abrir Turno")
            col1, col2, col3 = st.columns(3)
            tasa_ap = col1.number_input("Tasa del Día (Bs/$)", min_value=1.0, value=60.0)
            f_bs = col2.number_input("Fondo Inicial en Bolívares (Bs)", min_value=0.0)
            f_usd = col3.number_input("Fondo Inicial en Divisas ($)", min_value=0.0)
            
            if st.form_submit_button("✅ REGISTRAR APERTURA Y EMPEZAR", use_container_width=True):
                total_usd_ap = f_usd + (f_bs / tasa_ap)
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{hoy}",
                    "monto_usd": total_usd_ap,
                    "monto_bs_extra": f_bs,
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success("¡Caja abierta exitosamente!")
                time.sleep(1)
                st.rerun()

    # --- BLOQUE B: VISTA DE CIERRE (Si ya se cerró la caja hoy) ---
    elif esta_cerrada:
        st.success("✅ La jornada de hoy ha sido FINALIZADA y bloqueada.")
        st.info("A continuación se muestra el reporte de cierre generado. No se pueden realizar más cambios.")
        # Aquí podrías opcionalmente mostrar el reporte que se guardó o recalcularlo solo lectura
        if st.button("🔄 Volver a Menú Principal"):
            st.rerun()

    # --- BLOQUE C: PANEL DE ARQUEO ACTIVO (Caja abierta y lista para cerrar) ---
    else:
        # Recuperar Fondos Iniciales
        f_bs_ini = caja_datos['monto_bs_extra']
        f_usd_ini = caja_datos['monto_usd'] - (f_bs_ini / 60) 

        st.info(f"🟢 Caja Abierta hoy con: {f_bs_ini:,.2f} Bs | ${f_usd_ini:,.2f} USD")

        # Consultar Movimientos del Sistema
        v_res = db.table("ventas").select("*").gte("fecha", hoy).execute()
        g_res = db.table("gastos").select("*").gte("fecha", hoy).execute()
        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()
        df_g = pd.DataFrame(g_res.data) if g_res.data else pd.DataFrame()

        # Totales del Sistema
        if not df_v.empty:
            s_ef_bs = df_v['pago_efectivo'].sum(); s_di_usd = df_v['pago_divisas'].sum()
            s_pm_bs = df_v['pago_movil'].sum(); s_pu_bs = df_v['pago_punto'].sum()
            s_ze_usd = df_v['pago_zelle'].sum(); s_ot_bs = df_v['pago_otros'].sum()
            total_ingreso = df_v['total_usd'].sum()
        else:
            s_ef_bs = s_di_usd = s_pm_bs = s_pu_bs = s_ze_usd = s_ot_bs = total_ingreso = 0.0

        # Interfaz de Resumen del Sistema
        st.subheader("💳 Ventas Registradas (Sistema)")
        c_sys = st.columns(6)
        c_sys[0].metric("Efec. Bs", f"{s_ef_bs:,.2f}"); c_sys[1].metric("Efec. $", f"{s_di_usd:,.2f}")
        c_sys[2].metric("P. Móvil", f"{s_pm_bs:,.2f}"); c_sys[3].metric("Punto", f"{s_pu_bs:,.2f}")
        c_sys[4].metric("Zelle", f"{s_ze_usd:,.2f}"); c_sys[5].metric("Otros", f"{s_ot_bs:,.2f}")

        # Sección de Ingreso de Dinero Real
        st.divider()
        st.subheader("📝 Arqueo Físico y de Cuentas")
        with st.container(border=True):
            col_r1, col_r2, col_r3 = st.columns(3)
            r_ef_bs = col_r1.number_input("Efectivo Bs en Caja", 0.0)
            r_ef_usd = col_r1.number_input("Efectivo $ en Caja", 0.0)
            r_pm_bs = col_r2.number_input("Total en Pago Móvil", 0.0)
            r_pu_bs = col_r2.number_input("Total en Punto", 0.0)
            r_ze_usd = col_r3.number_input("Total en Zelle $", 0.0)
            r_ot_bs = col_r3.number_input("Otras Cuentas Bs", 0.0)

        # BOTÓN DE CIERRE DEFINITIVO
        st.divider()
        if st.button("🏮 FINALIZAR JORNADA Y BLOQUEAR CAJA", use_container_width=True, type="primary"):
            # Cálculos finales
            esp_bs = s_ef_bs + f_bs_ini
            esp_usd = s_di_usd + f_usd_ini
            d_bs = r_ef_bs - esp_bs; d_usd = r_ef_usd - esp_usd
            d_pm = r_pm_bs - s_pm_bs; d_pu = r_pu_bs - s_pu_bs

            # 1. ACTUALIZAR ESTADO EN DB PARA BLOQUEO
            db.table("gastos").update({"estado": "cerrado"}).eq("descripcion", f"APERTURA_{hoy}").execute
