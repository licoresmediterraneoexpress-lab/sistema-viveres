import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

@st.cache_resource
def init_db():
    return create_client(URL, KEY)

db = init_db()

# Estilos Profesionales
st.markdown("""
<style>
    .stApp {background-color: #F4F7F6;}
    [data-testid='stSidebar'] {background-color: #002D62;}
    .main-header {color: #002D62; font-weight: bold; border-bottom: 2px solid #FF8C00;}
    .stButton>button {border-radius: 5px; font-weight: bold;}
    .stDataFrame {border: 1px solid #e0e0e0; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if 'car' not in st.session_state: st.session_state.car = []
if 'venta_finalizada' not in st.session_state: st.session_state.venta_finalizada = False

# --- 2. LÓGICA DE TURNO ---
try:
    res_caja = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
    turno_activo = res_caja.data[0] if res_caja.data else None
    id_turno = turno_activo['id'] if turno_activo else None
except Exception:
    turno_activo = None
    id_turno = None

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:white;text-align:center;'>🚢 MEDITERRANEO</h2>", unsafe_allow_html=True)
    opcion = st.radio("MENÚ PRINCIPAL", ["📦 Inventario", "🛒 Punto de Venta", "📜 Historial", "💸 Gastos", "📊 Cierre de Caja"])
    st.divider()
    if turno_activo:
        st.success(f"Turno Abierto: #{id_turno}")
    else:
        st.error("Caja Cerrada")

# --- 4. MÓDULO INVENTARIO ---
if opcion == "📦 Inventario":
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    res = db.table("inventario").select("*").order("nombre").execute()
    df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_inv.empty:
        # Buscador
        busc = st.text_input("🔍 Buscar Producto", placeholder="Nombre del producto...")
        df_mostrar = df_inv[df_inv['nombre'].str.contains(busc, case=False)] if busc else df_inv

        # Botones de Acción arriba de la tabla
        st.subheader("📋 Existencias")
        
        # Diálogo Edición
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

        # Visualización en Tabla
        st.dataframe(df_mostrar[['nombre', 'stock', 'precio_detal', 'precio_mayor', 'min_mayor']], use_container_width=True, hide_index=True)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            sel = st.selectbox("Seleccione para Editar", [None] + df_mostrar['nombre'].tolist())
            if sel:
                p_data = df_inv[df_inv['nombre'] == sel].iloc[0].to_dict()
                if st.button(f"Modificar {sel}"): edit_dial(p_data)
        
        with col_act2:
            del_sel = st.selectbox("Seleccione para Eliminar", [None] + df_mostrar['nombre'].tolist())
            clave = st.text_input("Clave Admin", type="password", key="del_key")
            if st.button("Eliminar Producto", type="primary"):
                if clave == CLAVE_ADMIN and del_sel:
                    db.table("inventario").delete().eq("nombre", del_sel).execute()
                    st.success("Eliminado"); time.sleep(1); st.rerun()

    # Registro Nuevo
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
                st.rerun()

# --- 5. MÓDULO PUNTO DE VENTA (SOPORTE PAGOS MIXTOS) ---
elif opcion == "🛒 Punto de Venta":
    # Sincronización de Turno (Uso de id_turno desde session_state)
    if not st.session_state.get('id_turno'):
        st.error("⚠️ DEBE ABRIR CAJA PRIMERO")
        st.info("Vaya al módulo de 'Cierre de Caja' para iniciar una jornada.")
        st.stop()
    
    id_turno = int(st.session_state.id_turno)
    
    st.markdown("<h1 class='main-header'>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    
    # 1. CONTROL DE TASA (Blindaje Float)
    tasa_actual_val = float(st.session_state.get('tasa_dia', 1.0))
    tasa = st.number_input("Tasa BCV (Bs/$)", value=tasa_actual_val, format="%.2f", step=0.01)
    
    c_izq, c_der = st.columns([1, 1.1])
    
    with c_izq:
        st.subheader("🔍 Buscador de Productos")
        busc_v = st.text_input("Escribe nombre o ID...", placeholder="Ej: Harina Pan", key="pos_search")
        
        # Filtro en tiempo real con Supabase
        if busc_v:
            res_v = db.table("inventario").select("*").ilike("nombre", f"%{busc_v}%").gt("stock", 0).limit(8).execute()
        else:
            res_v = db.table("inventario").select("*").gt("stock", 0).limit(8).execute()

        for p in res_v.data:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.markdown(f"**{p['nombre']}**\n\nStock: `{int(p['stock'])}`")
                col2.markdown(f"<h4 style='color:green;'>${float(p['precio_detal']):.2f}</h4>", unsafe_allow_html=True)
                
                # Botón de añadir con un solo clic
                if col3.button("➕ Añadir", key=f"add_{p['id']}", use_container_width=True):
                    # Evitar duplicados: Si ya existe en el carrito, sumar 1
                    found = False
                    for item in st.session_state.car:
                        if item['id'] == p['id']:
                            item['cant'] += 1.0
                            found = True
                            break
                    if not found:
                        st.session_state.car.append({
                            "id": int(p['id']), 
                            "nombre": p['nombre'], 
                            "cant": 1.0, 
                            "precio": float(p['precio_detal']), 
                            "costo": float(p['costo'])
                        })
                    st.rerun()

    with c_der:
        st.subheader("📋 Carrito de Ventas")
        total_usd = 0.0
        
        if not st.session_state.car:
            st.info("El carrito está vacío.")
        else:
            # Iteración del carrito con corrección de StreamlitMixedNumericTypesError
            for i, item in enumerate(st.session_state.car):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 1.5, 0.5])
                    
                    # CORRECCIÓN DE ERROR DE TIPOS: Forzar todos los parámetros a float
                    item['cant'] = c1.number_input(
                        f"{item['nombre']} ($/u {item['precio']:.2f})", 
                        min_value=0.1, 
                        step=1.0, 
                        value=float(item['cant']), 
                        key=f"c_{item['id']}_{i}"
                    )
                    
                    subt = float(item['cant']) * float(item['precio'])
                    total_usd += subt
                    c2.markdown(f"**Subt:**\n${subt:.2f}")
                    
                    if c3.button("❌", key=f"del_{i}"):
                        st.session_state.car.pop(i)
                        st.rerun()
        
        st.divider()
        total_bs_sist = float(total_usd * tasa)
        st.markdown(f"### Total: `${total_usd:.2f}` / `{total_bs_sist:,.2f} Bs`")
        
        # Campo editable para redondeos manuales
        monto_bs_cobrar = st.number_input("Monto a cobrar en Bolívares (Redondeo)", value=float(total_bs_sist), format="%.2f")
        
        with st.expander("💳 REGISTRAR PAGOS MIXTOS", expanded=True):
            p1, p2 = st.columns(2)
            # Todos los inputs forzados a float para cálculos consistentes
            d_efec_usd = p1.number_input("Efectivo $", min_value=0.0, format="%.2f", key="pay_ef_usd")
            d_zelle = p1.number_input("Zelle $", min_value=0.0, format="%.2f", key="pay_zelle")
            d_otros = p1.number_input("Otros $", min_value=0.0, format="%.2f", key="pay_otros")
            
            d_efec_bs = p2.number_input("Efectivo Bs", min_value=0.0, format="%.2f", key="pay_ef_bs")
            d_pmovil = p2.number_input("Pago Móvil Bs", min_value=0.0, format="%.2f", key="pay_pm")
            d_punto = p2.number_input("Punto de Venta Bs", min_value=0.0, format="%.2f", key="pay_pv")
            
            # Cálculo de balance en tiempo real
            pagado_usd_desde_bs = (d_efec_bs + d_pmovil + d_punto) / tasa if tasa > 0 else 0.0
            total_pagado_usd = d_efec_usd + d_zelle + d_otros + pagado_usd_desde_bs
            
            monto_esperado_usd = monto_bs_cobrar / tasa if tasa > 0 else 0.0
            vuelto_usd = total_pagado_usd - monto_esperado_usd
            
            if vuelto_usd >= -0.01:
                st.success(f"✅ Vuelto: ${vuelto_usd:.2f} / {vuelto_usd * tasa:,.2f} Bs")
            else:
                st.error(f"❌ Faltante: ${abs(vuelto_usd):.2f} / {abs(vuelto_usd * tasa):,.2f} Bs")

        # Botón Finalizar con validación de pago y blindaje de tipos para Supabase
        if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True, disabled=(vuelto_usd < -0.01 or not st.session_state.car)):
            try:
                items_resumen = ""
                costo_v = 0.0
                
                # 1. Proceso de Actualización de Inventario y Resumen
                for it in st.session_state.car:
                    # Consultar stock actual para evitar valores negativos
                    curr = db.table("inventario").select("stock").eq("id", it['id']).execute()
                    if curr.data:
                        new_st = float(curr.data[0]['stock']) - float(it['cant'])
                        db.table("inventario").update({"stock": new_st}).eq("id", it['id']).execute()
                    
                    items_resumen += f"{int(it['cant'])}x {it['nombre']}, "
                    costo_v += (float(it['costo']) * float(it['cant']))

                # 2. Inserción en Tabla Ventas (Blindaje de tipos PGRST204)
                venta_payload = {
                    "id_cierre": int(id_turno), 
                    "producto": items_resumen.strip(", "), 
                    "cantidad": int(len(st.session_state.car)),
                    "total_usd": float(round(total_usd, 2)), 
                    "monto_cobrado_bs": float(round(monto_bs_cobrar, 2)), 
                    "tasa_cambio": float(tasa),
                    "pago_divisas": float(d_efec_usd), 
                    "pago_zelle": float(d_zelle), 
                    "pago_otros": float(d_otros),
                    "pago_efectivo": float(d_efec_bs), 
                    "pago_movil": float(d_pmovil), 
                    "pago_punto": float(d_punto),
                    "costo_venta": float(round(costo_v, 2)), 
                    "estado": "Finalizado", 
                    "items": st.session_state.car, # JSONB
                    "id_transaccion": int(datetime.now().timestamp()),
                    "fecha": datetime.now().isoformat()
                }
                
                db.table("ventas").insert(venta_payload).execute()
                
                # 3. Generación de Ticket (Vista Previa)
                st.balloons()
                st.markdown("""
                    <div style="background-color:white; color:black; padding:20px; border-radius:10px; font-family:monospace; border:1px solid #ccc;">
                        <h3 style="text-align:center;">TICKET DE VENTA</h3>
                        <p><b>Fecha:</b> """+datetime.now().strftime("%d/%m/%Y %H:%M")+"""</p>
                        <hr>
                        """+items_resumen+"""
                        <hr>
                        <p><b>TOTAL USD:</b> $"""+f"{total_usd:.2f}"+"""</p>
                        <p><b>TOTAL BS:</b> """+f"{monto_bs_cobrar:,.2f}"+"""</p>
                        <p style="text-align:center;">¡Gracias por su compra!</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Limpiar carrito y estado
                st.session_state.car = []
                if st.button("🔄 Nueva Venta", use_container_width=True):
                    st.rerun()
                
            except Exception as e:
                st.error(f"Error crítico al guardar: {e}")

# --- 6. MÓDULO HISTORIAL (PROFESIONAL Y AUDITABLE) ---
elif opcion == "📜 Historial":
    if not st.session_state.get('id_turno'):
        st.error("⚠️ DEBE ABRIR CAJA PARA VER EL HISTORIAL DEL TURNO"); st.stop()
    
    id_turno = st.session_state.id_turno

    st.markdown("<h1 class='main-header'>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    st.markdown(f"**Turno Activo ID:** `{id_turno}`")

    # 1. CARGA DE DATOS (Filtrado por Turno Activo - Soporta Cruce de Medianoche)
    try:
        # Traemos todas las ventas del turno, ordenadas por fecha/hora
        res_h = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        data_ventas = res_h.data if res_h.data else []
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        data_ventas = []

    if data_ventas:
        # Convertir a DataFrame para búsqueda instantánea en memoria
        df_h = pd.DataFrame(data_ventas)
        
        # Formateo de tipos para evitar StreamlitMixedNumericTypesError
        df_h['total_usd'] = df_h['total_usd'].astype(float)
        df_h['monto_cobrado_bs'] = df_h['monto_cobrado_bs'].astype(float)
        
        # Extraer Hora para la visualización
        df_h['hora'] = pd.to_datetime(df_h['fecha']).dt.strftime('%I:%M %p')

        # 2. BUSCADOR INTELIGENTE (Filtros dinámicos)
        c_busc1, c_busc2 = st.columns([2, 1])
        busqueda = c_busc1.text_input("🔍 Buscar por producto o cliente...", placeholder="Ej: Harina / Juan Perez").lower()
        estado_filtro = c_busc2.selectbox("Filtrar por Estado", ["Todos", "Finalizado", "Anulado"])

        # Aplicar filtros al DataFrame
        if busqueda:
            mask = df_h['producto'].str.lower().str.contains(busqueda) | df_h['cliente'].astype(str).str.lower().str.contains(busqueda)
            df_h = df_h[mask]
        
        if estado_filtro != "Todos":
            df_h = df_h[df_h['estado'] == estado_filtro]

        # 3. INTERFAZ DE TABLA ESTILO EXCEL
        st.divider()
        cols_header = st.columns([0.8, 1, 3, 1.2, 1.2, 1.3])
        headers = ["ID", "HORA", "DESCRIPCIÓN PRODUCTOS", "TOTAL $", "TOTAL BS", "ACCIONES"]
        for col, h in zip(cols_header, headers):
            col.markdown(f"**{h}**")
        st.divider()

        # 4. RENDERIZADO DE FILAS CON LÓGICA DE ANULACIÓN
        for _, fila in df_h.iterrows():
            # Estilo visual para ventas anuladas
            es_anulado = fila['estado'] == 'Anulado'
            st_style = "color: #9e9e9e; text-decoration: line-through;" if es_anulado else "color: white;"
            
            c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1, 3, 1.2, 1.2, 1.3])
            
            c1.markdown(f"<span style='{st_style}'>{fila['id']}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='{st_style}'>{fila['hora']}</span>", unsafe_allow_html=True)
            
            # Resumen de productos (tooltip si es muy largo)
            prod_txt = fila['producto'][:45] + "..." if len(fila['producto']) > 45 else fila['producto']
            c3.markdown(f"<span style='{st_style}' title='{fila['producto']}'>{prod_txt}</span>", unsafe_allow_html=True)
            
            c4.markdown(f"<span style='{st_style}'>${fila['total_usd']:,.2f}</span>", unsafe_allow_html=True)
            c5.markdown(f"<span style='{st_style}'>{fila['monto_cobrado_bs']:,.2f} Bs</span>", unsafe_allow_html=True)

            # Botón de Anulación
            if not es_anulado:
                if c6.button("🚫 Anular", key=f"btn_anul_{fila['id']}", use_container_width=True):
                    try:
                        with st.spinner("Revirtiendo stock..."):
                            # REVERSIÓN DE STOCK (Iterar sobre el JSONB 'items')
                            for item in fila['items']:
                                # 1. Obtener stock actual
                                res_inv = db.table("inventario").select("stock").eq("id", item['id']).execute()
                                if res_inv.data:
                                    stock_actual = float(res_inv.data[0]['stock'])
                                    cantidad_vendida = float(item['cant'])
                                    nuevo_stock = stock_actual + cantidad_vendida
                                    
                                    # 2. Actualizar stock
                                    db.table("inventario").update({"stock": nuevo_stock}).eq("id", item['id']).execute()
                            
                            # 3. Marcar venta como Anulada
                            db.table("ventas").update({"estado": "Anulado"}).eq("id", fila['id']).execute()
                            
                            st.toast(f"Venta #{fila['id']} anulada y stock devuelto", icon="✅")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error en el proceso de anulación: {e}")
            else:
                c6.markdown("<span style='color: #ff4b4b; font-weight: bold;'>ANULADA</span>", unsafe_allow_html=True)

        # 5. RESUMEN RÁPIDO DEL FILTRO
        st.divider()
        total_filtro_usd = df_h[df_h['estado'] != 'Anulado']['total_usd'].sum()
        st.subheader(f"Total Visible en Turno: ${total_filtro_usd:,.2f}")

    else:
        st.info("No se registraron ventas en este turno todavía.")

