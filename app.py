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

# --- 3. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Gestión de Inventario y Mercancía")
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_inv.empty:
        # Alertas de Stock Bajo
        bajo_stock = df_inv[df_inv['stock'] <= 5]
        if not bajo_stock.empty:
            st.warning(f"⚠️ Tienes {len(bajo_stock)} productos por agotarse.")
            with st.expander("Ver lista de reposición"):
                st.table(bajo_stock[['nombre', 'stock']])

        # Valorización de la mercancía
        df_inv['valor_total'] = df_inv['stock'] * df_inv['costo']
        st.metric("Inversión Total en Mercancía", f"${df_inv['valor_total'].sum():,.2f}")
        
        # Buscador Inteligente de Stock
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

# --- 4. MÓDULO VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        # BUSCADOR INTELIGENTE EN TIEMPO REAL
        busc = st.text_input("🔍 Buscar producto...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        col1, col2 = st.columns([3, 1])
        item_sel = col1.selectbox("Seleccionar Producto", df_f['nombre'])
        cant_sel = col2.number_input("Cantidad", 1)
        
        if st.button("➕ AÑADIR AL CARRITO"):
            p = df_p[df_p['nombre'] == item_sel].iloc[0]
            if p['stock'] >= cant_sel:
                precio = float(p['precio_mayor']) if cant_sel >= p['min_mayor'] else float(p['precio_detal'])
                st.session_state.car.append({
                    "p": item_sel, "c": cant_sel, "u": precio, 
                    "t": round(precio * cant_sel, 2), "costo_u": float(p['costo'])
                })
                st.rerun()
            else:
                st.error("No hay suficiente stock disponible.")

    if st.session_state.car:
        st.divider()
        st.subheader("📋 Resumen del Carrito")
        sub_total_usd = sum(x['t'] for x in st.session_state.car)
        for x in st.session_state.car:
            st.text(f"• {x['p']} (x{x['c']}) - ${x['t']:.2f}")
        
        total_bs_sug = sub_total_usd * tasa
        st.markdown(f"### Total Sugerido: **{total_bs_sug:,.2f} Bs.** (${sub_total_usd:,.2f})")
        
        # AJUSTE DE MONTO FINAL (REDONDEO / PROPINA)
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
                # La propina es el sobrante del redondeo convertido a USD
                propina_usd = (total_cobrado_bs / tasa) - sub_total_usd
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": ef, "pago_punto": pu, "pago_movil": pm, "pago_zelle": ze, 
                        "pago_otros": ot, "pago_divisas": di, "costo_venta": x['costo_u'] * x['c'],
                        "propina": propina_usd / len(st.session_state.car), "fecha": datetime.now().isoformat()
                    }).execute()
                    # Actualización de Stock
                    stk_act = df_p[df_p['nombre'] == x['p']].iloc[0]['stock']
                    db.table("inventario").update({"stock": int(stk_act - x['c'])}).eq("nombre", x['p']).execute()
                st.balloons()
                st.success("VENTA REGISTRADA CON ÉXITO")
                st.session_state.car = []
                st.rerun()
            except Exception as e: st.error(f"Error técnico: {e}")

# --- 5. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos Operativos")
    with st.form("form_g"):
        desc = st.text_input("Descripción del Gasto")
        monto = st.number_input("Monto en Dólares ($)", 0.0)
        if st.form_submit_button("💾 Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto registrado y restado de la utilidad.")

# --- 6. CIERRE DE CAJA Y UTILIDADES ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Cierre de Caja y Balance Diario")
    f_rep = st.date_input("Consultar Fecha", date.today())
    
    v_data = db.table("ventas").select("*").gte("fecha", f_rep.isoformat()).execute()
    g_data = db.table("gastos").select("*").gte("fecha", f_rep.isoformat()).execute()
    
    if v_data.data:
        df_v = pd.DataFrame(v_data.data)
        df_g = pd.DataFrame(g_data.data) if g_data.data else pd.DataFrame()
        
        st.subheader("💳 Ingresos por Método de Pago")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Efectivo Bs", f"{df_v['pago_efectivo'].sum():,.2f}")
        c2.metric("Pago Móvil Bs", f"{df_v['pago_movil'].sum():,.2f}")
        c3.metric("Punto Bs", f"{df_v['pago_punto'].sum():,.2f}")
        c4.metric("Zelle $", f"${df_v['pago_zelle'].sum():,.2f}")
        c5.metric("Divisas $", f"${df_v['pago_divisas'].sum():,.2f}")
        
        st.divider()
        # Cálculos de Utilidad
        ing_total = df_v['total_usd'].sum()
        cos_total = df_v['costo_venta'].sum()
        gas_total = df_g['monto_usd'].sum() if not df_g.empty else 0
        propina_total = df_v['propina'].sum()
        uti_neta = ing_total - cos_total - gas_total

        st.subheader("📈 Balance General")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("INGRESOS TOTALES", f"${ing_total:,.2f}")
        k2.metric("COSTO MERCANCÍA", f"${cos_total:,.2f}")
        k3.metric("GASTOS TOTALES", f"${gas_total:,.2f}")
        k4.metric("UTILIDAD NETA", f"${uti_neta:,.2f}", delta=f"{((uti_neta/ing_total)*100 if ing_total > 0 else 0):.1f}%")

        st.info(f"💰 **Sobrante por Redondeo (Propina):** ${propina_total:,.2f} USD (Diferencia de tasa/redondeo)")
        
        st.write("### Detalle de Ventas")
        st.dataframe(df_v[['fecha', 'producto', 'cantidad', 'total_usd', 'propina']], use_container_width=True)
    else:
        st.info("No hay registros para la fecha seleccionada.")
