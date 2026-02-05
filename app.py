import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

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

    # Inyección de CSS para Estilo Excel y Contenedores
    st.markdown("""
        <style>
        .report-container { border: 1px solid #ddd; border-radius: 5px; padding: 10px; background-color: #1e1e1e; }
        .table-header { background-color: #333; padding: 10px; border-bottom: 2px solid #555; font-weight: bold; color: #00ffcc; }
        .total-row { background-color: #262730; padding: 15px; border-top: 2px solid #00ffcc; font-size: 1.2rem; font-weight: bold; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='main-header'>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    st.info(f"🔎 Auditando **Turno ID: {id_turno}**")

    # 1. CARGA DE DATOS
    try:
        res_h = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        data_ventas = res_h.data if res_h.data else []
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}"); data_ventas = []

    if data_ventas:
        # Cargamos el DataFrame original
        df_h = pd.DataFrame(data_ventas)
        
        # Blindaje de tipos y manejo de nulos preventivo
        df_h['total_usd'] = df_h['total_usd'].astype(float)
        df_h['monto_cobrado_bs'] = df_h['monto_cobrado_bs'].astype(float)
        df_h['producto'] = df_h['producto'].fillna("")
        df_h['cliente'] = df_h['cliente'].fillna("General")
        
        # Formateo de fechas para visualización y filtro
        df_h['fecha_dt'] = pd.to_datetime(df_h['fecha'])
        df_h['hora'] = df_h['fecha_dt'].dt.strftime('%I:%M %p')
        df_h['fecha_corta'] = df_h['fecha_dt'].dt.strftime('%d/%m/%Y')

        # 2. BUSCADOR INTELIGENTE (MEJORADO)
        with st.container(border=True):
            c_busc1, c_busc2, c_busc3 = st.columns([2, 1, 1])
            busqueda = c_busc1.text_input("🔍 Filtro inteligente", placeholder="Buscar por ID, Producto o Cliente...")
            f_fecha = c_busc2.text_input("📅 Fecha (DD/MM/YYYY)", placeholder="Ej: 05/02/2026")
            estado_filtro = c_busc3.selectbox("Estado", ["Todos", "Finalizado", "Anulado"])

        # Lógica de Filtrado Multicolumna y Manejo de Nulos
        # Creamos una copia para filtrar sin perder los datos originales de la sesión
        df_filtrado = df_h.copy()

        if busqueda:
            # CORRECCIÓN DE SINTAXIS: Se añade .str y se maneja case/na
            mask = (
                df_filtrado['id'].astype(str).str.contains(busqueda, case=False, na=False) |
                df_filtrado['producto'].str.contains(busqueda, case=False, na=False) |
                df_filtrado['cliente'].astype(str).str.contains(busqueda, case=False, na=False)
            )
            df_filtrado = df_filtrado[mask]
            
        if f_fecha:
            df_filtrado = df_filtrado[df_filtrado['fecha_corta'].str.contains(f_fecha, na=False)]
            
        if estado_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado['estado'] == estado_filtro]

        # 3. ENCABEZADOS ESTILO EXCEL
        st.markdown("<div class='table-header'>", unsafe_allow_html=True)
        h1, h2, h3, h4, h5, h6 = st.columns([0.8, 1, 3, 1.2, 1.2, 1.3])
        for col, h in zip([h1, h2, h3, h4, h5, h6], ["ID", "HORA", "PRODUCTOS", "USD", "BS", "ACCIÓN"]):
            col.write(f"**{h}**")
        st.markdown("</div>", unsafe_allow_html=True)

        # 4. CUERPO DE LA TABLA (Usando df_filtrado)
        for _, fila in df_filtrado.iterrows():
            es_anulado = fila['estado'] == 'Anulado'
            st_style = "color: #888; text-decoration: line-through;" if es_anulado else "color: white;"
            
            with st.container():
                c1, c2, c3, c4, c5, c6 = st.columns([0.8, 1, 3, 1.2, 1.2, 1.3])
                c1.markdown(f"<span style='{st_style}'>{fila['id']}</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='{st_style}'>{fila['hora']}</span>", unsafe_allow_html=True)
                
                # Procesamiento seguro de nombres de productos
                items_raw = fila.get('items')
                try:
                    if isinstance(items_raw, str):
                        items_lista = json.loads(items_raw)
                    elif isinstance(items_raw, list):
                        items_lista = items_raw
                    else:
                        items_lista = []
                    
                    nombres_items = ", ".join([str(i.get('nombre', 'Desconocido')) for i in items_lista]) if items_lista else fila['producto']
                except:
                    nombres_items = fila['producto']
                
                prod_display = (nombres_items[:50] + '...') if len(nombres_items) > 50 else nombres_items
                c3.markdown(f"<span style='{st_style}' title='{nombres_items}'>{prod_display}</span>", unsafe_allow_html=True)
                c4.markdown(f"<span style='{st_style}'>${fila['total_usd']:,.2f}</span>", unsafe_allow_html=True)
                c5.markdown(f"<span style='{st_style}'>{fila['monto_cobrado_bs']:,.2f} Bs</span>", unsafe_allow_html=True)

                if not es_anulado:
                    if c6.button("🚫 Anular", key=f"btn_anul_{fila['id']}", use_container_width=True):
                        try:
                            with st.spinner("Procesando anulación..."):
                                items_a_revertir = fila.get('items')
                                if items_a_revertir:
                                    if isinstance(items_a_revertir, str):
                                        items_a_revertir = json.loads(items_a_revertir)
                                    
                                    for item in items_a_revertir:
                                        id_prod = item.get('id')
                                        cant_v = float(item.get('cant', 0))
                                        if id_prod:
                                            res_inv = db.table("inventario").select("stock").eq("id", id_prod).execute()
                                            if res_inv.data:
                                                stk_act = float(res_inv.data[0]['stock'])
                                                db.table("inventario").update({"stock": stk_act + cant_v}).eq("id", id_prod).execute()
                                else:
                                    st.warning(f"⚠️ Venta #{fila['id']}: No hay desglose para revertir stock.")

                                db.table("ventas").update({"estado": "Anulado"}).eq("id", fila['id']).execute()
                                st.toast(f"Venta #{fila['id']} anulada", icon="✅")
                                time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"Error crítico en reversión: {str(e)}")
                else:
                    c6.markdown("<center>❌</center>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:2px; border-color:#444'>", unsafe_allow_html=True)

        # 5. TOTALES (RECALCULADOS SEGÚN EL FILTRO)
        # Sumamos solo las ventas activas (no anuladas) de los resultados filtrados
        df_totales = df_filtrado[df_filtrado['estado'] != 'Anulado']
        
        st.markdown(f"""
            <div class='total-row'>
                <div style='display: flex; justify-content: space-between;'>
                    <span>TOTALES EN PANTALLA (Ventas Activas):</span>
                    <span>
                        <span style='color: #00ffcc;'>$ {df_totales['total_usd'].sum():,.2f}</span> | 
                        <span style='color: #ffcc00;'>Bs. {df_totales['monto_cobrado_bs'].sum():,.2f}</span>
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay registros en este turno.")

# --- 7. MÓDULO GASTOS ---
elif opcion == "💸 Gastos":
    st.markdown("<h1 class='main-header'>💸 Gastos Operativos</h1>", unsafe_allow_html=True)
    with st.form("g"):
        d = st.text_input("Descripción")
        m = st.number_input("Monto $", 0.0)
        if st.form_submit_button("REGISTRAR GASTO") and id_turno:
            db.table("gastos").insert({"id_cierre": id_turno, "descripcion": d, "monto_usd": m}).execute()
            st.success("Gasto guardado")

# --- 8. CIERRE DE CAJA (BLINDADO Y AUDITABLE) ---
elif opcion == "📊 Cierre de Caja":
    st.markdown("<h1 class='main-header'>📊 Gestión de Caja y Turnos</h1>", unsafe_allow_html=True)
    
    # Inyección de CSS para alertas de cuadre
    st.markdown("""
        <style>
        .cuadre-positivo { padding:20px; background-color:#d4edda; color:#155724; border-radius:10px; border:2px solid #c3e6cb; }
        .cuadre-negativo { padding:20px; background-color:#f8d7da; color:#721c24; border-radius:10px; border:2px solid #f5c6cb; }
        .metric-card { background-color: #262730; padding: 15px; border-radius: 8px; border: 1px solid #444; }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get('id_turno'):
        # --- LÓGICA DE APERTURA ---
        with st.form("apertura_jornada"):
            st.subheader("🔓 Apertura de Nueva Jornada")
            c1, c2 = st.columns(2)
            t_a = c1.number_input("Tasa de Cambio (BCV/Mkt)", value=60.0, format="%.2f")
            f_usd = c2.number_input("Fondo Inicial Divisas ($)", value=0.0, format="%.2f")
            f_bs = c1.number_input("Fondo Inicial Bolívares (Bs)", value=0.0, format="%.2f")
            
            st.info("Al abrir caja, se habilitará el módulo de ventas y se registrará la hora de inicio.")
            
            if st.form_submit_button("🚀 INICIAR TURNO", use_container_width=True):
                try:
                    nueva_apertura = {
                        "tasa_apertura": float(t_a),
                        "monto_apertura": float(f_usd),
                        "fondo_bs": float(f_bs),
                        "fondo_usd": float(f_usd),
                        "estado": "abierto",
                        "fecha_apertura": datetime.now().isoformat()
                    }
                    db.table("cierres").insert(nueva_apertura).execute()
                    st.success("Caja abierta correctamente."); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error al abrir turno: {e}")
    else:
        # --- LÓGICA DE CIERRE ---
        id_turno = st.session_state.id_turno
        
        # 1. Recuperar Datos del Turno Actual
        datos_turno = db.table("cierres").select("*").eq("id", id_turno).single().execute().data
        
        # 2. Cálculos del Sistema (Auditoría de Ventas)
        v_res = db.table("ventas").select("*").eq("id_cierre", id_turno).neq("estado", "Anulado").execute()
        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()

        if not df_v.empty:
            # Asegurar tipos float para evitar StreamlitMixedNumericTypesError
            metodos = ['pago_punto', 'pago_efectivo', 'pago_movil', 'pago_zelle', 'pago_otros', 'pago_divisas', 'costo_venta', 'total_usd']
            for col in metodos: df_v[col] = df_v[col].astype(float)

            # Sumatorias por método
            s_punto = df_v['pago_punto'].sum()
            s_movil = df_v['pago_movil'].sum()
            s_zelle = df_v['pago_zelle'].sum()
            s_efec_bs = df_v['pago_efectivo'].sum()
            s_divisas = df_v['pago_divisas'].sum()
            s_otros = df_v['pago_otros'].sum()
            
            total_facturado = df_v['total_usd'].sum()
            costo_total = df_v['costo_venta'].sum()
            banco_sistema = s_punto + s_movil + s_zelle
        else:
            s_punto = s_movil = s_zelle = s_efec_bs = s_divisas = s_otros = total_facturado = costo_total = banco_sistema = 0.0

        # 3. Interfaz de Auditoría
        st.subheader("🕵️ Panel de Auditoría del Sistema")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Efectivo Bs (Sistema)", f"{s_efec_bs:,.2f} Bs")
        c2.metric("Divisas (Sistema)", f"${s_divisas:,.2f}")
        c3.metric("Banco (Sistema)", f"${banco_sistema:,.2f}")
        c4.metric("Total Facturado", f"${total_facturado:,.2f}")

        st.divider()

        # 4. Formulario de Declaración Física
        st.subheader("📝 Declaración de Conteo Físico")
        with st.container(border=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            f_efec_usd = col_f1.number_input("Efectivo Divisas en Físico ($)", min_value=0.0, step=1.0)
            f_efec_bs = col_f2.number_input("Efectivo Bolívares en Físico (Bs)", min_value=0.0, step=1.0)
            f_banco = col_f3.number_input("Total Banco (Punto/Móvil/Zelle)", min_value=0.0, step=1.0)

        # 5. Cálculo de Diferencia
        # Lo que debería haber: (Ventas por método + Fondos Iniciales)
        debe_haber_usd = s_divisas + datos_turno['fondo_usd']
        debe_haber_bs = s_efec_bs + datos_turno['fondo_bs']
        debe_haber_banco = banco_sistema
        
        # Diferencia total convertida a USD para el registro
        # (Físico - Sistema)
        diff_usd = (f_efec_usd - debe_haber_usd) + ((f_efec_bs - debe_haber_bs) / datos_turno['tasa_apertura']) + (f_banco - debe_haber_banco)

        # Visualización de Resultado
        if diff_usd >= 0:
            st.markdown(f"<div class='cuadre-positivo'>✅ <b>SOBRANTE:</b> ${diff_usd:.2f} USD. La caja está cuadrada o tiene excedente.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='cuadre-negativo'>⚠️ <b>FALTANTE:</b> ${abs(diff_usd):.2f} USD. El conteo físico es menor al sistema.</div>", unsafe_allow_html=True)

        st.divider()

        # 6. Botón de Acción Final
        if st.button("🔴 FINALIZAR JORNADA Y CERRAR CAJA", type="primary", use_container_width=True):
            try:
                # Cálculo de ganancia neta (Ventas - Costo)
                ganancia_neta = total_facturado - costo_total
                
                update_data = {
                    "fecha_cierre": datetime.now().isoformat(),
                    "total_ventas": float(total_facturado),
                    "total_costos": float(costo_total),
                    "total_ganancias": float(ganancia_neta),
                    "diferencia": float(diff_usd),
                    "estado": "cerrado"
                }
                
                db.table("cierres").update(update_data).eq("id", id_turno).execute()
                
                # Limpiar sesión
                st.session_state.id_turno = None
                st.success("✅ Turno cerrado y auditoría registrada con éxito.")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error al cerrar turno: {e}")

        # 7. Información de Inventario (Solo lectura)
        with st.expander("📦 Valorización de Inventario (Costo)"):
            inv_res = db.table("inventario").select("stock, costo").execute()
            if inv_res.data:
                total_inv = sum([float(x['stock']) * float(x['costo']) for x in inv_res.data])
                st.metric("Capital en Inventario (Costo USD)", f"${total_inv:,.2f}")