# --- 7. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.markdown("<h1 class='main-header'>💸 Gastos Operativos</h1>", unsafe_allow_html=True)
    with st.form("g"):
        d = st.text_input("Descripción")
        m = st.number_input("Monto $", 0.0)
        if st.form_submit_button("REGISTRAR GASTO") and id_turno:
            db.table("gastos").insert({"id_cierre": id_turno, "descripcion": d, "monto_usd": m}).execute()
            st.success("Gasto guardado")

# --- 8. CIERRE DE CAJA ---
elif opcion == "📊 Cierre de Caja":
    st.markdown("<h1 class='main-header'>📊 Gestión de Caja</h1>", unsafe_allow_html=True)
    
    if not turno_activo:
        with st.form("apertura"):
            st.subheader("Apertura de Turno")
            t_a = st.number_input("Tasa de Apertura", value=60.0)
            f_a = st.number_input("Fondo Inicial $", value=0.0)
            if st.form_submit_button("ABRIR CAJA"):
                db.table("cierres").insert({"tasa_apertura": t_a, "monto_apertura": f_a, "estado": "abierto"}).execute()
                st.rerun()
    else:
        # Cálculos de Cierre
        v_res = db.table("ventas").select("total_usd, costo_venta").eq("id_cierre", id_turno).neq("estado", "Anulado").execute()
        g_res = db.table("gastos").select("monto_usd").eq("id_cierre", id_turno).execute()
        
        total_v = sum([x['total_usd'] for x in v_res.data])
        total_c = sum([x['costo_venta'] for x in v_res.data])
        total_g = sum([x['monto_usd'] for x in g_res.data])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas Totales", f"${total_v:.2f}")
        c2.metric("Gastos", f"${total_g:.2f}")
        c3.metric("Ganancia Neta", f"${total_v - total_c - total_g:.2f}")
        
        if st.button("🔴 CERRAR TURNO ACTUAL", type="primary"):
            db.table("cierres").update({"estado": "cerrado", "fecha_cierre": datetime.now().isoformat()}).eq("id", id_turno).execute()
            st.rerun()



