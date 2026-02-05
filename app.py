import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Mediterraneo Express Pro", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# --- 2. GESTIÓN DE ESTADO Y TURNO (REGLA DE ORO) ---
if 'id_turno' not in st.session_state:
    st.session_state.id_turno = None

try:
    res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
    if res_caja.data:
        st.session_state.id_turno = int(res_caja.data[0]['id'])
        st.session_state.tasa_dia = float(res_caja.data[0]['tasa_apertura'])
    else:
        st.session_state.id_turno = None
except Exception:
    st.error("Error al sincronizar turno activo.")

# Estilos
st.markdown("""
<style>
    .stApp {background-color: #FFFFFF;}
    [data-testid='stSidebar'] {background-color: #0041C2;}
    .stButton>button {border-radius: 8px; font-weight: bold;}
    .stMetric {background-color: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee;}
</style>
""", unsafe_allow_html=True)

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    if st.session_state.id_turno:
        st.success(f"Turno Activo: #{st.session_state.id_turno}")
    else:
        st.warning("Caja Cerrada")
    
    opcion = st.radio("MENÚ PRINCIPAL", 
        ["📦 Inventario", "🛒 Venta Rápida", "📜 Historial de Ventas", "💸 Gastos", "📊 Cierre de Caja"])

# --- 4. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Control de Inventario")
    try:
        res = db.table("inventario").select("*").execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        if not df_inv.empty:
            busqueda = st.text_input("🔍 Buscar producto...", key="inv_search")
            df_f = df_inv[df_inv['nombre'].str.contains(busqueda, case=False)] if busqueda else df_inv
            
            st.dataframe(df_f[['nombre', 'stock', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)
            
            with st.expander("➕ Registrar Nuevo Producto"):
                with st.form("nuevo_p"):
                    n1, n2 = st.columns(2)
                    nom = n1.text_input("Nombre").upper()
                    stk = n2.number_input("Stock", min_value=0)
                    p1, p2, p3 = st.columns(3)
                    cost = p1.number_input("Costo $")
                    det = p2.number_input("Precio Detal $")
                    min_m = p3.number_input("Min Mayor", value=1)
                    if st.form_submit_button("Guardar"):
                        db.table("inventario").insert({
                            "nombre": nom, "stock": int(stk), "costo": float(cost), 
                            "precio_detal": float(det), "min_mayor": int(min_m)
                        }).execute()
                        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- 5. MÓDULO VENTA RÁPIDA ---
elif opcion == "🛒 Venta Rápida":
    if not st.session_state.id_turno:
        st.error("Debe abrir un turno en 'Cierre de Caja' primero."); st.stop()

    if 'car' not in st.session_state: st.session_state.car = []
    
    col_i, col_d = st.columns([1.2, 1])
    
    with col_i:
        busc = st.text_input("🔍 Buscar Producto", key="venta_busc")
        if busc:
            res_p = db.table("inventario").select("*").ilike("nombre", f"%{busc}%").gt("stock", 0).execute()
            for p in res_p.data:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{p['nombre']}** - Stock: {p['stock']}")
                    if c2.button("Añadir", key=f"add_{p['id']}"):
                        st.session_state.car.append({"id": p['id'], "nombre": p['nombre'], "cant": 1, "precio": float(p['precio_detal']), "costo": float(p['costo'])})
                        st.rerun()

    with col_d:
        st.subheader("🛒 Carrito")
        total_usd = 0.0
        for i, item in enumerate(st.session_state.car):
            with st.container(border=True):
                r1, r2, r3 = st.columns([2, 1, 0.5])
                r1.write(item['nombre'])
                item['cant'] = r2.number_input("Cant", value=item['cant'], min_value=1, key=f"c_{i}")
                total_usd += item['cant'] * item['precio']
                if r3.button("🗑️", key=f"del_{i}"):
                    st.session_state.car.pop(i); st.rerun()
        
        tasa = st.session_state.tasa_dia
        st.metric("Total a Pagar", f"${total_usd:,.2f} / {total_usd*tasa:,.2f} Bs")
        
        with st.expander("💳 Registrar Pago"):
            p_ef = st.number_input("Efectivo $", 0.0)
            p_bs = st.number_input("Pago Móvil / Punto Bs", 0.0)
            
            if st.button("🚀 FINALIZAR VENTA"):
                try:
                    ts_id = int(datetime.now().timestamp())
                    items_json = [{"id": x['id'], "nombre": x['nombre'], "cantidad": x['cant'], "precio_u": x['precio']} for x in st.session_state.car]
                    
                    venta_data = {
                        "id_cierre": int(st.session_state.id_turno),
                        "fecha": datetime.now().isoformat(),
                        "producto": f"Venta {len(items_json)} items",
                        "cantidad": int(sum(x['cant'] for x in st.session_state.car)),
                        "total_usd": float(round(total_usd, 2)),
                        "tasa_cambio": float(tasa),
                        "pago_efectivo": float(p_bs),
                        "pago_divisas": float(p_ef),
                        "costo_venta": float(sum(x['cant']*x['costo'] for x in st.session_state.car)),
                        "items": items_json,
                        "estado": "Finalizado",
                        "id_transaccion": ts_id,
                        "monto_cobrado_bs": float(round(total_usd * tasa, 2))
                    }
                    
                    db.table("ventas").insert(venta_data).execute()
                    # Descontar Stock
                    for x in st.session_state.car:
                        db.rpc("decrement_stock", {"row_id": x['id'], "amount": x['cant']}).execute() # O update normal
                    
                    st.session_state.car = []
                    st.success("Venta Guardada")
                    time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- 6. MÓDULO HISTORIAL (SINCRONIZADO Y CERRADO) ---
elif opcion == "📜 Historial de Ventas":
    st.header("📊 Historial del Turno")
    try:
        res = db.table("ventas").select("*").eq("id_cierre", int(st.session_state.id_turno)).order("fecha", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            busc = st.text_input("🔍 Filtrar historial...")
            if busc: df = df[df.astype(str).apply(lambda x: x.str.contains(busc, case=False)).any(axis=1)]

            # Tabla estilo Excel
            for _, fila in df.iterrows():
                es_anulada = fila['estado'] == 'Anulado'
                col_h = st.columns([1, 2, 1, 1, 1, 1])
                col_h[0].write(f"#{fila['id']}")
                col_h[1].write(fila['producto'])
                col_h[2].write(f"{fila['total_usd']}$")
                col_h[3].write(f"{fila['monto_cobrado_bs']} Bs")
                col_h[4].write(fila['estado'])
                
                if not es_anulada:
                    if col_h[5].button("🚫", key=f"anul_{fila['id']}"):
                        # Lógica de Reversión
                        for item in fila['items']:
                            res_inv = db.table("inventario").select("stock").eq("id", item['id']).execute()
                            if res_inv.data:
                                nuevo_stk = float(res_inv.data[0]['stock']) + float(item['cantidad'])
                                db.table("inventario").update({"stock": nuevo_stk}).eq("id", item['id']).execute()
                        db.table("ventas").update({"estado": "Anulado"}).eq("id", int(fila['id'])).execute()
                        st.rerun()
            
            # Métricas
            df_a = df[df['estado'] != 'Anulado']
            m1, m2 = st.columns(2)
            m1.metric("Total Turno $", f"{df_a['total_usd'].sum():,.2f}")
            m2.metric("Ventas Activas", len(df_a))
    except Exception as e: st.error(f"Error: {e}")

# --- 7. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos del Turno")
    with st.form("g"):
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto $", 0.0)
        if st.form_submit_button("Registrar"):
            db.table("gastos").insert({
                "descripcion": desc, "monto_usd": float(monto), 
                "id_cierre": int(st.session_state.id_turno), "fecha": datetime.now().isoformat()
            }).execute()
            st.success("Gasto registrado")

# --- 8. MÓDULO CIERRE DE CAJA ---
elif opcion == "📊 Cierre de Caja":
    st.header("📊 Control de Caja")
    
    if not st.session_state.id_turno:
        with st.form("apertura"):
            st.subheader("Apertura de Turno")
            tasa = st.number_input("Tasa de Cambio Bs/$", value=60.0)
            fondo = st.number_input("Fondo de Caja $", value=0.0)
            if st.form_submit_button("Abrir Turno"):
                db.table("cierres").insert({
                    "tasa_apertura": float(tasa), "monto_apertura": float(fondo), 
                    "estado": "abierto", "fecha_apertura": datetime.now().isoformat()
                }).execute()
                st.rerun()
    else:
        # Cierre
        res_v = db.table("ventas").select("total_usd, costo_venta").eq("id_cierre", st.session_state.id_turno).eq("estado", "Finalizado").execute()
        res_g = db.table("gastos").select("monto_usd").eq("id_cierre", st.session_state.id_turno).execute()
        
        ventas_t = sum(x['total_usd'] for x in res_v.data)
        gastos_t = sum(x['monto_usd'] for x in res_g.data)
        
        st.metric("Ventas Totales", f"${ventas_t:,.2f}")
        st.metric("Gastos Totales", f"${gastos_t:,.2f}")
        st.metric("Balance Neto", f"${ventas_t - gastos_t:,.2f}")
        
        if st.button("🔴 CERRAR TURNO ACTUAL", type="primary"):
            db.table("cierres").update({
                "estado": "cerrado", "fecha_cierre": datetime.now().isoformat(),
                "total_ventas": float(ventas_t)
            }).eq("id", st.session_state.id_turno).execute()
            st.session_state.id_turno = None
            st.rerun()
