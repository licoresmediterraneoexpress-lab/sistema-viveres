import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

# --- 2. INYECCIÓN DE ESTILOS (TUS ESTILOS ORIGINALES) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] { background-color: #ADD8E6 !important; border-right: 1px solid #90C3D4; }
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #000000 !important; font-weight: 500;
    }
    h1, h2, h3, h4, p, span, label { color: #000000 !important; }
    .stButton > button[kind="primary"] {
        background-color: #002D62 !important; color: #FFFFFF !important; border-radius: 8px !important;
        font-weight: bold; text-transform: uppercase;
    }
    .stButton > button:contains("Anular"), .stButton > button:contains("Eliminar") {
        background-color: #D32F2F !important; color: #FFFFFF !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #FFFFFF !important; color: #000000 !important; border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }
    input { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

db = create_client(URL, KEY)

# --- ESTADO DE SESIÓN ---
if 'car' not in st.session_state: st.session_state.car = []
if 'venta_finalizada' not in st.session_state: st.session_state.venta_finalizada = False

# --- 2. LÓGICA DE TURNO UNIFICADA ---
try:
    res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
    turno_activo = res_caja.data[0] if res_caja.data else None
    id_turno = turno_activo['id'] if turno_activo else None
    st.session_state.id_turno = id_turno 
except Exception:
    turno_activo = None
    id_turno = None
    st.session_state.id_turno = None

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:#002D62;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MENÚ PRINCIPAL", ["📦 Inventario", "🛒 Punto de Venta", "📜 Historial", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    if id_turno:
        st.success(f"Turno Abierto: #{id_turno}")
    else:
        st.error("Caja Cerrada")

if opcion in ["🛒 Punto de Venta", "📜 Historial", "💸 Gastos"] and not id_turno:
    st.warning("⚠️ ACCESO RESTRINGIDO. Debe abrir la caja en 'Cierre de Caja'.")
    st.stop()

# --- 4. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.markdown("<h1>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    res = db.table("inventario").select("*").order("nombre").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_inv.empty:
        busc = st.text_input("🔍 Buscar Producto", placeholder="Nombre del producto...")
        df_mostrar = df_inv[df_inv['nombre'].str.contains(busc, case=False)] if busc else df_inv
        st.subheader("📋 Existencias")
        
        @st.dialog("✏️ Modificar Producto")
        def edit_dial(prod):
            with st.form("f_edit"):
                n_nom = st.text_input("Nombre", value=prod['nombre'])
                c1, c2 = st.columns(2)
                n_stock = c1.number_input("Stock", value=float(prod['stock']))
                n_costo = c2.number_input("Costo $", value=float(prod['costo']))
                c3, c4, c5 = st.columns(3)
                n_detal = c3.number_input("Precio Detal $", value=float(prod['precio_detal']))
                n_mayor = c4.number_input("Precio Mayor $", value=float(prod['precio_mayor']))
                n_min = c5.number_input("Min. Mayor", value=int(prod['min_mayor']))
                if st.form_submit_button("GUARDAR"):
                    db.table("inventario").update({
                        "nombre": n_nom, "stock": n_stock, "costo": n_costo,
                        "precio_detal": n_detal, "precio_mayor": n_mayor, "min_mayor": n_min
                    }).eq("id", prod['id']).execute()
                    st.rerun()

        st.dataframe(df_mostrar[['nombre', 'stock', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            sel = st.selectbox("Editar", [None] + df_mostrar['nombre'].tolist())
            if sel:
                p_data = df_inv[df_inv['nombre'] == sel].iloc[0].to_dict()
                if st.button(f"Modificar {sel}"): edit_dial(p_data)
        with col_act2:
            del_sel = st.selectbox("Eliminar", [None] + df_mostrar['nombre'].tolist())
            clave = st.text_input("Clave Admin", type="password")
            if st.button("Eliminar Producto", type="primary"):
                if clave == CLAVE_ADMIN and del_sel:
                    db.table("inventario").delete().eq("nombre", del_sel).execute()
                    st.success("Eliminado"); time.sleep(1); st.rerun()

    with st.expander("➕ Añadir Nuevo Producto"):
        with st.form("new_p"):
            f1, f2 = st.columns(2)
            n_n = f1.text_input("Nombre").upper()
            n_s = f2.number_input("Stock Inicial", 0.0)
            f3, f4, f5 = st.columns(3)
            n_c = f3.number_input("Costo", 0.0)
            n_d = f4.number_input("Detal", 0.0)
            n_m = f5.number_input("Mayor", 0.0)
            n_min = st.number_input("Min. para Mayor", 1)
            if st.form_submit_button("REGISTRAR"):
                db.table("inventario").insert({"nombre": n_n, "stock": n_s, "costo": n_c, "precio_detal": n_d, "precio_mayor": n_m, "min_mayor": n_min}).execute()
                st.success("✅ Guardado"); st.rerun()

# --- 5. MÓDULO PUNTO DE VENTA ---
elif opcion == "🛒 Punto de Venta":
    id_turno = int(st.session_state.id_turno)
    st.markdown("<h1>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    tasa = st.number_input("Tasa BCV (Bs/$)", value=60.0, format="%.2f")
    
    c_izq, c_der = st.columns([1, 1.1])
    with c_izq:
        busc_v = st.text_input("🔍 Buscar...", key="pos_search")
        res_v = db.table("inventario").select("*").ilike("nombre", f"%{busc_v}%").gt("stock", 0).limit(8).execute() if busc_v else db.table("inventario").select("*").gt("stock", 0).limit(8).execute()
        for p in res_v.data:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.markdown(f"**{p['nombre']}**\n\nStock: `{int(p['stock'])}`")
                col2.markdown(f"<h4 style='color:green;'>${float(p['precio_detal']):.2f}</h4>", unsafe_allow_html=True)
                if col3.button("➕", key=f"add_{p['id']}"):
                    found = False
                    for item in st.session_state.car:
                        if item['id'] == p['id']:
                            item['cant'] += 1.0; found = True; break
                    if not found:
                        st.session_state.car.append({"id": int(p['id']), "nombre": p['nombre'], "cant": 1.0, "precio": float(p['precio_detal']), "costo": float(p['costo'])})
                    st.rerun()

    with c_der:
        total_usd = 0.0
        if not st.session_state.car: st.info("Carrito vacío")
        else:
            for i, item in enumerate(st.session_state.car):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 1.5, 0.5])
                    item['cant'] = c1.number_input(f"{item['nombre']}", min_value=0.1, value=float(item['cant']), key=f"c_{i}")
                    subt = item['cant'] * item['precio']
                    total_usd += subt
                    c2.write(f"${subt:.2f}")
                    if c3.button("❌", key=f"del_{i}"): st.session_state.car.pop(i); st.rerun()
        
        st.divider()
        st.markdown(f"### Total: `${total_usd:.2f}` / `{total_usd*tasa:,.2f} Bs`Config")
        monto_bs_cobrar = st.number_input("Total Bs Cobrar", value=float(total_usd*tasa))
        
        with st.expander("💳 PAGOS MIXTOS", expanded=True):
            p1, p2 = st.columns(2)
            d_ef_usd = p1.number_input("Efectivo $", 0.0)
            d_zelle = p1.number_input("Zelle $", 0.0)
            d_otros = p1.number_input("Otros $", 0.0)
            d_ef_bs = p2.number_input("Efectivo Bs", 0.0)
            d_pm = p2.number_input("Pago Móvil Bs", 0.0)
            d_pv = p2.number_input("Punto Bs", 0.0)
            
            total_pagado_usd = d_ef_usd + d_zelle + d_otros + ((d_ef_bs + d_pm + d_pv)/tasa)
            vuelto = total_pagado_usd - (monto_bs_cobrar/tasa)
            if vuelto >= -0.01: st.success(f"Vuelto: ${vuelto:.2f}")
            else: st.error(f"Faltante: ${abs(vuelto):.2f}")

        if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True, disabled=(vuelto < -0.01 or not st.session_state.car)):
            items_res = ""; costo_v = 0.0
            for it in st.session_state.car:
                curr = db.table("inventario").select("stock").eq("id", it['id']).execute()
                db.table("inventario").update({"stock": float(curr.data[0]['stock']) - it['cant']}).eq("id", it['id']).execute()
                items_res += f"{int(it['cant'])}x {it['nombre']}, "
                costo_v += (it['costo'] * it['cant'])
            
            payload = {
                "id_cierre": id_turno, "producto": items_res.strip(", "), "total_usd": float(total_usd),
                "monto_cobrado_bs": float(monto_bs_cobrar), "tasa_cambio": float(tasa),
                "pago_divisas": float(d_ef_usd), "pago_zelle": float(d_zelle), "pago_otros": float(d_otros),
                "pago_efectivo": float(d_ef_bs), "pago_movil": float(d_pm), "pago_punto": float(d_pv),
                "costo_venta": float(costo_v), "estado": "Finalizado", "items": st.session_state.car,
                "fecha": datetime.now().isoformat()
            }
            db.table("ventas").insert(payload).execute()
            st.balloons(); st.session_state.car = []; st.rerun()

# --- 6. MÓDULO HISTORIAL ---
elif opcion == "📜 Historial":
    st.markdown("<h1>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    res_h = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
    if res_h.data:
        df_h = pd.DataFrame(res_h.data)
        for _, fila in df_h.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
                c1.write(fila['fecha'][:16])
                c2.write(fila['producto'])
                c3.write(f"${fila['total_usd']:.2f}")
                if fila['estado'] == 'Finalizado':
                    if c4.button("🚫 Anular", key=f"an_{fila['id']}"):
                        # Revertir Stock
                        items = fila['items']
                        for it in items:
                            inv = db.table("inventario").select("stock").eq("id", it['id']).execute()
                            db.table("inventario").update({"stock": float(inv.data[0]['stock']) + it['cant']}).eq("id", it['id']).execute()
                        db.table("ventas").update({"estado": "Anulado"}).eq("id", fila['id']).execute()
                        st.rerun()
                else: c4.write("Anulada")

# --- 7. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.markdown("<h1>💸 Gastos Operativos</h1>", unsafe_allow_html=True)
    with st.form("g"):
        d = st.text_input("Descripción")
        m = st.number_input("Monto $", 0.0)
        if st.form_submit_button("REGISTRAR GASTO"):
            db.table("gastos").insert({"id_cierre": id_turno, "descripcion": d, "monto_usd": m}).execute()
            st.success("Gasto guardado")

# --- 8. CIERRE DE CAJA (OPTIMIZADO) ---
elif opcion == "📊 Cierre de Caja":
    st.markdown("<h1>📊 Cierre de Caja</h1>", unsafe_allow_html=True)
    
    if not id_turno:
        with st.form("apertura"):
            tasa_v = st.number_input("Tasa Apertura", value=60.0)
            f_bs = st.number_input("Fondo Bs", 0.0)
            f_usd = st.number_input("Fondo $", 0.0)
            if st.form_submit_button("ABRIR CAJA"):
                db.table("cierres").insert({"tasa_apertura": tasa_v, "fondo_bs": f_bs, "fondo_usd": f_usd, "estado": "abierto", "fecha_apertura": datetime.now().isoformat()}).execute()
                st.rerun()
    else:
        # Cálculos de Cierre
        res_v = db.table("ventas").select("*").eq("id_cierre", id_turno).eq("estado", "Finalizado").execute()
        df_v = pd.DataFrame(res_v.data) if res_v.data else pd.DataFrame()
        
        col1, col2, col3 = st.columns(3)
        total_f = df_v['total_usd'].sum() if not df_v.empty else 0.0
        col1.metric("Total Ventas $", f"${total_f:,.2f}")
        
        costo_t = df_v['costo_venta'].sum() if not df_v.empty else 0.0
        col2.metric("Ganancia Bruta $", f"${total_f - costo_t:,.2f}")

        # OPTIMIZACIÓN DEL VALOR DE INVENTARIO (Aquí estaba el error de peso)
        if st.button("📊 CALCULAR VALOR INVENTARIO ACTUAL"):
            with st.spinner("Calculando..."):
                inv_data = db.table("inventario").select("stock, costo").execute()
                # Usamos pandas para procesar miles de datos en milisegundos
                df_inv_val = pd.DataFrame(inv_data.data)
                df_inv_val['stock'] = pd.to_numeric(df_inv_val['stock'], errors='coerce').fillna(0)
                df_inv_val['costo'] = pd.to_numeric(df_inv_val['costo'], errors='coerce').fillna(0)
                valor_total = (df_inv_val['stock'] * df_inv_val['costo']).sum()
                col3.metric("Valor Inventario", f"${valor_total:,.2f}")

        if st.button("🔒 CERRAR TURNO DEFINITIVAMENTE"):
            db.table("cierres").update({"estado": "cerrado", "fecha_cierre": datetime.now().isoformat(), "total_ventas": float(total_f)}).eq("id", id_turno).execute()
            st.success("Cerrado"); time.sleep(1); st.rerun()
