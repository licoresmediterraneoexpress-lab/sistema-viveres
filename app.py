import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Mediterraneo Express PRO", layout="wide")

# --- 2. INYECCIÓN DE ESTILOS (AQUÍ MODIFICAMOS LOS COLORES) ---
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #F8F9FA;
    }

    /* BARRA LATERAL (MENU) - AZUL CLARO */
    [data-testid="stSidebar"] {
        background-color: #ADD8E6 !important; /* Azul Claro */
        border-right: 1px solid #90C3D4;
    }

    /* LETRAS DEL MENU (Negras) */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #000000 !important;
        font-weight: 500;
    }

    /* TEXTOS GENERALES EN NEGRO */
    h1, h2, h3, h4, p, span, label {
        color: #000000 !important;
    }

    /* BOTÓN FINALIZAR (Azul Oscuro con Letras Blancas) */
    .stButton > button[kind="primary"] {
        background-color: #002D62 !important; /* Azul Rey Profundo */
        color: #FFFFFF !important; /* Letras Blancas */
        border-radius: 8px !important;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* BOTONES DE ANULACIÓN (Rojo con Letras Blancas) */
    .stButton > button:contains("Anular"), 
    .stButton > button:contains("Eliminar") {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
    }

    /* TARJETAS DE CONTENEDORES (Blancas con sombra suave) */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }
    
    /* INPUTS (Cuadros de texto) */
    input {
        color: #000000 !important;
    }

    </style>
    """, unsafe_allow_html=True)

# --- CONTINUACIÓN DEL CÓDIGO (No tocar) ---
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"

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

# --- 8. CIERRE DE CAJA (PROFESIONAL, BLINDADO Y SEGREGADO) ---
elif opcion == "📊 Cierre de Caja":
    st.markdown("<h1 class='main-header'>📊 Gestión de Caja y Auditoría</h1>", unsafe_allow_html=True)
    
    # Inyección de CSS para resaltar métricas de auditoría
    st.markdown("""
        <style>
        .cuadre-positivo { padding:20px; background-color:#d4edda; color:#155724; border-radius:10px; border:2px solid #c3e6cb; font-weight: bold; }
        .cuadre-negativo { padding:20px; background-color:#f8d7da; color:#721c24; border-radius:10px; border:2px solid #f5c6cb; font-weight: bold; }
        .resumen-auditoria { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #444; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    # REPARACIÓN CRÍTICA: Lógica de Apertura
    if not st.session_state.get('id_turno'):
        st.warning("⚠️ No hay un turno activo. Por favor, abra la caja para comenzar a facturar.")
        
        with st.form("apertura_jornada_blindada"):
            st.subheader("🔓 Apertura de Turno")
            col_ap1, col_ap2 = st.columns(2)
            
            tasa_v = col_ap1.number_input("Tasa de Cambio del Día (Bs/$)", min_value=1.0, value=60.0, format="%.2f")
            f_bs_v = col_ap1.number_input("Fondo Inicial en Bolívares (Efectivo)", min_value=0.0, value=0.0, step=10.0)
            f_usd_v = col_ap2.number_input("Fondo Inicial en Divisas (Efectivo $)", min_value=0.0, value=0.0, step=1.0)
            
            if st.form_submit_button("🚀 ABRIR CAJA E INICIAR JORNADA", use_container_width=True):
                try:
                    # Registro en base de datos
                    data_ins = {
                        "tasa_apertura": float(tasa_v),
                        "fondo_bs": float(f_bs_v),
                        "fondo_usd": float(f_usd_v),
                        "monto_apertura": float(f_usd_v), # Compatibilidad con esquemas previos
                        "estado": "abierto",
                        "fecha_apertura": datetime.now().isoformat()
                    }
                    res_ins = db.table("cierres").insert(data_ins).execute()
                    
                    if res_ins.data:
                        # Actualización inmediata del state para evitar NoneType
                        nuevo_id = res_ins.data[0]['id']
                        st.session_state.id_turno = nuevo_id
                        st.success(f"✅ Turno #{nuevo_id} abierto exitosamente.")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error crítico de apertura: {e}")
    
    else:
        # --- LÓGICA DE CIERRE Y AUDITORÍA ---
        id_turno = st.session_state.id_turno
        
        # 1. Recuperar Datos del Registro de Cierre Actual
        res_turno = db.table("cierres").select("*").eq("id", id_turno).single().execute()
        d_turno = res_turno.data
        tasa_dia = float(d_turno['tasa_apertura'])

        # 2. Cálculos del Sistema (Segregación de Pagos)
        # Filtramos estrictamente por id_cierre para soportar turnos nocturnos
        v_res = db.table("ventas").select("*").eq("id_cierre", id_turno).neq("estado", "Anulado").execute()
        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame()

        if not df_v.empty:
            # Forzar conversión a float para cálculos matemáticos
            cols_money = [
                'pago_efectivo', 'pago_divisas', 'pago_movil', 'pago_punto', 
                'pago_zelle', 'pago_otros', 'total_usd', 'costo_venta'
            ]
            for c in cols_money:
                df_v[c] = df_v[c].fillna(0).astype(float)

            # Segregación exacta
            sys_efec_bs = df_v['pago_efectivo'].sum()
            sys_divisas = df_v['pago_divisas'].sum()
            sys_pago_movil = df_v['pago_movil'].sum()
            sys_punto = df_v['pago_punto'].sum()
            sys_zelle = df_v['pago_zelle'].sum()
            sys_otros = df_v['pago_otros'].sum() # Se asume USD por defecto en la sumatoria total
            
            sys_total_usd = df_v['total_usd'].sum()
            sys_total_costo = df_v['costo_venta'].sum()
        else:
            sys_efec_bs = sys_divisas = sys_pago_movil = sys_punto = sys_zelle = sys_otros = sys_total_usd = sys_total_costo = 0.0

        # 3. Formulario de Declaración Ciega (Seguridad)
        st.subheader("🕵️ Declaración de Conteo Físico")
        st.info("Ingrese los montos físicos presentes en caja y bancos. El sistema calculará la diferencia al finalizar.")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_bs = c1.number_input("Efectivo Bolívares (Físico)", min_value=0.0, step=1.0, key="f_bs")
            f_usd = c2.number_input("Efectivo Divisas $ (Físico)", min_value=0.0, step=1.0, key="f_usd")
            f_pmovil = c3.number_input("Monto Pago Móvil (Banco)", min_value=0.0, step=1.0, key="f_pm")
            
            f_punto = c1.number_input("Monto Punto de Venta (Banco)", min_value=0.0, step=1.0, key="f_pv")
            f_zelle = c2.number_input("Monto Zelle / Otros $ (Banco)", min_value=0.0, step=1.0, key="f_zl")

        # 4. Cálculos de Auditoría y Salida
        if st.button("📊 GENERAR PRE-CIERRE Y AUDITAR", use_container_width=True):
            st.divider()
            
            # Cálculo de Diferencias (Ventas + Fondos Iniciales)
            # Lo que debería haber en Bs:
            debe_bs = sys_efec_bs + float(d_turno['fondo_bs'])
            # Lo que debería haber en USD:
            debe_usd = sys_divisas + float(d_turno['fondo_usd'])
            # Bancos:
            debe_bancos_bs = sys_pago_movil + sys_punto
            debe_bancos_usd = sys_zelle + sys_otros

            # Totales Declarados
            total_declarado_bs = f_bs + f_pmovil + f_punto
            total_declarado_usd = f_usd + f_zelle
            
            # Diferencia Final (Normalizada a USD para registro)
            diff_bs = (f_bs - debe_bs) + (f_pmovil - sys_pago_movil) + (f_punto - sys_punto)
            diff_usd = (f_usd - debe_usd) + (f_zelle - debe_bancos_usd)
            
            diferencia_final_usd = diff_usd + (diff_bs / tasa_dia)

            # Panel de Resultados
            st.markdown("<div class='resumen-auditoria'>", unsafe_allow_html=True)
            st.subheader("📈 Resultado de la Jornada")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Facturado (USD)", f"${sys_total_usd:,.2f}")
            m1.metric("Total Facturado (Bs)", f"{sys_total_usd * tasa_dia:,.2f} Bs")
            
            # Cálculo de Ganancia Neta
            ganancia_neta = sys_total_usd - sys_total_costo
            m2.metric("Ganancia Neta", f"${ganancia_neta:,.2f}", delta="Utilidad Bruta")
            
            # Valorización de Inventario
            inv_res = db.table("inventario").select("stock, costo").execute()
            valor_inv = sum([float(x['stock']) * float(x['costo']) for x in inv_res.data]) if inv_res.data else 0.0
            m3.metric("Valor Inventario", f"${valor_inv:,.2f}")
            
            st.markdown("</div>", unsafe_allow_html=True)

            # Visualización de Cuadre
            if abs(diferencia_final_usd) < 0.01:
                st.markdown(f"<div class='cuadre-positivo'>✅ CAJA CUADRADA: La diferencia es de $0.00.</div>", unsafe_allow_html=True)
            elif diferencia_final_usd > 0:
                st.markdown(f"<div class='cuadre-positivo'>🟢 SOBRANTE DETECTADO: +${diferencia_final_usd:,.2f} USD</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='cuadre-negativo'>🔴 FALTANTE DETECTADO: -${abs(diferencia_final_usd):,.2f} USD</div>", unsafe_allow_html=True)

            # Botón Final de Persistencia
            st.warning("⚠️ Una vez cerrado, no podrá modificar ventas de este turno.")
            if st.button("🔒 CERRAR TURNO DEFINITIVAMENTE", type="primary"):
                try:
                    update_data = {
                        "fecha_cierre": datetime.now().isoformat(),
                        "total_ventas": float(sys_total_usd),
                        "total_ganancias": float(ganancia_neta),
                        "diferencia": float(diferencia_final_usd),
                        "estado": "cerrado"
                    }
                    db.table("cierres").update(update_data).eq("id", id_turno).execute()
                    
                    # Reset de sesión
                    st.session_state.id_turno = None
                    st.success("Jornada finalizada exitosamente.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al persistir el cierre: {e}")

    # Pie de página informativo
    st.caption(f"ID Turno Actual: {st.session_state.get('id_turno', 'Ninguno')}")




