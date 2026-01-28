import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo POS Premium", layout="wide")

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

# --- 3. MÓDULO INVENTARIO (CON EXPORTACIÓN A EXCEL) ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_inv.empty:
        # Métricas principales
        df_inv['valor_total'] = df_inv['stock'] * df_inv['costo']
        c1, c2 = st.columns(2)
        c1.metric("Inversión Total", f"${df_inv['valor_total'].sum():,.2f}")
        c2.metric("Productos Registrados", len(df_inv))

        # --- BOTÓN DE EXPORTAR A EXCEL ---
        st.divider()
        try:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Ordenamos las columnas para que el Excel sea legible
                columnas_excel = ['nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']
                df_inv[columnas_excel].to_excel(writer, index=False, sheet_name='Inventario')
            
            st.download_button(
                label="📥 Descargar Inventario en Excel",
                data=buffer.getvalue(),
                file_name=f"Inventario_Mediterraneo_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al generar Excel: {e}")
        
        st.divider()

        # Buscador y Tabla
        bus_inv = st.text_input("🔍 Buscar en inventario...")
        df_m = df_inv[df_inv['nombre'].str.contains(bus_inv, case=False)] if bus_inv else df_inv
        st.dataframe(df_m[['nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)

    # Registro y Edición
    with st.expander("⚙️ Agregar o Modificar Producto (Admin)"):
        if st.text_input("Clave de Seguridad", type="password") == CLAVE_ADMIN:
            with st.form("form_inv"):
                c1, c2, c3 = st.columns(3)
                n_nom = c1.text_input("Nombre")
                n_stk = c1.number_input("Stock", 0)
                n_cos = c2.number_input("Costo $", 0.0)
                n_pde = c2.number_input("Precio Detal $", 0.0)
                n_pma = c3.number_input("Precio Mayor $", 0.0)
                n_mma = c3.number_input("Mínimo para Mayor", 12)
                if st.form_submit_button("💾 Guardar Producto"):
                    data = {"nombre": n_nom, "stock": n_stk, "costo": n_cos, "precio_detal": n_pde, "precio_mayor": n_pma, "min_mayor": n_mma}
                    db.table("inventario").upsert(data, on_conflict="nombre").execute()
                    st.success("Inventario Actualizado")
                    st.rerun()
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

# --- 6. CIERRE DE CAJA (ACTUALIZADO CON PAGO_OTROS) ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Cierre de Caja y Balance Diario")
    f_rep = st.date_input("Fecha a Consultar", date.today())
    
    # Consultas a Supabase
    v = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v.data:
        df_v = pd.DataFrame(v.data)
        df_g = pd.DataFrame(g.data) if g.data else pd.DataFrame()
        
        # 1. DESGLOSE POR MÉTODO DE PAGO (Aquí incluimos pago_otros)
        st.subheader("💳 Detalle por Método de Pago")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        
        c1.metric("Efectivo Bs", f"{df_v['pago_efectivo'].sum():,.2f}")
        c2.metric("P. Móvil Bs", f"{df_v['pago_movil'].sum():,.2f}")
        c3.metric("Punto Bs", f"{df_v['pago_punto'].sum():,.2f}")
        c4.metric("Otros Bs", f"{df_v['pago_otros'].sum():,.2f}") # <-- SE AGREGA ESTE DATO
        c5.metric("Zelle $", f"${df_v['pago_zelle'].sum():,.2f}")
        c6.metric("Divisas $", f"${df_v['pago_divisas'].sum():,.2f}")
        
        st.divider()
        
        # 2. CÁLCULO DE TOTALES Y UTILIDADES
        t_usd = df_v['total_usd'].sum()
        t_cos = df_v['costo_venta'].sum()
        t_gas = df_g['monto_usd'].sum() if not df_g.empty else 0
        t_pro = df_v['propina'].sum()
        
        # Balance General
        st.subheader("📈 Balance de Ganancias")
        k1, k2, k3, k4 = st.columns(4)
        
        k1.metric("VENTAS TOTALES", f"${t_usd:,.2f}")
        k2.metric("COSTO MERCANCÍA", f"${t_cos:,.2f}")
        k3.metric("GASTOS TOTALES", f"${t_gas:,.2f}")
        k4.metric("UTILIDAD NETA", f"${t_usd - t_cos - t_gas:,.2f}")

        st.info(f"💰 **Sobrante Redondeo (Propina):** ${t_pro:,.2f}")
        
        # 3. TABLA DETALLADA
        with st.expander("Ver lista de ventas del día"):
            st.dataframe(df_v[['fecha', 'producto', 'cantidad', 'total_usd']], use_container_width=True)
            
    else:
        st.info("No hay registros de ventas para esta fecha.")











