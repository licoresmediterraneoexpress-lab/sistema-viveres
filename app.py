import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
import time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express POS Premium", layout="wide")

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
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    if st.button("🗑️ Vaciar Carrito"):
        st.session_state.car = []
        st.rerun()

# --- 3. MÓDULO INVENTARIO PROFESIONAL ---
if opcion == "📦 Inventario":
    st.header("📦 Centro de Control de Inventario")
    
    # Obtener datos
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_inv.empty:
        # Cálculos Financieros
        df_inv['valor_costo'] = df_inv['stock'] * df_inv['costo']
        df_inv['valor_venta'] = df_inv['stock'] * df_inv['precio_detal']
        df_inv['ganancia_estimada'] = df_inv['valor_venta'] - df_inv['valor_costo']

        # 1. KPIs Superiores (Métricas)
        m1, m2, m3 = st.columns(3)
        m1.metric("🛒 Inversión en Stock", f"${df_inv['valor_costo'].sum():,.2f}")
        m2.metric("💰 Valor de Venta", f"${df_inv['valor_venta'].sum():,.2f}")
        m3.metric("📈 Ganancia Proyectada", f"${df_inv['ganancia_estimada'].sum():,.2f}")

        st.divider()

        # 2. Herramientas de Exportación y Filtro
        col_bus, col_exp = st.columns([3, 1])
        
        with col_exp:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_inv[['nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor']].to_excel(writer, index=False, sheet_name='Stock')
            
            st.download_button(
                label="📥 Exportar a Excel",
                data=buffer.getvalue(),
                file_name=f"Inventario_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # 3. Buscador y Alertas de Stock Crítico
        bus_inv = col_bus.text_input("🔍 Buscar producto o marca...", placeholder="Ej: Harina, Polar, Mantequilla...")
        
        # Filtrado dinámico
        df_m = df_inv[df_inv['nombre'].str.contains(bus_inv, case=False)] if bus_inv else df_inv
        
        # Identificar stock bajo (menos de 10 unidades)
        bajo_stock = df_m[df_m['stock'] <= 10]
        if not bajo_stock.empty:
            st.error(f"⚠️ ATENCIÓN: Tienes {len(bajo_stock)} productos con stock crítico (menos de 10 unidades).")

        # 4. Tabla Maestra Estilizada
        # Añadimos un indicador visual (Emoji) según el stock
        def alert_stock(stk):
            if stk <= 0: return "❌ Agotado"
            elif stk <= 10: return "⚠️ Crítico"
            return "✅ Disponible"

        df_m['Estado'] = df_m['stock'].apply(alert_stock)
        
        st.dataframe(
            df_m[['Estado', 'nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']],
            use_container_width=True,
            hide_index=True
        )

    # 5. Panel de Control de Productos (Admin)
    with st.expander("🛠️ Panel de Carga y Edición de Mercancía"):
        if st.text_input("Clave de Administrador", type="password") == CLAVE_ADMIN:
            with st.form("form_gestion"):
                c1, c2 = st.columns(2)
                f_nom = c1.text_input("Nombre Completo del Producto")
                f_stk = c1.number_input("Cantidad en Almacén (Stock)", 0)
                f_cos = c2.number_input("Costo de Compra ($)", 0.0, format="%.2f")
                f_pde = c2.number_input("Precio Venta Detal ($)", 0.0, format="%.2f")
                
                c3, c4 = st.columns(2)
                f_pma = c3.number_input("Precio Venta Mayor ($)", 0.0, format="%.2f")
                f_mma = c4.number_input("Cantidad Mínima para Mayor", 12)
                
                if st.form_submit_button("💾 ACTUALIZAR / REGISTRAR PRODUCTO"):
                    if f_nom:
                        data_prod = {
                            "nombre": f_nom, "stock": f_stk, "costo": f_cos, 
                            "precio_detal": f_pde, "precio_mayor": f_pma, "min_mayor": f_mma
                        }
                        db.table("inventario").upsert(data_prod, on_conflict="nombre").execute()
                        st.success(f"Producto '{f_nom}' actualizado correctamente.")
                        st.rerun()
                    else:
                        st.warning("El nombre es obligatorio.")
elif opcion == "🛒 Venta Rápida":
    import time
    st.header("🛒 Terminal de Ventas")
    
    # 1. Configuración de Tasa
    with st.sidebar:
        st.divider()
        tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)

    # 2. Obtención de productos
    res_p = db.table("inventario").select("*").execute()
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # BUSCADOR INTELIGENTE
        busc = st.text_input("🔍 Escribe letras del producto (ej: 'cer')").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        c1, c2, c3 = st.columns([2, 1, 1])
        item_sel = c1.selectbox("Producto Seleccionado", df_f['nombre'])
        
        p_data = df_p[df_p['nombre'] == item_sel].iloc[0]
        c2.write(f"**Stock:** {p_data['stock']}")
        c2.write(f"**Precio:** ${p_data['precio_detal']}")
        
        cant_sel = c3.number_input("Cantidad", 1, max_value=int(p_data['stock']) if p_data['stock'] > 0 else 1)
        
        if st.button("➕ AÑADIR AL CARRITO", use_container_width=True):
            if p_data['stock'] >= cant_sel:
                precio = float(p_data['precio_mayor']) if cant_sel >= p_data['min_mayor'] else float(p_data['precio_detal'])
                st.session_state.car.append({
                    "p": item_sel, "c": cant_sel, "u": precio, 
                    "t": round(float(precio) * int(cant_sel), 2), 
                    "costo_u": float(p_data['costo'])
                })
                st.rerun()
            else:
                st.error("No hay stock suficiente.")

    # 3. Gestión del Carrito y Pagos
    if st.session_state.car:
        st.divider()
        st.subheader("📋 Carrito de Compra")
        df_car = pd.DataFrame(st.session_state.car)
        st.table(df_car[['p', 'c', 'u', 't']].rename(columns={'p':'Producto','c':'Cant','u':'Precio $','t':'Total $'}))
        
        sub_total_usd = sum(float(x['t']) for x in st.session_state.car)
        total_bs_sugerido = sub_total_usd * tasa
        
        st.write(f"### Total Sugerido: **{total_bs_sugerido:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        # REDONDEO MANUAL
        total_a_cobrar_bs = st.number_input("MONTO FINAL A COBRAR (Ajuste manual/Redondeo)", value=float(total_bs_sugerido))
        
        st.write("#### 💸 Registro de Pagos Mixtos")
        col_p1, col_p2, col_p3 = st.columns(3)
        ef = col_p1.number_input("Efectivo Bs", 0.0); pm = col_p1.number_input("Pago Móvil Bs", 0.0)
        pu = col_p2.number_input("Punto Bs", 0.0); ot = col_p2.number_input("Otros Bs", 0.0)
        ze = col_p3.number_input("Zelle $", 0.0); di = col_p3.number_input("Divisas $", 0.0)
        
        pago_total_bs = ef + pm + pu + ot + ((ze + di) * tasa)
        diferencia = pago_total_bs - total_a_cobrar_bs
        
        if diferencia > 0.1:
            st.success(f"✅ VUELTO: {diferencia:,.2f} Bs.")
        elif diferencia < -0.1:
            st.warning(f"⚠️ FALTA: {abs(diferencia):,.2f} Bs.")

        # 4. Finalizar Venta
        if st.button("🚀 FINALIZAR VENTA Y GENERAR TICKET", use_container_width=True):
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
                st.balloons()
                
                # --- DISEÑO DEL TICKET ---
                ticket_html = f"""
                <div style='background-color: #fff; padding: 15px; border: 1px solid #ddd; color: #000; font-family: "Courier New", Courier, monospace; width: 300px; margin: auto;'>
                    <h3 style='text-align: center; margin:0;'>BODEGON Y LICORERIA MEDITERRANEO EXPRESS, C.A.</h3>
                    <p style='text-align: center; font-size: 12px; margin: 2px;'>RIF: J 404855807</p>
                    <p style='text-align: center; font-size: 11px; margin: 2px;'>BARRIO MATURIN CARRERA 11 CON CALLE 4</p>
                    <p style='text-align: center; font-size: 12px;'>{ahora}</p>
                    <hr style='border-top: 1px dashed #000;'>
                    <table style='width:100%; font-size: 12px;'>
                        <tr><th align='left'>DESCRIPCIÓN</th><th align='center'>CT</th><th align='right'>TOTAL</th></tr>
                """
                for item in items_ticket:
                    ticket_html += f"<tr><td>{item['p'][:15]}</td><td align='center'>{item['c']}</td><td align='right'>${item['t']:.2f}</td></tr>"
                
                ticket_html += f"""
                    </table>
                    <hr style='border-top: 1px dashed #000;'>
                    <h4 style='text-align: right; margin:2px;'>TOTAL USD: ${sub_total_usd:,.2f}</h4>
                    <h4 style='text-align: right; margin:2px;'>TOTAL BS: {total_a_cobrar_bs:,.2f}</h4>
                    <p style='text-align: center; font-size: 10px; margin-top: 10px;'>*** NO VALIDO COMO FACTURA FISCAL ***</p>
                </div>
                """
                st.markdown(ticket_html, unsafe_allow_html=True)
                
                # Botón de Impresión Directa
                st.download_button("📥 DESCARGAR TICKET (TEXTO)", data=ticket_html.replace('</div>','').replace('<hr>','-'*20), file_name=f"ticket_{int(time.time())}.txt")
                
                if st.button("🔄 NUEVA VENTA"):
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
            st.success("Gasto registrado y restado de la utilidad.")

# --- 6. CIERRE DE CAJA (VERSION PROFESIONAL CON TABLA MODIFICADA) ---
elif opcion == "📊 Cierre de Caja":
    import time 
    st.header("📊 Gestión de Caja: Apertura y Cierre")
    f_hoy = date.today().isoformat()
    
    # --- BLOQUE DE APERTURA ---
    with st.expander("🔑 APERTURA DE JORNADA", expanded=True):
        # Buscamos si existe apertura para hoy
        res_ap = db.table("gastos").select("*").eq("descripcion", f"APERTURA_{f_hoy}").execute()
        
        if not res_ap.data:
            st.subheader("Registro de Fondo Inicial")
            c_ap1, c_ap2, c_ap3 = st.columns(3)
            tasa_ap = c_ap1.number_input("Tasa de Cambio (Bs/$)", 1.0, 500.0, 60.0)
            ef_bs_ap = c_ap2.number_input("Fondo Efectivo Bs", 0.0)
            ef_usd_ap = c_ap3.number_input("Fondo Efectivo $", 0.0)
            
            if st.button("✅ REGISTRAR APERTURA", use_container_width=True):
                # Guardamos USD total y Bs por separado en la nueva columna
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
            st.info(f"🟢 Caja Abierta: {d_ap['monto_bs_extra']:,.2f} Bs. | ${ (d_ap['monto_usd'] - (d_ap['monto_bs_extra']/60)):,.2f} USD")

    st.divider()
    f_rep = st.date_input("Fecha a Consultar", date.today())
    v = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v.data:
        df_v = pd.DataFrame(v.data)
        df_g = pd.DataFrame(g.data)
        # Filtros
        df_gr = df_g[~df_g['descripcion'].str.contains("APERTURA_", na=False)]
        reg_ap = df_g[df_g['descripcion'].str.contains("APERTURA_", na=False)]
        
        # Fondo inicial desde las nuevas columnas
        f_bs_ini = reg_ap['monto_bs_extra'].sum() if not reg_ap.empty else 0.0
        # Calculamos el USD puro (Total - Bs convertido)
        f_usd_ini = (reg_ap['monto_usd'].sum() - (f_bs_ini / 60)) if not reg_ap.empty else 0.0

        # --- 1. MÉTODOS DE PAGO ---
        st.subheader("💳 Detalle de Pagos (Sistema)")
        s_ef_bs = df_v['pago_efectivo'].sum(); s_pm_bs = df_v['pago_movil'].sum()
        s_pu_bs = df_v['pago_punto'].sum(); s_ot_bs = df_v['pago_otros'].sum()
        s_ze_usd = df_v['pago_zelle'].sum(); s_di_usd = df_v['pago_divisas'].sum()
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Efec. Bs", f"{s_ef_bs:,.2f}"); c2.metric("P.Móvil", f"{s_pm_bs:,.2f}")
        c3.metric("Punto", f"{s_pu_bs:,.2f}"); c4.metric("Otros", f"{s_ot_bs:,.2f}")
        c5.metric("Zelle $", f"{s_ze_usd:,.2f}"); c6.metric("Divisa $", f"{s_di_usd:,.2f}")
        
        # --- 2. ANÁLISIS FINANCIERO (UTILIDADES) ---
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

        # --- 3. ARQUEO FÍSICO ---
        st.divider()
        st.subheader("🔍 Arqueo de Caja Real")
        col_c1, col_c2, col_c3 = st.columns(3)
        r_ef_bs = col_c1.number_input("Real en Efectivo Bs", 0.0)
        r_di_usd = col_c1.number_input("Real en Divisas $", 0.0)
        r_pm_bs = col_c2.number_input("Real en Pago Móvil Bs", 0.0)
        r_pu_bs = col_c2.number_input("Real en Punto Bs", 0.0)
        r_ze_usd = col_c3.number_input("Real en Zelle $", 0.0)
        r_ot_bs = col_c3.number_input("Real en Otros Bs", 0.0)

        # --- 4. CIERRE Y PDF ---
        st.divider()
        clave_c = st.text_input("Clave Administrativa", type="password")
        if st.button("🏮 CERRAR JORNADA Y IMPRIMIR REPORTE", use_container_width=True):
            if clave_c == CLAVE_ADMIN:
                ahora = datetime.now().strftime('%d/%m/%Y %H:%M')
                t_bs_sis = s_ef_bs + s_pm_bs + s_pu_bs + s_ot_bs
                
                reporte_html = f"""
                <div style="color:black; background:white; padding:20px; border:2px solid black; font-family:Arial;">
                    <center><h2>MEDITERRANEO EXPRESS</h2><h3>REPORTE DE CIERRE</h3></center>
                    <hr>
                    <p><b>Fecha:</b> {ahora}</p>
                    <p><b>Ingresos:</b> ${t_ingreso:,.2f} / <b>Utilidad Neta:</b> ${ganancia_neta:,.2f}</p>
                    <hr>
                    <b>CUADRE DE EFECTIVO:</b><br>
                    Bs Caja: Sist {s_ef_bs+f_bs_ini:,.2f} | Real {r_ef_bs:,.2f}<br>
                    $ Caja: Sist {s_di_usd+f_usd_ini:,.2f} | Real {r_di_usd:,.2f}
                    <hr>
                    <p style="font-size:12px; text-align:center;">Caja Cerrada - Control Interno</p>
                </div>
                """
                st.markdown(reporte_html, unsafe_allow_html=True)
                st.components.v1.html("<script>window.print();</script>", height=0)
                st.success("¡Cierre completado!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Acceso Denegado: Clave Incorrecta")
    else:
        st.info("No se encontraron movimientos para la fecha seleccionada.")

