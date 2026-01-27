import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS Premium", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

# Estado del carrito
if 'car' not in st.session_state: st.session_state.car = []

# Estilos Pro
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {background-color: #FF8C00; color: white; border-radius: 8px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 2. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MÓDULOS", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Reporte de Utilidades"])
    st.divider()
    if st.button("🗑️ Vaciar Carrito Actual"):
        st.session_state.car = []; st.rerun()

# --- 3. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario")
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_inv.empty:
        # Alertas de Stock Bajo
        bajo_stock = df_inv[df_inv['stock'] <= 5]
        if not bajo_stock.empty:
            st.warning(f"⚠️ ¡Atención! Tienes {len(bajo_stock)} productos con stock bajo (5 o menos).")
            with st.expander("Ver productos a reponer"):
                st.table(bajo_stock[['nombre', 'stock']])

        # Valorización
        df_inv['valor_total'] = df_inv['stock'] * df_inv['costo']
        st.metric("Inversión Total en Mercancía", f"${df_inv['valor_total'].sum():,.2f}")
        
        # Buscador y tabla
        bus_inv = st.text_input("🔍 Buscar en inventario...")
        df_m = df_inv[df_inv['nombre'].str.contains(bus_inv, case=False)] if bus_inv else df_inv
        st.dataframe(df_m[['nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)

    # Registro y edición (Solo Admin)
    with st.expander("⚙️ Agregar o Modificar Producto (Clave Requerida)"):
        pass_adm = st.text_input("Clave Admin", type="password")
        if pass_adm == CLAVE_ADMIN:
            with st.form("form_inv"):
                c1, c2, c3 = st.columns(3)
                n_nom = c1.text_input("Nombre del Producto")
                n_stk = c1.number_input("Stock", 0)
                n_cos = c2.number_input("Costo $", 0.0)
                n_pde = c2.number_input("Precio Detal $", 0.0)
                n_pma = c3.number_input("Precio Mayor $", 0.0)
                n_mma = c3.number_input("Mínimo Mayorista", 12)
                if st.form_submit_button("Guardar Producto"):
                    # Verificar si existe para actualizar o insertar
                    existente = df_inv[df_inv['nombre'] == n_nom] if not df_inv.empty else pd.DataFrame()
                    data = {"nombre": n_nom, "stock": n_stk, "costo": n_cos, "precio_detal": n_pde, "precio_mayor": n_pma, "min_mayor": n_mma}
                    if not existente.empty:
                        db.table("inventario").update(data).eq("nombre", n_nom).execute()
                    else:
                        db.table("inventario").insert(data).execute()
                    st.success("¡Base de datos actualizada!"); st.rerun()

elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        # BUSCADOR INTELIGENTE
        busc = st.text_input("🔍 Escribe para buscar producto...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        c1, c2 = st.columns([3, 1])
        ps = c1.selectbox("Producto", df_f['nombre'])
        cs = c2.number_input("Cantidad", 1)
        
        if st.button("➕ AÑADIR AL CARRITO"):
            p = df_p[df_p['nombre'] == ps].iloc[0]
            precio = float(p['precio_mayor']) if cs >= p['min_mayor'] else float(p['precio_detal'])
            st.session_state.car.append({
                "p": ps, "c": cs, "u": precio, 
                "t": round(precio*cs, 2), "costo_u": float(p['costo'])
            })
            st.rerun()

    if st.session_state.car:
        st.divider()
        sub_total_usd = sum(x['t'] for x in st.session_state.car)
        total_bs_sug = sub_total_usd * tasa
        st.write(f"### Total sugerido: **{total_bs_sug:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        # Ajuste de monto final (Propina/Redondeo)
        total_cobrado_bs = st.number_input("MONTO FINAL A COBRAR (Bs.)", value=float(total_bs_sug))
        
        st.write("#### 💳 Registro de Pagos Mixtos")
        c1, c2, c3 = st.columns(3)
        ef = c1.number_input("Efectivo Bs", 0.0); pm = c1.number_input("Pago Móvil Bs", 0.0)
        pu = c2.number_input("Punto Bs", 0.0); ot = c2.number_input("Otros Bs", 0.0)
        ze = c3.number_input("Zelle $", 0.0); di = c3.number_input("Divisas $", 0.0)
        
        pago_total_bs = ef + pm + pu + ot + ((ze + di) * tasa)
        diff = total_cobrado_bs - pago_total_bs
        
        if diff > 0.1: st.warning(f"Faltan cobrar: {diff:,.2f} Bs.")
        elif diff < -0.1: st.success(f"DAR VUELTO: {abs(diff):,.2f} Bs.")

        if st.button("🚀 FINALIZAR VENTA"):
            try:
                # La propina es la diferencia entre lo que marcaba el carrito y lo que cobraste
                propina_usd = (total_cobrado_bs / tasa) - sub_total_usd
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, 
                        "pago_otros": ot, "pago_divisas": di, "costo_venta": x['costo_u'] * x['c'],
                        "propina": propina_usd / len(st.session_state.car), "fecha": datetime.now().isoformat()
                    }).execute()
                    # Actualizar stock
                    stk = df_p[df_p['nombre'] == x['p']].iloc[0]['stock']
                    db.table("inventario").update({"stock": int(stk - x['c'])}).eq("nombre", x['p']).execute()
                st.balloons(); st.session_state.car = []; st.rerun()
            except Exception as e: st.error(f"Error: {e}")
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Resumen y Cierre de Caja")
    fecha_sel = st.date_input("Día a consultar", date.today())
    
    # Cargar ventas y gastos
    res_v = db.table("ventas").select("*").gte("fecha", fecha_sel.isoformat()).execute()
    res_g = db.table("gastos").select("*").gte("fecha", fecha_sel.isoformat()).execute()
    
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        df_g = pd.DataFrame(res_g.data) if res_g.data else pd.DataFrame()

        # 1. Desglose de ingresos
        st.subheader("💰 Ingresos por Método")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Efectivo Bs", f"{df_v['pago_efectivo'].sum():,.2f}")
        c2.metric("P. Móvil Bs", f"{df_v['pago_movil'].sum():,.2f}")
        c3.metric("Punto Bs", f"{df_v['pago_punto'].sum():,.2f}")
        c4.metric("Zelle $", f"{df_v['pago_zelle'].sum():,.2f}")
        c5.metric("Divisas $", f"{df_v['pago_divisas'].sum():,.2f}")

        # 2. Utilidad
        st.divider()
        ingreso_total = df_v['total_usd'].sum()
        costo_total = df_v['costo_venta'].sum()
        gastos_total = df_g['monto_usd'].sum() if not df_g.empty else 0
        utilidad_neta = ingreso_total - costo_total - gastos_total
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 📈 Utilidades")
            st.metric("Utilidad Bruta", f"${ingreso_total:,.2f}")
            st.metric("Utilidad Neta (Real)", f"${utilidad_neta:,.2f}", delta=f"${utilidad_neta:,.2f}")
        with col2:
            st.write("### 💸 Gastos y Propinas")
            st.write(f"**Gastos del día:** ${gastos_total:,.2f}")
            st.write(f"**Acumulado Propinas (Redondeo):** ${df_v['propina'].sum():,.2f}")
    else:
        st.info("No hay ventas registradas en esta fecha.")
# --- 5. REPORTES ---
elif opcion == "📊 Reporte de Utilidades":
    st.header("📊 Resultado Financiero")
    f_rep = st.date_input("Consultar Fecha", date.today())
    v_data = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g_data = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v_data.data:
        df_v = pd.DataFrame(v_data.data)
        df_g = pd.DataFrame(g_data.data) if g_data.data else pd.DataFrame()
        
        bruta = df_v['total_usd'].sum()
        costos = df_v['costo_venta'].sum()
        gastos = df_g['monto_usd'].sum() if not df_g.empty else 0
        propina = df_v['propina'].sum()
        neta = bruta - costos - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingresos Brutos", f"${bruta:,.2f}")
        c2.metric("Costo de Ventas", f"${costos:,.2f}")
        c3.metric("Gastos Totales", f"${gastos:,.2f}")
        c4.metric("UTILIDAD NETA", f"${neta:,.2f}", delta=f"${neta:,.2f}")
        
        st.info(f"💰 **Sobrante por Redondeo (Propina):** ${propina:,.2f}")
        st.write("### Detalle de Transacciones")
        st.dataframe(df_v[['fecha', 'producto', 'cantidad', 'total_usd', 'propina']], use_container_width=True)

