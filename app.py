import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mediterraneo POS", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db(): return create_client(URL, KEY)
db = init_db()

# Inicialización de estados
if 'car' not in st.session_state: st.session_state.car = []
if 'pdf_b' not in st.session_state: st.session_state.pdf_b = None

# --- FUNCIONES ---
def crear_ticket(carrito, total_bs, total_usd, tasa, propina_usd):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "MEDITERRANEO EXPRESS", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    # Tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(80, 7, "Producto", 1, 0, 'C', 1)
    pdf.cell(20, 7, "Cant", 1, 0, 'C', 1)
    pdf.cell(45, 7, "P. Unit $", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Total $", 1, 1, 'C', 1)
    for i in carrito:
        pdf.cell(80, 7, str(i['p'])[:30], 1)
        pdf.cell(20, 7, str(i['c']), 1, 0, 'C')
        pdf.cell(45, 7, f"{i['u']:.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"{i['t']:.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.cell(190, 7, f"TOTAL BS: {total_bs:,.2f}", ln=True, align='R')
    pdf.cell(190, 7, f"TOTAL USD: {(total_usd + propina_usd):,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFAZ ---
with st.sidebar:
    st.title("🚢 MEDITERRANEO")
    opcion = st.radio("MENÚ", ["📦 Inventario", "🛒 Venta Rápida", "💸 Gastos", "📊 Reportes"])
    if st.button("🗑️ Limpiar Todo"):
        st.session_state.car = []
        st.session_state.pdf_b = None
        st.rerun()

# --- MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.header("📦 Inventario y Mercancía")
    res = db.table("inventario").select("*").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_inv.empty:
        total_inv = (df_inv['stock'] * df_inv['costo']).sum()
        st.metric("Valor Total de Mercancía", f"${total_inv:,.2f}")
        
        busq = st.text_input("🔍 Buscador rápido de stock...")
        df_m = df_inv[df_inv['nombre'].str.contains(busq, case=False)] if busq else df_inv
        st.dataframe(df_m, use_container_width=True, hide_index=True)

    with st.expander("⚙️ Agregar o Modificar Producto (Requiere Clave)"):
        pass_adm = st.text_input("Clave Admin", type="password")
        if pass_adm == CLAVE_ADMIN:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Nuevo / Editar")
                nombre = st.text_input("Nombre del Producto")
                stock = st.number_input("Stock actual", 0)
                costo = st.number_input("Costo Compra $", 0.0)
            with col2:
                p_detal = st.number_input("Precio Detal $", 0.0)
                p_mayor = st.number_input("Precio Mayor $", 0.0)
                m_mayor = st.number_input("Mínimo para Mayor", 1)
            
            if st.button("💾 Guardar en Sistema"):
                existente = df_inv[df_inv['nombre'] == nombre]
                data = {"nombre": nombre, "stock": stock, "costo": costo, "precio_detal": p_detal, "precio_mayor": p_mayor, "min_mayor": m_mayor}
                if not existente.empty:
                    db.table("inventario").update(data).eq("nombre", nombre).execute()
                else:
                    db.table("inventario").insert(data).execute()
                st.success("¡Producto actualizado!"); st.rerun()

# --- MÓDULO VENTA ---
elif opcion == "🛒 Venta Rápida":
    st.header("🛒 Terminal de Ventas")
    tasa = st.number_input("Tasa del Día (Bs/$)", 1.0, 500.0, 60.0)
    res_p = db.table("inventario").select("*").execute()
    
    if res_p.data:
        df_p = pd.DataFrame(res_p.data)
        
        # BUSCADOR INTELIGENTE
        busc = st.text_input("🔍 Escribe el nombre del producto...", placeholder="Ej: Harina, Arroz...").lower()
        df_f = df_p[df_p['nombre'].str.lower().str.contains(busc)] if busc else df_p
        
        c1, c2 = st.columns([3, 1])
        item_sel = c1.selectbox("Selecciona Producto", df_f['nombre'])
        cant_sel = c2.number_input("Cantidad", 1)
        
        if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
            p = df_p[df_p['nombre'] == item_sel].iloc[0]
            if p['stock'] >= cant_sel:
                precio = float(p['precio_mayor']) if cant_sel >= p['min_mayor'] else float(p['precio_detal'])
                st.session_state.car.append({
                    "p": p['nombre'], "c": cant_sel, "u": precio, 
                    "t": round(precio * cant_sel, 2), "costo_u": float(p['costo'])
                })
                st.rerun()
            else: st.error("¡Stock insuficiente!")

    if st.session_state.car:
        st.subheader("📋 Resumen de Venta")
        for i, it in enumerate(st.session_state.car):
            st.text(f"• {it['p']} x{it['c']} - ${it['t']:.2f}")
        
        sub_total_usd = sum(x['t'] for x in st.session_state.car)
        total_bs_sug = sub_total_usd * tasa
        
        st.divider()
        total_bs = st.number_input("MONTO FINAL A COBRAR (Bs.)", value=float(total_bs_sug))
        
        # Pagos Mixtos
        st.write("### 💳 Registro de Pagos")
        c1, c2, c3 = st.columns(3)
        p_ef = c1.number_input("Efectivo Bs", 0.0); p_pm = c1.number_input("Pago Móvil Bs", 0.0)
        p_pu = c2.number_input("Punto Bs", 0.0); p_ot = c2.number_input("Otros Bs", 0.0)
        p_ze = c3.number_input("Zelle $", 0.0); p_di = c3.number_input("Divisas $", 0.0)
        
        total_pagado_bs = p_ef + p_pm + p_pu + p_ot + ((p_ze + p_di) * tasa)
        diferencia = total_bs - total_pagado_bs
        
        if diferencia > 0.1: st.warning(f"Faltan: {diferencia:,.2f} Bs.")
        elif diferencia < -0.1: st.success(f"Vuelto a dar: {abs(diferencia):,.2f} Bs.")
        
        if st.button("🚀 FINALIZAR VENTA Y EMITIR TICKET", use_container_width=True):
            try:
                # Cálculo de propina (redondeo)
                redondeo_usd = (total_bs / tasa) - sub_total_usd
                st.session_state.pdf_b = crear_ticket(st.session_state.car, total_bs, sub_total_usd, tasa, redondeo_usd)
                
                for x in st.session_state.car:
                    db.table("ventas").insert({
                        "producto": x['p'], "cantidad": x['c'], "total_usd": x['t'], "tasa_cambio": tasa,
                        "pago_efectivo": p_ef, "pago_punto": p_pu, "pago_movil": p_pm, "pago_zelle": p_ze, 
                        "pago_otros": p_ot, "pago_divisas": p_di, "costo_venta": x['costo_u'] * x['c'],
                        "propina": redondeo_usd / len(st.session_state.car), "fecha": datetime.now().isoformat()
                    }).execute()
                    
                    # Descontar stock
                    nuevo_stock = int(df_p[df_p['nombre'] == x['p']].iloc[0]['stock']) - x['c']
                    db.table("inventario").update({"stock": nuevo_stock}).eq("nombre", x['p']).execute()
                
                st.balloons()
                st.success("✅ ¡VENTA FINALIZADA CON ÉXITO!")
                st.session_state.car = []
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    if st.session_state.pdf_b:
        st.download_button("📥 DESCARGAR FACTURA PDF", st.session_state.pdf_b, "ticket.pdf", "application/pdf")

# --- MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.header("💸 Gastos")
    with st.form("gas_f"):
        desc = st.text_input("Descripción del gasto")
        monto = st.number_input("Monto en $", 0.0)
        if st.form_submit_button("Registrar Gasto"):
            db.table("gastos").insert({"descripcion": desc, "monto_usd": monto, "fecha": datetime.now().isoformat()}).execute()
            st.success("Gasto guardado")

# --- MÓDULO REPORTES ---
elif opcion == "📊 Reportes":
    st.header("📊 Inteligencia de Negocio")
    f = st.date_input("Seleccionar Día", date.today())
    v_res = db.table("ventas").select("*").gte("fecha", f.isoformat()).execute()
    g_res = db.table("gastos").select("*").gte("fecha", f.isoformat()).execute()
    
    if v_res.data:
        df_v = pd.DataFrame(v_res.data)
        df_g = pd.DataFrame(g_res.data)
        
        bruta = df_v['total_usd'].sum()
        costos = df_v['costo_venta'].sum()
        gastos = df_g['monto_usd'].sum() if not df_g.empty else 0
        propinas = df_v['propina'].sum()
        
        neta = bruta - costos - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Utilidad Bruta (Ventas)", f"${bruta:,.2f}")
        c2.metric("Propina / Redondeo", f"${propinas:,.2f}")
        c3.metric("Gastos Totales", f"${gastos:,.2f}")
        c4.metric("UTILIDAD NETA", f"${neta:,.2f}", delta=f"${neta:,.2f}")
        
        st.write("### Detalle de Ventas")
        st.dataframe(df_v[['fecha', 'producto', 'cantidad', 'total_usd', 'propina']], use_container_width=True)
