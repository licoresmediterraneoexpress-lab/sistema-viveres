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

# --- 6. CIERRE DE CAJA (VERSION PROFESIONAL INTEGRADA) ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Gestión de Caja: Apertura y Arqueo")
    f_hoy = date.today().isoformat()
    
    # --- BLOQUE 1: APERTURA ---
    with st.expander("🔑 APERTURA DE JORNADA", expanded=True):
        res_ap = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{f_hoy}").execute()
        
        if not res_ap.data:
            st.subheader("Registro de Fondo Inicial")
            c_ap1, c_ap2, c_ap3 = st.columns(3)
            tasa_ap = c_ap1.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)
            ef_bs_ap = c_ap2.number_input("Fondo Inicial Bs", 0.0)
            ef_usd_ap = c_ap3.number_input("Fondo Inicial $", 0.0)
            
            # Cálculo informativo para el usuario
            total_ap_usd = ef_usd_ap + (ef_bs_ap / tasa_ap)
            st.caption(f"Valor total de apertura: ${total_ap_usd:,.2f} USD")

            if st.button("✅ REGISTRAR APERTURA", use_container_width=True):
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{f_hoy}",
                    "monto_usd": total_ap_usd,
                    "monto_bs_extra": ef_bs_ap, # Guardamos Bs para el arqueo
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success("¡Caja abierta exitosamente!")
                time.sleep(1)
                st.rerun()
        else:
            d_ap = res_ap.data[0]
            st.info(f"🟢 Caja Abierta hoy con: {d_ap['monto_bs_extra']:,.2f} Bs. y ${(d_ap['monto_usd'] - (d_ap['monto_bs_extra']/60)):,.2f} USD")

    st.divider()

    # --- BLOQUE 2: RESUMEN DE VENTAS Y MÉTODOS DE PAGO ---
    f_rep = st.date_input("Consultar Fecha de Cierre", date.today())
    
    # Consultar ventas y gastos (para utilidades)
    v = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v.data:
        df_v = pd.DataFrame(v.data)
        df_g = pd.DataFrame(g.data) if g.data else pd.DataFrame()
        
        # 1. Totales por método de pago
        st.subheader("💳 Ventas por Tipo de Pago (Sistema)")
        s_ef_bs = df_v['pago_efectivo'].sum()
        s_pm_bs = df_v['pago_movil'].sum()
        s_pu_bs = df_v['pago_punto'].sum()
        s_ze_usd = df_v['pago_zelle'].sum()
        s_di_usd = df_v['pago_divisas'].sum()
        s_ot_bs = df_v['pago_otros'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Efectivo Bs", f"{s_ef_bs:,.2f}")
        c1.metric("Pago Móvil Bs", f"{s_pm_bs:,.2f}")
        c2.metric("Punto Bs", f"{s_pu_bs:,.2f}")
        c2.metric("Zelle $", f"${s_ze_usd:,.2f}")
        c3.metric("Divisas $", f"${s_di_usd:,.2f}")
        c3.metric("Otros Bs", f"{s_ot_bs:,.2f}")

        # 2. Análisis de Rentabilidad
        st.divider()
        st.subheader("📈 Análisis Financiero")
        t_ingreso = df_v['total_usd'].sum()
        t_costo = df_v['costo_venta'].sum()
        # Gastos excluyendo la apertura
        df_gastos_puros = df_g[~df_g['descripcion'].str.contains("APERTURA_", na=False)] if not df_g.empty else pd.DataFrame()
        t_gastos = df_gastos_puros['monto_usd'].sum() if not df_gastos_puros.empty else 0.0
        
        u1, u2, u3 = st.columns(3)
        u1.metric("Ingreso Bruto", f"${t_ingreso:,.2f}")
        u2.metric("Gastos/Egresos", f"${t_gastos:,.2f}")
        u3.metric("Utilidad Neta", f"${(t_ingreso - t_costo - t_gastos):,.2f}", delta_color="normal")

        # --- BLOQUE 3: ARQUEO FÍSICO (COMPARATIVA REAL) ---
        st.divider()
        st.subheader("🔍 Arqueo de Caja Real vs Sistema")
        
        # Obtenemos fondo inicial para el cuadre
        reg_ap = df_g[df_g['descripcion'].str.contains("APERTURA_", na=False)] if not df_g.empty else pd.DataFrame()
        f_bs_ini = reg_ap['monto_bs_extra'].sum() if not reg_ap.empty else 0.0
        f_usd_ini = (reg_ap['monto_usd'].sum() - (f_bs_ini / 60)) if not reg_ap.empty else 0.0

        st.warning(f"Nota: El sistema espera en caja el Fondo Inicial + Ventas en Efectivo.")
        
        col_arqueo1, col_arqueo2 = st.columns(2)
        with col_arqueo1:
            st.markdown("### 💵 Conteo Físico")
            r_ef_bs = st.number_input("Total Efectivo Bs en Caja", 0.0)
            r_di_usd = st.number_input("Total Divisas $ en Caja", 0.0)
            
        with col_arqueo2:
            st.markdown("### ⚖️ Diferencia")
            esperado_bs = s_ef_bs + f_bs_ini
            esperado_usd = s_di_usd + f_usd_ini
            
            dif_bs = r_ef_bs - esperado_bs
            dif_usd = r_di_usd - esperado_usd
            
            st.metric("Dif. Bolívares", f"{dif_bs:,.2f} Bs", delta=dif_bs)
            st.metric("Dif. Divisas", f"${dif_usd:,.2f}", delta=dif_usd)

  # ========================================================
# --- 6. CIERRE DE CAJA (VERSIÓN FINAL CONSOLIDADA) ---
# ========================================================
elif opcion == "📊 Cierre de Caja":
    import time 
    st.header("📊 Gestión de Caja: Apertura y Cierre")
    f_hoy = date.today().isoformat()
    
    # --- BLOQUE DE APERTURA ---
    with st.expander("🔑 APERTURA DE JORNADA", expanded=True):
        res_ap = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{f_hoy}").execute()
        
        if not res_ap.data:
            st.subheader("Registro de Fondo Inicial")
            c_ap1, c_ap2, c_ap3 = st.columns(3)
            tasa_ap = c_ap1.number_input("Tasa de Cambio (Bs/$)", 1.0, 500.0, 60.0)
            ef_bs_ap = c_ap2.number_input("Fondo Efectivo Bs", 0.0)
            ef_usd_ap = c_ap3.number_input("Fondo Efectivo $", 0.0)
            
            if st.button("✅ REGISTRAR APERTURA", use_container_width=True):
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{f_hoy}",
                    "monto_usd": ef_usd_ap + (ef_bs_ap / tasa_ap),
                    "monto_bs_extra": ef_bs_ap,
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success("¡Caja abierta exitosamente!")
                st.rerun()
        else:
            d_ap = res_ap.data[0]
            # Cálculo para mostrar el desglose de lo que se abrió
            bs_f = d_ap['monto_bs_extra']
            usd_f = d_ap['monto_usd'] - (bs_f / 60) # Usamos 60 como tasa base visual
            st.info(f"🟢 Caja Abierta: {bs_f:,.2f} Bs. | ${usd_f:,.2f} USD")

    st.divider()
    
    # --- CONSULTA DE RESULTADOS ---
    f_rep = st.date_input("Fecha a Consultar", date.today())
    v = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v.data:
        df_v = pd.DataFrame(v.data)
        df_g = pd.DataFrame(g.data)
        
        # Filtros para separar gastos de apertura
        df_gr = df_g[~df_g['descripcion'].str.contains("APERTURA_", na=False)]
        reg_ap = df_g[df_g['descripcion'].str.contains("APERTURA_", na=False)]
        
        # Fondos iniciales
        f_bs_ini = reg_ap['monto_bs_extra'].sum() if not reg_ap.empty else 0.0
        f_usd_ini = (reg_ap['monto_usd'].sum() - (f_bs_ini / 60)) if not reg_ap.empty else 0.0

        # --- 1. MÉTODOS DE PAGO (INGRESOS BRUTOS) ---
        st.subheader("💳 Detalle de Pagos (Sistema)")
        s_ef_bs = df_v['pago_efectivo'].sum(); s_pm_bs = df_v['pago_movil'].sum()
        s_pu_bs = df_v['pago_punto'].sum(); s_ot_bs = df_v['pago_otros'].sum()
        s_ze_usd = df_v['pago_zelle'].sum(); s_di_usd = df_v['pago_divisas'].sum()
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Efec. Bs", f"{s_ef_bs:,.2f}")
        c2.metric("P.Móvil", f"{s_pm_bs:,.2f}")
        c3.metric("Punto", f"{s_pu_bs:,.2f}")
        c4.metric("Otros", f"{s_ot_bs:,.2f}")
        c5.metric("Zelle $", f"${s_ze_usd:,.2f}")
        c6.metric("Divisa $", f"${s_di_usd:,.2f}")
        
        # --- 2. ANÁLISIS DE UTILIDADES ---
        st.divider()
        st.subheader("📈 Análisis de Rentabilidad")
        t_ingreso = df_v['total_usd'].sum()
        t_costo = df_v['costo_venta'].sum()
        t_gastos_op = df_gr['monto_usd'].sum()
        ganancia_bruta = t_ingreso - t_costo
        ganancia_neta = ganancia_bruta - t_gastos_op
        
        u1, u2, u3, u4 = st.columns(4)
        u1.metric("INGRESO TOTAL", f"${t_ingreso:,.2f}")
        u2.metric("COSTO MERCANCÍA", f"${t_costo:,.2f}", delta_color="inverse")
        u3.metric("GANANCIA BRUTA", f"${ganancia_bruta:,.2f}")
        u4.metric("GANANCIA NETA", f"${ganancia_neta:,.2f}")

        # --- 3. ARQUEO FÍSICO ---
        st.divider()
        st.subheader("🔍 Arqueo de Caja Real")
        st.write("Introduzca el conteo físico del dinero en caja:")
        col_c1, col_c2, col_c3 = st.columns(3)
        r_ef_bs = col_c1.number_input("Real Efectivo Bs", 0.0)
        r_di_usd = col_c1.number_input("Real Divisas $", 0.0)
        r_pm_bs = col_c2.number_input("Real Pago Móvil Bs", 0.0)
        r_pu_bs = col_c2.number_input("Real Punto Bs", 0.0)
        r_ze_usd = col_c3.number_input("Real Zelle $", 0.0)
        r_ot_bs = col_c3.number_input("Real Otros Bs", 0.0)

# --- 6. CIERRE DE CAJA (VERSIÓN FINAL CORREGIDA) ---
elif opcion == "📊 Cierre de Caja":
    import time 
    st.header("📊 Gestión de Caja: Apertura y Arqueo")
    f_hoy = date.today().isoformat()
    
    # 1. INICIALIZACIÓN PREVENTIVA (Evita errores NameError)
    r_ef_bs = r_di_usd = r_pm_bs = r_pu_bs = r_ze_usd = r_ot_bs = 0.0
    f_bs_ini = f_usd_ini = 0.0
    
    # --- BLOQUE DE APERTURA ---
    with st.expander("🔑 APERTURA DE JORNADA", expanded=True):
        res_ap = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{f_hoy}").execute()
        
        if not res_ap.data:
            st.subheader("Registro de Fondo Inicial")
            c_ap1, c_ap2, c_ap3 = st.columns(3)
            tasa_ap = c_ap1.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)
            ef_bs_ap = c_ap2.number_input("Fondo Inicial Bs", 0.0)
            ef_usd_ap = c_ap3.number_input("Fondo Inicial $", 0.0)
            
            if st.button("✅ REGISTRAR APERTURA", use_container_width=True):
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{f_hoy}",
                    "monto_usd": ef_usd_ap + (ef_bs_ap / tasa_ap),
                    "monto_bs_extra": ef_bs_ap,
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success("¡Caja abierta exitosamente!")
                time.sleep(1)
                st.rerun()
        else:
            d_ap = res_ap.data[0]
            f_bs_ini = d_ap['monto_bs_extra']
            # El USD inicial es el total menos el equivalente en BS
            f_usd_ini = d_ap['monto_usd'] - (f_bs_ini / 60) # Usando 60 como base o la tasa guardada
            st.info(f"🟢 Caja Abierta: {f_bs_ini:,.2f} Bs. | ${f_usd_ini:,.2f} USD")

    st.divider()
    f_rep = st.date_input("Fecha a Consultar", date.today())
    v = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v.data:
        df_v = pd.DataFrame(v.data)
        df_g = pd.DataFrame(g.data)
        
        # Filtros de Gastos
        df_gr = df_g[~df_g['descripcion'].str.contains("APERTURA_", na=False)]
        
        # --- 1. MÉTODOS DE PAGO (SISTEMA) ---
        st.subheader("💳 Detalle de Pagos (Sistema)")
        s_ef_bs = df_v['pago_efectivo'].sum(); s_pm_bs = df_v['pago_movil'].sum()
        s_pu_bs = df_v['pago_punto'].sum(); s_ot_bs = df_v['pago_otros'].sum()
        s_ze_usd = df_v['pago_zelle'].sum(); s_di_usd = df_v['pago_divisas'].sum()
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Efec. Bs", f"{s_ef_bs:,.2f}"); c2.metric("P.Móvil", f"{s_pm_bs:,.2f}")
        c3.metric("Punto", f"{s_pu_bs:,.2f}"); c4.metric("Otros", f"{s_ot_bs:,.2f}")
        c5.metric("Zelle $", f"{s_ze_usd:,.2f}"); c6.metric("Divisa $", f"{s_di_usd:,.2f}")
        
        # --- 2. ANÁLISIS FINANCIERO ---
        st.divider()
        st.subheader("📈 Análisis de Rentabilidad")
        t_ingreso = df_v['total_usd'].sum()
        t_costo = df_v['costo_venta'].sum()
        t_gastos_op = df_gr['monto_usd'].sum()
        ganancia_bruta = t_ingreso - t_costo
        ganancia_neta = ganancia_bruta - t_gastos_op
        
        u1, u2, u3, u4 = st.columns(4)
        u1.metric("INGRESO TOTAL", f"${t_ingreso:,.2f}")
        u2.metric("COSTO MERCANCÍA", f"${t_costo:,.2f}")
        u3.metric("GANANCIA BRUTA", f"${ganancia_bruta:,.2f}")
        u4.metric("GANANCIA NETA", f"${ganancia_neta:,.2f}")

        # --- 3. ARQUEO FÍSICO (VARIABLES CORREGIDAS) ---
        st.divider()
        st.subheader("🔍 Arqueo de Caja Real")
        col_c1, col_c2, col_c3 = st.columns(3)
        r_ef_bs = col_c1.number_input("Real en Efectivo Bs", 0.0)
        r_di_usd = col_c1.number_input("Real en Divisas $", 0.0)
        r_pm_bs = col_c2.number_input("Real en Pago Móvil Bs", 0.0)
        r_pu_bs = col_c2.number_input("Real en Punto Bs", 0.0)
        r_ze_usd = col_c3.number_input("Real en Zelle $", 0.0)
        r_ot_bs = col_c3.number_input("Real en Otros Bs", 0.0)

