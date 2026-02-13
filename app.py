import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

# --- 2. INYECCIÓN DE ESTILOS (TU DISEÑO ORIGINAL) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] { background-color: #ADD8E6 !important; border-right: 1px solid #90C3D4; }
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #000000 !important; font-weight: 500;
    }
    h1, h2, h3, h4, p, span, label { color: #000000 !important; }
    .stButton > button[kind="primary"] {
        background-color: #002D62 !important; color: #FFFFFF !important;
        border-radius: 8px !important; font-weight: bold; text-transform: uppercase;
    }
    .stButton > button:contains("Anular"), .stButton > button:contains("Eliminar") {
        background-color: #D32F2F !important; color: #FFFFFF !important;
    }
    input { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"
db = create_client(URL, KEY)

# --- ESTADO DE SESIÓN ---
if 'car' not in st.session_state: st.session_state.car = []
if 'id_turno' not in st.session_state: st.session_state.id_turno = None

# --- LÓGICA DE TURNO (OPTIMIZADA) ---
@st.cache_data(ttl=10) # Cache de 10 segundos para no saturar Supabase con cada clic
def obtener_turno():
    try:
        res = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except: return None

turno_activo = obtener_turno()
id_turno = turno_activo['id'] if turno_activo else None
st.session_state.id_turno = id_turno

# --- MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:#002D62;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MENÚ PRINCIPAL", ["📦 Inventario", "🛒 Punto de Venta", "📜 Historial", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    if id_turno: st.success(f"Turno Abierto: #{id_turno}")
    else: st.error("Caja Cerrada")

# Seguridad módulos
if opcion in ["🛒 Punto de Venta", "📜 Historial", "💸 Gastos"] and not id_turno:
    st.warning("⚠️ ACCESO RESTRINGIDO: Abra caja primero.")
    st.stop()

# --- MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.markdown("<h1>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    res = db.table("inventario").select("*").order("nombre").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_inv.empty:
        busc = st.text_input("🔍 Buscar Producto")
        df_mostrar = df_inv[df_inv['nombre'].str.contains(busc, case=False)] if busc else df_inv
        st.dataframe(df_mostrar[['nombre', 'stock', 'precio_detal', 'precio_mayor']], use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            sel = st.selectbox("Editar Producto", [None] + df_mostrar['nombre'].tolist())
            if sel:
                p = df_inv[df_inv['nombre'] == sel].iloc[0]
                with st.form("edit"):
                    n_stock = st.number_input("Stock", value=float(p['stock']))
                    n_detal = st.number_input("Precio $", value=float(p['precio_detal']))
                    if st.form_submit_button("GUARDAR"):
                        db.table("inventario").update({"stock": n_stock, "precio_detal": n_detal}).eq("id", p['id']).execute()
                        st.rerun()
        with col2:
            del_sel = st.selectbox("Eliminar Producto", [None] + df_mostrar['nombre'].tolist())
            pw = st.text_input("Clave Admin", type="password")
            if st.button("ELIMINAR") and pw == CLAVE_ADMIN and del_sel:
                db.table("inventario").delete().eq("nombre", del_sel).execute()
                st.rerun()

    with st.expander("➕ Añadir Nuevo"):
        with st.form("nuevo"):
            n = st.text_input("Nombre").upper()
            s = st.number_input("Stock", 0.0)
            c = st.number_input("Costo", 0.0)
            p = st.number_input("Precio", 0.0)
            if st.form_submit_button("REGISTRAR"):
                db.table("inventario").insert({"nombre":n, "stock":s, "costo":c, "precio_detal":p}).execute()
                st.rerun()

# --- PUNTO DE VENTA ---
elif opcion == "🛒 Punto de Venta":
    st.markdown("<h1>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    tasa = st.number_input("Tasa BCV", value=60.0)
    
    c1, c2 = st.columns([1, 1.2])
    with c1:
        busc_v = st.text_input("Buscar producto...")
        res_v = db.table("inventario").select("*").ilike("nombre", f"%{busc_v}%").gt("stock", 0).limit(5).execute()
        for p in res_v.data:
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{p['nombre']}** (${p['precio_detal']})")
                if col_b.button("➕", key=f"add_{p['id']}"):
                    st.session_state.car.append({"id": p['id'], "nombre": p['nombre'], "cant": 1.0, "precio": float(p['precio_detal']), "costo": float(p['costo'])})
                    st.rerun()

    with c2:
        st.subheader("Carrito")
        total = 0.0
        for i, item in enumerate(st.session_state.car):
            total += item['cant'] * item['precio']
            st.write(f"{item['nombre']} x {item['cant']} = ${item['cant']*item['precio']:.2f}")
        
        st.divider()
        st.metric("Total USD", f"${total:.2f}")
        st.metric("Total Bs", f"{total*tasa:,.2f} Bs")

        if st.button("🚀 FINALIZAR VENTA") and st.session_state.car:
            for it in st.session_state.car:
                # Actualiza stock
                res_s = db.table("inventario").select("stock").eq("id", it['id']).execute()
                new_s = float(res_s.data[0]['stock']) - it['cant']
                db.table("inventario").update({"stock": new_s}).eq("id", it['id']).execute()
            
            # Registrar venta
            db.table("ventas").insert({
                "id_cierre": id_turno, "producto": "Venta Multi", "total_usd": total, 
                "monto_cobrado_bs": total*tasa, "tasa_cambio": tasa, "estado": "Finalizado",
                "fecha": datetime.now().isoformat()
            }).execute()
            st.session_state.car = []
            st.success("Venta Guardada")
            time.sleep(1)
            st.rerun()

# --- HISTORIAL ---
elif opcion == "📜 Historial":
    st.markdown("<h1>📜 Historial</h1>", unsafe_allow_html=True)
    res_h = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
    if res_h.data:
        df_h = pd.DataFrame(res_h.data)
        st.table(df_h[['id', 'total_usd', 'monto_cobrado_bs', 'estado']])
        if st.button("Anular Última Venta"):
            last_id = res_h.data[0]['id']
            db.table("ventas").update({"estado": "Anulado"}).eq("id", last_id).execute()
            st.rerun()

# --- GASTOS ---
elif opcion == "💸 Gastos":
    st.markdown("<h1>💸 Gastos</h1>", unsafe_allow_html=True)
    with st.form("gastos"):
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto $", 0.0)
        if st.form_submit_button("GUARDAR"):
            db.table("gastos").insert({"id_cierre": id_turno, "descripcion": desc, "monto_usd": monto}).execute()
            st.success("Gasto registrado")

# --- CONFIGURACIÓN DE ESTILO ---
st.markdown(f"""
    <style>
    /* Estilo de botones */
    div.stButton > button {{
        background-color: #002D62 !important;
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        width: 100%;
    }}
    /* Color de letras global */
    h1, h2, h3, p, label, .stMetric {{
        color: black !important;
    }}
    /* Contenedores de cuadre */
    .cuadre-positivo {{ padding:15px; background-color:#d4edda; color:#155724; border-radius:10px; border:2px solid #c3e6cb; margin-bottom:10px; }}
    .cuadre-negativo {{ padding:15px; background-color:#f8d7da; color:#721c24; border-radius:10px; border:2px solid #f5c6cb; margin-bottom:10px; }}
    </style>
    """, unsafe_allow_html=True)

def modulo_cierre_caja(db):
    st.markdown("<h1 style='text-align: center;'>📊 Gestión de Caja y Auditoría</h1>", unsafe_allow_html=True)

    # --- 1. LÓGICA DE APERTURA ---
    if 'id_turno' not in st.session_state or st.session_state.id_turno is None:
        with st.container(border=True):
            st.subheader("🔓 Apertura de Nuevo Turno")
            col1, col2, col3 = st.columns(3)
            
            tasa = col1.number_input("Tasa de Cambio (Bs/$)", min_value=1.0, value=60.0, format="%.2f")
            f_bs = col2.number_input("Fondo Inicial Bs", min_value=0.0, step=100.0)
            f_usd = col3.number_input("Fondo Inicial USD", min_value=0.0, step=10.0)

            if st.button("🚀 INICIAR JORNADA"):
                try:
                    data_apertura = {
                        "fecha_apertura": datetime.now().isoformat(),
                        "tasa_cambio": float(tasa),
                        "fondo_bs": float(f_bs),
                        "fondo_usd": float(f_usd),
                        "estado": "abierto"
                    }
                    res = db.table("cierres").insert(data_apertura).execute()
                    
                    if res.data:
                        st.session_state.id_turno = res.data[0]['id']
                        st.success(f"✅ Turno #{st.session_state.id_turno} abierto.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al abrir turno: {e}")
        return

    # --- SI HAY TURNO ACTIVO ---
    id_actual = st.session_state.id_turno

    # --- 2. PRE-CIERRE (CÁLCULOS DINÁMICOS) ---
    with st.container(border=True):
        st.subheader(f"🔍 Auditoría de Turno Activo: #{id_actual}")
        
        # Consultas optimizadas
        res_v = db.table("ventas").select("total_usd").eq("id_cierre", id_actual).eq("estado", "Finalizado").execute()
        total_ventas = sum(item.get('total_usd', 0) for item in res_v.data) if res_v.data else 0

        res_g = db.table("gastos").select("monto_usd").eq("id_cierre", id_actual).execute()
        total_gastos = sum(item.get('monto_usd', 0) for item in res_g.data) if res_g.data else 0

        # Recuperar fondo inicial
        res_c = db.table("cierres").select("fondo_usd", "tasa_cambio").eq("id", id_actual).single().execute()
        fondo_inicial = res_c.data.get('fondo_usd', 0)
        tasa_actual = res_c.data.get('tasa_cambio', 1)

        esperado_sistema = (total_ventas + fondo_inicial) - total_gastos

        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas (USD)", f"${total_ventas:,.2f}")
        c2.metric("Gastos (USD)", f"-${total_gastos:,.2f}")
        c3.metric("Debe haber en Caja", f"${esperado_sistema:,.2f}")

        # Auditoría de Inventario
        st.divider()
        if st.button("📦 AUDITAR VALOR DE INVENTARIO"):
            with st.spinner("Calculando valorización..."):
                inv_res = db.table("inventario").select("stock, costo").execute()
                valor_inv = sum(float(i.get('stock', 0) or 0) * float(i.get('costo', 0) or 0) for i in inv_res.data)
                st.info(f"💰 Valor total del inventario en almacén: **${valor_inv:,.2f} USD**")

    # --- 3. CÁLCULO DE DIFERENCIAS (CUADRE) ---
    with st.container(border=True):
        st.subheader("💵 Cuadre Físico")
        fisico_usd = st.number_input("Monto contado físicamente en caja (USD)", min_value=0.0, step=1.0)
        diferencia = fisico_usd - esperado_sistema

        if diferencia == 0:
            st.markdown('<div class="cuadre-positivo">✅ CAJA CUADRADA: El monto físico coincide con el sistema.</div>', unsafe_allow_html=True)
        elif diferencia > 0:
            st.markdown(f'<div class="cuadre-positivo">🟢 SOBRANTE: +${diferencia:,.2f} USD</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cuadre-negativo">🔴 FALTANTE: -${abs(diferencia):,.2f} USD</div>', unsafe_allow_html=True)

    # --- 4. CIERRE DEFINITIVO ---
    with st.container(border=True):
        st.subheader("🔐 Finalizar Turno")
        st.warning("Esta acción bloqueará todas las ventas y gastos de este turno.")
        
        confirmar = st.checkbox("He verificado los montos y confirmo el cierre de caja.")
        
        if st.button("🔒 CERRAR CAJA DEFINITIVAMENTE", disabled=not confirmar):
            try:
                data_cierre = {
                    "fecha_cierre": datetime.now().isoformat(),
                    "total_ventas": float(total_ventas),
                    "total_gastos": float(total_gastos),
                    "saldo_final_real": float(fisico_usd),
                    "diferencia": float(diferencia),
                    "estado": "cerrado"
                }
                db.table("cierres").update(data_cierre).eq("id", id_actual).execute()
                
                # Limpiar estado y reiniciar
                st.session_state.id_turno = None
                st.success("Caja cerrada correctamente. Redirigiendo...")
                st.rerun()
            except Exception as e:
                st.error(f"Error al procesar el cierre: {e}")
