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

# --- 4. MÓDULO VENTA RÁPIDA (ORDENADO Y CORREGIDO) ---
elif opcion == "🛒 Venta Rápida":
    from datetime import date, datetime
    import pandas as pd
    
    # 1. DEFINIR VARIABLES DE TIEMPO PRIMERO (Evita NameError)
    hoy = date.today().isoformat()
    
    # 2. VERIFICACIÓN DE ESTADO DE CAJA (El candado de seguridad)
    res_caja_check = db.table("gastos").select("estado").eq("descripcion", f"APERTURA_{hoy}").execute()
    
    if not res_caja_check.data:
        st.warning("⚠️ La caja no ha sido abierta hoy. Por favor, realiza la apertura en el módulo de 'Cierre de Caja'.")
        st.stop()
    elif res_caja_check.data[0].get('estado') == 'cerrado':
        st.error("🚫 LA CAJA ESTÁ CERRADA. No se pueden procesar más ventas hoy.")
        st.stop()

    # --- INICIO DE INTERFAZ DE VENTAS ---
    st.header("🛒 Ventas Mediterraneo Express")
    
    with st.sidebar:
        st.divider()
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)

    # Consulta de productos
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
        
        # Validación de cantidad máxima según stock
        cant_max = int(p_data['stock']) if p_data['stock'] > 0 else 1
        cant_sel = c3.number_input("Cantidad", 1, max_value=cant_max)
        
        if st.button("➕ AÑADIR AL CARRITO"):
            if p_data['stock'] >= cant_sel:
                precio = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                st.session_state.car.append({
                    "p": item_sel, 
                    "c": cant_sel, 
                    "u": precio, 
                    "t": round(float(precio) * int(cant_sel), 2), 
                    "costo_u": float(p_data['costo'])
                })
                st.rerun()
            else:
                st.error("No hay suficiente stock disponible.")

    # Visualización del Carrito
    if st.session_state.car:
        st.divider()
        df_car = pd.DataFrame(st.session_state.car)
        st.table(df_car[['p', 'c', 'u', 't']].rename(columns={'p':'Producto','c':'Cant','u':'Precio $','t':'Total $'}))
        
        sub_total_usd = sum(float(x['t']) for x in st.session_state.car)
        total_bs_sugerido = sub_total_usd * tasa
        st.write(f"### Total Sugerido: **{total_bs_sugerido:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        total_a_cobrar_bs = st.number_input("MONTO FINAL A COBRAR (Bs)", value=float(total_bs_sugerido))
        
        # Desglose de pagos
        st.markdown("#### Métodos de Pago")
        col_p1, col_p2, col_p3 = st.columns(3)
        ef = col_p1.number_input("Efectivo Bs", 0.0)
        pm = col_p1.number_input("Pago Móvil Bs", 0.0)
        pu = col_p2.number_input("Punto Bs", 0.0)
        ot = col_p2.number_input("Otros Bs", 0.0)
        ze = col_p3.number_input("Zelle $", 0.0)
        di = col_p3.number_input("Divisas $", 0.0)
        
        if st.button("🚀 FINALIZAR VENTA", use_container_width=True, type="primary"):
            try:
                # Cálculo de propina o diferencia por redondeo
                propina_usd = (total_a_cobrar_bs / tasa) - sub_total_usd
                ahora_iso = datetime.now().isoformat()
                
                for x in st.session_state.car:
                    # Insertar cada producto de la venta
                    db.table("ventas").insert({
                        "producto": x['p'], 
                        "cantidad": x['c'], 
                        "total_usd": x['t'], 
                        "tasa_cambio": tasa,
                        "pago_efectivo": ef, 
                        "pago_punto": pu, 
                        "pago_movil": pm, 
                        "pago_zelle": ze, 
                        "pago_otros": ot, 
                        "pago_divisas": di, 
                        "costo_venta": x['costo_u'] * x['c'],
                        "propina": propina_usd / len(st.session_state.car), 
                        "fecha": ahora_iso
                    }).execute()
                    
                    # Actualizar Inventario
                    stk_actual = df_p[df_p['nombre'] == x['p']].iloc[0]['stock']
                    db.table("inventario").update({"stock": int(stk_actual - x['c'])}).eq("nombre", x['p']).execute()
                
                st.success("🎉 VENTA REGISTRADA CON ÉXITO")
                st.session_state.car = []
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar la venta: {e}")

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado.")

# --- 6. MÓDULO DE CAJA: CONTROL TOTAL Y CIERRE (VERSIÓN CORREGIDA Y FINAL) ---
elif opcion == "📊 Cierre de Caja":
    import time
    from datetime import date, datetime
    import pandas as pd

    st.header("📊 Gestión de Caja y Arqueo Integral")
    
    # 1. DEFINICIÓN GLOBAL DE VARIABLES DE TIEMPO
    ahora_dt = datetime.now()
    hoy = ahora_dt.date().isoformat()
    ahora_iso = ahora_dt.isoformat()
    
    # 2. VERIFICACIÓN DE ESTADO DE CAJA EN SUPABASE
    # Buscamos si ya existe un registro de apertura para el día de hoy
    res_caja = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{hoy}").execute()
    caja_datos = res_caja.data[0] if res_caja.data else None
    
    # Determinamos estados
    caja_abierta_en_db = caja_datos is not None
    esta_cerrada = caja_datos.get('estado') == 'cerrado' if caja_abierta_en_db else False

    # --- BLOQUE A: FORMULARIO DE APERTURA (Si no existe registro hoy) ---
    if not caja_abierta_en_db:
        st.warning("⚠️ La caja se encuentra cerrada. Por favor, registre el fondo inicial para operar hoy.")
        
        # Usamos un formulario para asegurar que los datos se envíen juntos
        with st.form("form_apertura_final"):
            st.subheader("🔑 Abrir Turno de Trabajo")
            col1, col2, col3 = st.columns(3)
            
            tasa_ap = col1.number_input("Tasa del Día (Bs/$)", min_value=1.0, value=60.0, step=0.1)
            f_bs = col2.number_input("Fondo Inicial en Bolívares (Bs)", min_value=0.0, step=10.0)
            f_usd = col3.number_input("Fondo Inicial en Divisas ($)", min_value=0.0, step=1.0)
            
            submit_apertura = st.form_submit_button("✅ REGISTRAR APERTURA Y EMPEZAR", use_container_width=True)
            
            if submit_apertura:
                try:
                    # Cálculo del monto total convertido a USD para la columna monto_usd
                    total_usd_ap = float(f_usd) + (float(f_bs) / float(tasa_ap))
                    
                    # Inserción en la tabla gastos
                    db.table("gastos").insert({
                        "descripcion": f"APERTURA_{hoy}",
                        "monto_usd": total_usd_ap,
                        "monto_bs_extra": float(f_bs),
                        "fecha": ahora_iso,
                        "estado": "abierto"
                    }).execute()
                    
                    st.success("¡Caja abierta exitosamente! Cargando panel...")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al abrir caja: {str(e)}")

    # --- BLOQUE B: VISTA DE BLOQUEO (Si la caja ya fue cerrada) ---
    elif esta_cerrada:
        st.success("✅ JORNADA FINALIZADA: La caja de hoy ha sido cerrada y bloqueada.")
        st.info("No se permiten más registros de ventas o gastos para la fecha actual.")
        
        # Mostramos resumen rápido de solo lectura
        if st.button("🔄 Refrescar Pantalla"):
            st.rerun()

    # --- BLOQUE C: PANEL DE ARQUEO ACTIVO (Caja abierta, lista para cerrar) ---
    else:
        # Extraemos fondos iniciales del registro de apertura
        f_bs_ini = float(caja_datos.get('monto_bs_extra', 0.0))
        # Calculamos el USD inicial restando el equivalente en Bs del total en USD
        # Usamos la tasa de 60 por defecto si no se guardó la tasa específica
        f_usd_ini = float(caja_datos.get('monto_usd', 0.0)) - (f_bs_ini / 60)

        st.info(f"🟢 Caja Abierta hoy con: {f_bs_ini:,.2f} Bs | ${f_usd_ini:,.2f} USD")

        # Consultar todas las ventas del día actual
        v_res = db.table("ventas").select("*").gte("fecha", hoy).execute()
        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()

        # Inicializamos contadores del sistema
        if not df_v.empty:
            s_ef_bs = df_v['pago_efectivo'].sum()
            s_di_usd = df_v['pago_divisas'].sum()
            s_pm_bs = df_v['pago_movil'].sum()
            s_pu_bs = df_v['pago_punto'].sum()
            s_ze_usd = df_v['pago_zelle'].sum()
            s_ot_bs = df_v['pago_otros'].sum()
            total_ingreso = df_v['total_usd'].sum()
        else:
            s_ef_bs = s_di_usd = s_pm_bs = s_pu_bs = s_ze_usd = s_ot_bs = total_ingreso = 0.0

        # Interfaz de Métricas del Sistema
        st.subheader("💳 Ventas Registradas en Sistema")
        c_sys = st.columns(4)
        c_sys[0].metric("Efectivo Bs", f"{s_ef_bs:,.2f}")
        c_sys[1].metric("Divisas $", f"{s_di_usd:,.2f}")
        c_sys[2].metric("Pago Móvil", f"{s_pm_bs:,.2f}")
        c_sys[3].metric("Punto / Zelle", f"{(s_pu_bs + s_ze_usd):,.2f}")

        st.divider()
        st.subheader("📝 Arqueo Físico (Dinero en Mano)")
        
        # Contenedor para entrada de datos físicos
        with st.container(border=True):
            col_r1, col_r2, col_r3 = st.columns(3)
            r_ef_bs = col_r1.number_input("Total Efectivo Bs", 0.0)
            r_ef_usd = col_r1.number_input("Total Efectivo $", 0.0)
            r_pm_bs = col_r2.number_input("Total Pago Móvil Bs", 0.0)
            r_pu_bs = col_r2.number_input("Total Punto Bs", 0.0)
            r_ze_usd = col_r3.number_input("Total Zelle $", 0.0)
            r_ot_bs = col_r3.number_input("Otros ingresos Bs", 0.0)

        # BOTÓN DE CIERRE DEFINITIVO
        if st.button("🏮 FINALIZAR JORNADA Y BLOQUEAR TODO", use_container_width=True, type="primary"):
            try:
                # 1. Marcar el registro de apertura como CERRADO
                db.table("gastos").update({"estado": "cerrado"}).eq("descripcion", f"APERTURA_{hoy}").execute()
                
                # 2. Cálculos de conciliación (Esperado vs Real)
                esp_bs = s_ef_bs + f_bs_ini
                esp_usd = s_di_usd + f_usd_ini
                dif_bs = r_ef_bs - esp_bs
                dif_usd = r_ef_usd - esp_usd

                st.balloons()
                st.success("✅ Caja cerrada y bloqueada exitosamente.")

                # 3. Generación del Reporte Visual Final (Corregido variable reporte_html)
                reporte_html = f"""
                <div style="background: white; color: black; padding: 25px; border: 4px solid #333; font-family: 'Courier New', Courier, monospace; line-height: 1.2;">
                    <center>
                        <h2 style="margin:0;">MEDITERRANEO EXPRESS</h2>
                        <h4 style="margin:0;">REPORTE FINAL DE CIERRE</h4>
                        <p>Fecha: {hoy}</p>
                    </center>
                    <hr style="border: 1px dashed black;">
                    <table style="width:100%;">
                        <tr><td><b>VENTAS DEL DÍA:</b></td><td style="text-align:right;">${total_ingreso:,.2f}</td></tr>
                        <tr><td><b>FONDO INICIAL BS:</b></td><td style="text-align:right;">{f_bs_ini:,.2f}</td></tr>
                        <tr><td><b>FONDO INICIAL $:</b></td><td style="text-align:right;">${f_usd_ini:,.2f}</td></tr>
                    </table>
                    <hr style="border: 1px dashed black;">
                    <center><b>CUADRE DE CAJA</b></center>
                    <table style="width:100%; font-size: 14px;">
                        <tr><td>EFECTIVO BS (ESP):</td><td style="text-align:right;">{esp_bs:,.2f}</td></tr>
                        <tr><td>EFECTIVO BS (REAL):</td><td style="text-align:right;">{r_ef_bs:,.2f}</td></tr>
                        <tr><td><b>DIFERENCIA BS:</b></td><td style="text-align:right;"><b>{dif_bs:,.2f}</b></td></tr>
                        <tr><td colspan="2"><br></td></tr>
                        <tr><td>EFECTIVO $ (ESP):</td><td style="text-align:right;">${esp_usd:,.2f}</td></tr>
                        <tr><td>EFECTIVO $ (REAL):</td><td style="text-align:right;">${r_ef_usd:,.2f}</td></tr>
                        <tr><td><b>DIFERENCIA $:</b></td><td style="text-align:right;"><b>${dif_usd:,.2f}</b></td></tr>
                    </table>
                    <hr style="border: 1px dashed black;">
                    <center><p>CAJA CERRADA POR SISTEMA</p></center>
                </div>
                """
                st.markdown(reporte_html, unsafe_allow_html=True)
                
                # Esperar para que el usuario pueda ver el reporte antes de refrescar y bloquear
                time.sleep(7)
                st.rerun()

            except Exception as e:
                st.error(f"Error técnico durante el cierre: {str(e)}")