# --- 6. MÓDULO DE CAJA PROFESIONAL ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Control y Arqueo de Caja")
    hoy = date.today().isoformat()
    
    # --- 6.1. LÓGICA DE ESTADO DE CAJA ---
    # Buscamos si hay una apertura hoy
    res_caja = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{hoy}").execute()
    caja_abierta = len(res_caja.data) > 0
    
    # --- BLOQUE A: APERTURA (Solo si no hay una) ---
    if not caja_abierta:
        st.warning("⚠️ La caja se encuentra cerrada para el día de hoy.")
        with st.form("form_apertura"):
            st.subheader("🔑 Abrir Turno")
            col1, col2, col3 = st.columns(3)
            tasa_hoy = col1.number_input("Tasa de Cambio (Bs/$)", min_value=1.0, value=60.0)
            f_bs = col2.number_input("Fondo en Bolívares (Bs)", min_value=0.0)
            f_usd = col3.number_input("Fondo en Divisas ($)", min_value=0.0)
            
            if st.form_submit_button("✅ REGISTRAR APERTURA Y EMPEZAR"):
                # Guardamos el fondo inicial
                db.table("gastos").insert({
                    "descripcion": f"APERTURA_{hoy}",
                    "monto_usd": f_usd + (f_bs / tasa_hoy),
                    "monto_bs_extra": f_bs,
                    "fecha": datetime.now().isoformat(),
                    "estado": "abierto"
                }).execute()
                st.success("Caja abierta correctamente.")
                st.rerun()
    
    # --- BLOQUE B: PANEL DE CONTROL Y ARQUEO (Solo si ya está abierta) ---
    else:
        # Recuperar datos de apertura
        datos_ap = res_caja.data[0]
        fondo_bs_inicial = datos_ap['monto_bs_extra']
        fondo_usd_inicial = datos_ap['monto_usd'] - (fondo_bs_inicial / 60) # Ajuste base

        st.info(f"🟢 Caja abierta hoy con: {fondo_bs_inicial:,.2f} Bs | ${fondo_usd_inicial:,.2f} USD")

        # Consultar Movimientos del día
        ventas_hoy = db.table("ventas").select("*").gte("fecha", hoy).execute()
        gastos_hoy = db.table("gastos").select("*").gte("fecha", hoy).execute()
        
        df_v = pd.DataFrame(ventas_hoy.data) if ventas_hoy.data else pd.DataFrame()
        df_g = pd.DataFrame(gastos_hoy.data) if gastos_hoy.data else pd.DataFrame()

        # Cálculos de Sistema
        if not df_v.empty:
            sys_ef_bs = df_v['pago_efectivo'].sum()
            sys_ef_usd = df_v['pago_divisas'].sum()
            sys_pm_bs = df_v['pago_movil'].sum()
            sys_zelle = df_v['pago_zelle'].sum()
            sys_punto = df_v['pago_punto'].sum()
            total_ingreso_usd = df_v['total_usd'].sum()
        else:
            sys_ef_bs = sys_ef_usd = sys_pm_bs = sys_zelle = sys_punto = total_ingreso_usd = 0.0

        # --- SECCIÓN DE CONTEO FÍSICO ---
        st.divider()
        st.subheader("🔍 Arqueo Físico (Lo que tienes en mano)")
        
        c1, c2, c3 = st.columns(3)
        real_ef_bs = c1.number_input("Efectivo Bolívares Físico", 0.0, key="r1")
        real_ef_usd = c1.number_input("Efectivo Divisas Físico", 0.0, key="r2")
        
        real_pm_bs = c2.number_input("Total en Pago Móvil (Banco)", 0.0, key="r3")
        real_pu_bs = c2.number_input("Total en Punto (Banco)", 0.0, key="r4")
        
        real_zelle = c3.number_input("Total Zelle (App)", 0.0, key="r5")
        
        # --- CÁLCULO DE DIFERENCIAS ---
        # Esperado = Fondo inicial + Ventas
        esperado_bs = sys_ef_bs + fondo_bs_inicial
        esperado_usd = sys_ef_usd + fondo_usd_inicial
        
        # --- BOTÓN DE CIERRE ---
        st.divider()
        if st.button("🏮 REALIZAR CIERRE DE JORNADA", use_container_width=True):
            # Resultados
            diff_bs = real_ef_bs - esperado_bs
            diff_usd = real_ef_usd - esperado_usd
            diff_pm = real_pm_bs - sys_pm_bs
            
            st.subheader("📋 Resultado del Cuadre")
            
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Diferencia Efectivo Bs", f"{diff_bs:,.2f} Bs", delta=diff_bs)
            col_res2.metric("Diferencia Efectivo $", f"${diff_usd:,.2f}", delta=diff_usd)
            col_res3.metric("Diferencia Pago Móvil", f"{diff_pm:,.2f} Bs", delta=diff_pm)

            # Reporte Visual para Impresión
            reporte_cierre = f"""
            <div style="background: white; color: black; padding: 20px; border: 2px solid #000; font-family: monospace;">
                <h2 style="text-align: center;">MEDITERRANEO EXPRESS</h2>
                <h4 style="text-align: center;">CIERRE DE CAJA - {hoy}</h4>
                <hr>
                <p><b>VENTAS TOTALES:</b> ${total_ingreso_usd:,.2f}</p>
                <hr>
                <b>DETALLE DE ARQUEO:</b><br>
                - Efec. Bs: Real {real_ef_bs:,.2f} / Esp. {esperado_bs:,.2f} (Dif: {diff_bs:,.2f})<br>
                - Efec. $: Real {real_ef_usd:,.2f} / Esp. {esperado_usd:,.2f} (Dif: {diff_usd:,.2f})<br>
                - Pago Móvil: Real {real_pm_bs:,.2f} / Esp. {sys_pm_bs:,.2f} (Dif: {diff_pm:,.2f})<br>
                - Zelle: Real {real_zelle:,.2f} / Esp. {sys_zelle:,.2f}<br>
                <hr>
                <p style="text-align:center;">FIRMA RESPONSABLE</p>
            </div>
            """
            st.markdown(reporte_cierre, unsafe_allow_html=True)
            st.balloons()
