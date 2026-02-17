import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import json

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
st.set_page_config(
    page_title="MEDITERRANEO EXPRESS PRO",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados para mejor apariencia
st.markdown("""
    <style>
    .main-header {
        color: #1e3c72;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: #1e3c72;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
    }
    .product-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# CONEXIÓN A SUPABASE
# ============================================
URL = "https://orrfldqwpjkkooeuqnmp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ycmZsZHF3cGpra29vZXVxbm1wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzMDg5MDEsImV4cCI6MjA4NDg4NDkwMX0.va4XR7_lDF2QV9SBXTusmAa_bgqV9oKwiIhC23hsC7E"
CLAVE_ADMIN = "1234"

try:
    db = create_client(URL, KEY)
    st.session_state.db_connected = True
except Exception as e:
    st.session_state.db_connected = False
    st.error(f"Error de conexión a Supabase: {e}")
    st.stop()

# ============================================
# VERIFICAR TURNO ACTIVO
# ============================================
try:
    response = db.table("cierres").select("*").eq("estado", "abierto").order("fecha_apertura", desc=True).limit(1).execute()
    turno_activo = response.data[0] if response.data else None
    if turno_activo:
        st.session_state.id_turno = turno_activo['id']
        st.session_state.tasa_dia = turno_activo.get('tasa_apertura', 1.0)
        st.session_state.fondo_bs = turno_activo.get('fondo_bs', 0)
        st.session_state.fondo_usd = turno_activo.get('fondo_usd', 0)
    else:
        st.session_state.id_turno = None
except Exception as e:
    st.session_state.id_turno = None

# ============================================
# MENÚ LATERAL
# ============================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <h1 style="color: white; margin: 0;">⚓ MEDITERRANEO</h1>
            <p style="color: rgba(255,255,255,0.8);">Express PRO</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    opcion = st.radio(
        "MÓDULOS",
        ["📦 INVENTARIO", "🛒 PUNTO DE VENTA", "💸 GASTOS", "📜 HISTORIAL", "📊 CIERRE DE CAJA"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    if st.session_state.id_turno:
        st.success(f"✅ Turno activo: #{st.session_state.id_turno}")
        st.info(f"💱 Tasa: {st.session_state.tasa_dia:.2f} Bs/$")
    else:
        st.error("🔴 Caja cerrada")

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def requiere_turno():
    """Verifica si hay turno activo, si no, muestra mensaje y detiene."""
    if not st.session_state.id_turno:
        st.warning("⚠️ No hay un turno activo. Debe abrir caja en el módulo 'Cierre de Caja'.")
        st.stop()

def formatear_usd(valor):
    return f"${valor:,.2f}"

def formatear_bs(valor):
    return f"{valor:,.2f} Bs"

# ============================================
# MÓDULO 1: INVENTARIO
# ============================================
if opcion == "📦 INVENTARIO":
    st.markdown("<h1 class='main-header'>📦 Gestión de Inventario</h1>", unsafe_allow_html=True)
    
    try:
        response = db.table("inventario").select("*").order("nombre").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        
        if not df.empty:
            tab1, tab2, tab3 = st.tabs(["📋 Ver Inventario", "➕ Agregar Producto", "📊 Estadísticas"])
            
            with tab1:
                col1, col2 = st.columns([3, 1])
                with col1:
                    busqueda = st.text_input("🔍 Buscar producto", placeholder="Ej: Ron, Cerveza...")
                with col2:
                    ver_bajo_stock = st.checkbox("Solo stock bajo (<5)")
                
                df_filtrado = df.copy()
                if busqueda:
                    df_filtrado = df_filtrado[df_filtrado['nombre'].str.contains(busqueda, case=False, na=False)]
                if ver_bajo_stock:
                    df_filtrado = df_filtrado[df_filtrado['stock'] < 5]
                
                st.dataframe(
                    df_filtrado[['nombre', 'stock', 'costo', 'precio_detal', 'precio_mayor', 'min_mayor']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "nombre": "Producto",
                        "stock": st.column_config.NumberColumn("Stock", format="%.0f"),
                        "costo": st.column_config.NumberColumn("Costo $", format="$%.2f"),
                        "precio_detal": st.column_config.NumberColumn("Detal $", format="$%.2f"),
                        "precio_mayor": st.column_config.NumberColumn("Mayor $", format="$%.2f"),
                        "min_mayor": "Mín. Mayor"
                    }
                )
                
                st.divider()
                st.subheader("✏️ Editar producto")
                
                if not df_filtrado.empty:
                    producto_editar = st.selectbox("Seleccionar producto", df_filtrado['nombre'].tolist(), key="editar")
                    if producto_editar:
                        prod = df[df['nombre'] == producto_editar].iloc[0]
                        with st.form("form_editar"):
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                nuevo_nombre = st.text_input("Nombre", value=prod['nombre'])
                                nuevo_stock = st.number_input("Stock", value=float(prod['stock']), min_value=0.0, step=1.0)
                                nuevo_costo = st.number_input("Costo $", value=float(prod['costo']), min_value=0.0, step=0.01)
                            with col_e2:
                                nuevo_detal = st.number_input("Precio Detal $", value=float(prod['precio_detal']), min_value=0.0, step=0.01)
                                nuevo_mayor = st.number_input("Precio Mayor $", value=float(prod['precio_mayor']), min_value=0.0, step=0.01)
                                nuevo_min = st.number_input("Mín. Mayor", value=int(prod['min_mayor']), min_value=1, step=1)
                            
                            if st.form_submit_button("💾 Guardar Cambios"):
                                try:
                                    db.table("inventario").update({
                                        "nombre": nuevo_nombre,
                                        "stock": nuevo_stock,
                                        "costo": nuevo_costo,
                                        "precio_detal": nuevo_detal,
                                        "precio_mayor": nuevo_mayor,
                                        "min_mayor": nuevo_min
                                    }).eq("id", prod['id']).execute()
                                    st.success("✅ Producto actualizado")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                
                st.divider()
                st.subheader("🗑️ Eliminar producto")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    producto_eliminar = st.selectbox("Seleccionar producto", [""] + df['nombre'].tolist(), key="eliminar")
                with col_d2:
                    clave = st.text_input("Clave Admin", type="password", key="clave_eliminar")
                
                if producto_eliminar and st.button("❌ Eliminar", type="primary"):
                    if clave == CLAVE_ADMIN:
                        try:
                            db.table("inventario").delete().eq("nombre", producto_eliminar).execute()
                            st.success(f"Producto '{producto_eliminar}' eliminado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Clave incorrecta")
            
            with tab2:
                with st.form("nuevo_producto"):
                    st.markdown("### Datos del nuevo producto")
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        nombre = st.text_input("Nombre *").upper()
                        stock = st.number_input("Stock inicial *", min_value=0.0, step=1.0, format="%.2f")
                        costo = st.number_input("Costo $ *", min_value=0.0, step=0.01, format="%.2f")
                    with col_a2:
                        precio_detal = st.number_input("Precio Detal $ *", min_value=0.0, step=0.01, format="%.2f")
                        precio_mayor = st.number_input("Precio Mayor $ *", min_value=0.0, step=0.01, format="%.2f")
                        min_mayor = st.number_input("Mín. Mayor *", min_value=1, value=6, step=1)
                    
                    if st.form_submit_button("📦 Registrar Producto", use_container_width=True):
                        if not nombre:
                            st.error("El nombre es obligatorio")
                        else:
                            try:
                                existe = db.table("inventario").select("*").eq("nombre", nombre).execute()
                                if existe.data:
                                    st.error(f"Ya existe '{nombre}'")
                                else:
                                    db.table("inventario").insert({
                                        "nombre": nombre,
                                        "stock": stock,
                                        "costo": costo,
                                        "precio_detal": precio_detal,
                                        "precio_mayor": precio_mayor,
                                        "min_mayor": min_mayor
                                    }).execute()
                                    st.success(f"Producto '{nombre}' registrado")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            
            with tab3:
                valor_inv = (df['stock'] * df['costo']).sum()
                valor_venta = (df['stock'] * df['precio_detal']).sum()
                bajo_stock = len(df[df['stock'] < 5])
                ganancia_potencial = valor_venta - valor_inv
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Valor inventario (costo)", formatear_usd(valor_inv))
                col_m2.metric("Valor venta potencial", formatear_usd(valor_venta))
                col_m3.metric("Productos con stock bajo", bajo_stock)
                
                st.metric("Ganancia potencial", formatear_usd(ganancia_potencial),
                         delta=f"{(ganancia_potencial/valor_inv*100):.1f}%" if valor_inv else "")
                
                st.subheader("Top 10 productos por valor")
                df_top = df.nlargest(10, 'stock')[['nombre', 'stock', 'costo']]
                df_top['valor'] = df_top['stock'] * df_top['costo']
                st.dataframe(df_top, use_container_width=True, hide_index=True)
        else:
            st.info("No hay productos en el inventario")
    except Exception as e:
        st.error(f"Error cargando inventario: {e}")

# ============================================
# MÓDULO 2: PUNTO DE VENTA
# ============================================
elif opcion == "🛒 PUNTO DE VENTA":
    requiere_turno()
    
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []
    
    id_turno = st.session_state.id_turno
    tasa = st.session_state.tasa_dia
    
    st.markdown("<h1 class='main-header'>🛒 Punto de Venta</h1>", unsafe_allow_html=True)
    st.info(f"Turno #{id_turno} | Tasa: {tasa:.2f} Bs/$")
    
    col_busqueda, col_carrito = st.columns([1.2, 1.8])
    
    with col_busqueda:
        st.subheader("🔍 Buscar productos")
        es_tasca = st.checkbox("🍷 Venta en tasca (+10%)")
        busqueda = st.text_input("", placeholder="Escribe nombre del producto...", key="buscar_venta")
        
        if busqueda:
            try:
                response = db.table("inventario")\
                    .select("*")\
                    .ilike("nombre", f"%{busqueda}%")\
                    .gt("stock", 0)\
                    .order("nombre")\
                    .limit(20)\
                    .execute()
                
                productos = response.data
                if productos:
                    for i in range(0, len(productos), 2):
                        cols = st.columns(2)
                        for j in range(2):
                            if i + j < len(productos):
                                prod = productos[i + j]
                                precio_base = float(prod['precio_detal'])
                                precio_unitario = precio_base * 1.10 if es_tasca else precio_base
                                with cols[j]:
                                    with st.container(border=True):
                                        st.markdown(f"**{prod['nombre']}**")
                                        st.caption(f"Stock: {prod['stock']:.0f}")
                                        st.markdown(f"**${precio_unitario:.2f}**")
                                        if st.button("➕ Agregar", key=f"add_{prod['id']}", use_container_width=True):
                                            encontrado = False
                                            for item in st.session_state.carrito:
                                                if item['id'] == prod['id']:
                                                    item['cantidad'] += 1
                                                    item['subtotal'] = item['cantidad'] * item['precio']
                                                    encontrado = True
                                                    break
                                            if not encontrado:
                                                st.session_state.carrito.append({
                                                    "id": prod['id'],
                                                    "nombre": prod['nombre'],
                                                    "cantidad": 1,
                                                    "precio": precio_unitario,
                                                    "costo": float(prod['costo']),
                                                    "subtotal": precio_unitario
                                                })
                                            st.rerun()
                else:
                    st.info("No se encontraron productos")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.info("Escribe algo para buscar")
    
    with col_carrito:
        st.subheader("🛒 Carrito")
        if not st.session_state.carrito:
            st.info("Carrito vacío")
        else:
            total_venta_usd = 0
            total_costo = 0
            
            for idx, item in enumerate(st.session_state.carrito):
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([2.5, 1, 1, 0.5])
                    with col1:
                        st.markdown(f"**{item['nombre']}**")
                    with col2:
                        nueva_cant = st.number_input(
                            "Cant.",
                            min_value=0.0,
                            value=float(item['cantidad']),
                            step=1.0,
                            key=f"cant_{idx}",
                            label_visibility="collapsed"
                        )
                        if nueva_cant != item['cantidad']:
                            if nueva_cant == 0:
                                st.session_state.carrito.pop(idx)
                            else:
                                item['cantidad'] = nueva_cant
                                item['subtotal'] = item['cantidad'] * item['precio']
                            st.rerun()
                    with col3:
                        st.markdown(f"**${item['subtotal']:.2f}**")
                    with col4:
                        if st.button("❌", key=f"del_{idx}"):
                            st.session_state.carrito.pop(idx)
                            st.rerun()
                    
                    total_venta_usd += item['subtotal']
                    total_costo += item['cantidad'] * item['costo']
            
            total_venta_bs = total_venta_usd * tasa
            
            st.divider()
            st.markdown(f"### Total USD: ${total_venta_usd:,.2f}")
            st.markdown(f"### Total Bs: {total_venta_bs:,.2f}")
            
            st.divider()
            with st.expander("💳 Detalle de pagos", expanded=True):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    pago_usd_efectivo = st.number_input("Efectivo USD", min_value=0.0, step=5.0, format="%.2f", key="p_usd_efectivo")
                    pago_zelle = st.number_input("Zelle USD", min_value=0.0, step=5.0, format="%.2f", key="p_zelle")
                    pago_otros_usd = st.number_input("Otros USD", min_value=0.0, step=5.0, format="%.2f", key="p_otros_usd")
                with col_p2:
                    pago_bs_efectivo = st.number_input("Efectivo Bs", min_value=0.0, step=100.0, format="%.2f", key="p_bs_efectivo")
                    pago_movil = st.number_input("Pago Móvil Bs", min_value=0.0, step=100.0, format="%.2f", key="p_movil")
                    pago_punto = st.number_input("Punto de Venta Bs", min_value=0.0, step=100.0, format="%.2f", key="p_punto")
                
                total_usd_recibido = pago_usd_efectivo + pago_zelle + pago_otros_usd
                total_bs_recibido = pago_bs_efectivo + pago_movil + pago_punto
                total_usd_equivalente = total_usd_recibido + (total_bs_recibido / tasa if tasa else 0)
                esperado_usd = total_venta_bs / tasa if tasa else 0
                vuelto_usd = total_usd_equivalente - esperado_usd
                
                st.divider()
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Pagado USD eq.", f"${total_usd_equivalente:,.2f}")
                col_r2.metric("Esperado USD", f"${esperado_usd:,.2f}")
                if vuelto_usd >= 0:
                    col_r3.metric("Vuelto USD", f"${vuelto_usd:,.2f}")
                    st.success(f"✅ Vuelto: ${vuelto_usd:.2f} / {(vuelto_usd*tasa):,.2f} Bs")
                else:
                    col_r3.metric("Faltante USD", f"${abs(vuelto_usd):,.2f}", delta_color="inverse")
                    st.error(f"❌ Faltante: ${abs(vuelto_usd):,.2f} / {(abs(vuelto_usd)*tasa):,.2f} Bs")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🔄 Limpiar carrito", use_container_width=True):
                    st.session_state.carrito = []
                    st.rerun()
            with col_btn2:
                if st.button("🚀 Finalizar venta", type="primary", use_container_width=True,
                             disabled=(vuelto_usd < -0.01 or not st.session_state.carrito)):
                    try:
                        # Actualizar stock
                        for item in st.session_state.carrito:
                            stock_actual = db.table("inventario").select("stock").eq("id", item['id']).execute().data[0]['stock']
                            db.table("inventario").update({
                                "stock": stock_actual - item['cantidad']
                            }).eq("id", item['id']).execute()
                        
                        # Guardar venta
                        items_resumen = [f"{item['cantidad']:.0f}x {item['nombre']}" for item in st.session_state.carrito]
                        venta_data = {
                            "id_cierre": id_turno,
                            "producto": ", ".join(items_resumen),
                            "cantidad": len(st.session_state.carrito),
                            "total_usd": round(total_venta_usd, 2),
                            "monto_cobrado_bs": round(total_venta_bs, 2),
                            "tasa_cambio": tasa,
                            "pago_divisas": round(pago_usd_efectivo, 2),
                            "pago_zelle": round(pago_zelle, 2),
                            "pago_otros": round(pago_otros_usd, 2),
                            "pago_efectivo": round(pago_bs_efectivo, 2),
                            "pago_movil": round(pago_movil, 2),
                            "pago_punto": round(pago_punto, 2),
                            "costo_venta": round(total_costo, 2),
                            "estado": "Finalizado",
                            "items": json.dumps(st.session_state.carrito),
                            "id_transaccion": str(int(datetime.now().timestamp())),
                            "fecha": datetime.now().isoformat()
                        }
                        db.table("ventas").insert(venta_data).execute()
                        
                        st.balloons()
                        st.success("Venta registrada")
                        with st.expander("🧾 Ticket", expanded=True):
                            st.markdown(f"""
                            <div style="background:white; padding:20px; border-radius:10px; border:2px solid #1e3c72;">
                                <h3 style="text-align:center;">MEDITERRANEO EXPRESS</h3>
                                <p style="text-align:center;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                                <p style="text-align:center;">Turno #{id_turno}</p>
                                <hr>
                                {''.join([f'<p>• {r}</p>' for r in items_resumen])}
                                <hr>
                                <p><b>Total USD:</b> ${total_venta_usd:,.2f}</p>
                                <p><b>Total Bs:</b> {total_venta_bs:,.2f}</p>
                                <p><b>Vuelto:</b> ${vuelto_usd:.2f} / {(vuelto_usd*tasa):,.2f} Bs</p>
                                <p style="text-align:center;">¡Gracias por su compra!</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.session_state.carrito = []
                        if st.button("🔄 Nueva venta"):
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ============================================
# MÓDULO 3: GASTOS
# ============================================
elif opcion == "💸 GASTOS":
    requiere_turno()
    
    id_turno = st.session_state.id_turno
    st.markdown("<h1 class='main-header'>💸 Gestión de Gastos</h1>", unsafe_allow_html=True)
    
    try:
        response = db.table("gastos").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        df_gastos = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        
        if not df_gastos.empty:
            st.subheader("📋 Gastos del turno")
            st.dataframe(
                df_gastos[['fecha', 'descripcion', 'monto_usd', 'categoria', 'estado']],
                use_container_width=True,
                hide_index=True
            )
            st.metric("Total gastos USD", f"${df_gastos['monto_usd'].sum():,.2f}")
        else:
            st.info("No hay gastos registrados en este turno")
    except Exception as e:
        st.error(f"Error cargando gastos: {e}")
    
    st.divider()
    with st.form("nuevo_gasto"):
        st.subheader("➕ Registrar nuevo gasto")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            descripcion = st.text_input("Descripción *", placeholder="Ej: Agua, café...")
            monto_usd = st.number_input("Monto USD *", min_value=0.01, step=0.01, format="%.2f")
        with col_g2:
            categoria = st.selectbox("Categoría", ["", "Servicios", "Insumos", "Personal", "Otros"])
            monto_bs_extra = st.number_input("Monto extra Bs (opcional)", min_value=0.0, step=10.0, format="%.2f")
        
        if st.form_submit_button("✅ Registrar gasto", use_container_width=True):
            if descripcion and monto_usd > 0:
                try:
                    gasto_data = {
                        "id_cierre": id_turno,
                        "descripcion": descripcion,
                        "monto_usd": monto_usd,
                        "estado": "activo",
                        "fecha": datetime.now().isoformat()
                    }
                    if categoria:
                        gasto_data["categoria"] = categoria
                    if monto_bs_extra > 0:
                        gasto_data["monto_bs_extra"] = monto_bs_extra
                    
                    db.table("gastos").insert(gasto_data).execute()
                    st.success("Gasto registrado")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Complete los campos obligatorios")

# ============================================
# MÓDULO 4: HISTORIAL (VERSIÓN PROFESIONAL)
# ============================================
elif opcion == "📜 HISTORIAL":
    requiere_turno()
    
    id_turno = st.session_state.id_turno
    tasa = st.session_state.get('tasa_dia', 1.0)
    
    st.markdown("<h1 class='main-header'>📜 Historial de Ventas</h1>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style='background-color: #e7f3ff; padding: 0.8rem; border-radius: 8px; margin-bottom: 1.5rem;'>
            <span style='font-weight:600;'>📍 Turno #{id_turno}</span> | 
            <span>💱 Tasa: {tasa:.2f} Bs/$</span>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        response = db.table("ventas").select("*").eq("id_cierre", id_turno).order("fecha", desc=True).execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        
        if not df.empty:
            # Procesar fechas
            df['fecha_dt'] = pd.to_datetime(df['fecha'])
            df['hora'] = df['fecha_dt'].dt.strftime('%H:%M')
            df['fecha_corta'] = df['fecha_dt'].dt.strftime('%d/%m/%Y')
            df['fecha_display'] = df['fecha_dt'].dt.strftime('%d/%m/%Y %H:%M')
            
            # ============================================
            # FILTROS MEJORADOS
            # ============================================
            col_filtro1, col_filtro2, col_filtro3, col_filtro4 = st.columns([1.5, 1, 1, 1])
            
            with col_filtro1:
                fecha_filtro = st.text_input("📅 Filtrar por fecha", placeholder="DD/MM/AAAA", key="filtro_fecha")
            
            with col_filtro2:
                estado_filtro = st.selectbox(
                    "Estado",
                    ["Todos", "Finalizado", "Anulado"],
                    key="filtro_estado"
                )
            
            with col_filtro3:
                buscar_texto = st.text_input("🔍 Buscar producto", placeholder="Ej: Ron...", key="filtro_buscar")
            
            with col_filtro4:
                st.markdown("<br>", unsafe_allow_html=True)  # Espaciado para alinear
                ver_solo_activas = st.checkbox("Solo ventas activas", value=False, key="filtro_activas")
            
            # Aplicar filtros
            df_filtrado = df.copy()
            
            if fecha_filtro:
                df_filtrado = df_filtrado[df_filtrado['fecha_corta'].str.contains(fecha_filtro, na=False)]
            
            if estado_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['estado'] == estado_filtro]
            
            if buscar_texto:
                df_filtrado = df_filtrado[df_filtrado['producto'].str.contains(buscar_texto, case=False, na=False)]
            
            if ver_solo_activas:
                df_filtrado = df_filtrado[df_filtrado['estado'] != 'Anulado']
            
            # ============================================
            # MÉTRICAS SUPERIORES
            # ============================================
            if not df_filtrado.empty:
                # Calcular métricas
                total_usd = df_filtrado[df_filtrado['estado'] != 'Anulado']['total_usd'].sum() if any(df_filtrado['estado'] != 'Anulado') else 0
                total_bs = df_filtrado[df_filtrado['estado'] != 'Anulado']['monto_cobrado_bs'].sum() if any(df_filtrado['estado'] != 'Anulado') else 0
                cantidad_ventas = len(df_filtrado[df_filtrado['estado'] != 'Anulado'])
                promedio_usd = total_usd / cantidad_ventas if cantidad_ventas > 0 else 0
                
                # Mostrar métricas en tarjetas
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                
                with col_m1:
                    st.markdown("""
                        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 1rem; border-radius: 10px; color: white; text-align: center;'>
                            <span style='font-size: 0.9rem; opacity: 0.9;'>💰 TOTAL USD</span><br>
                            <span style='font-size: 1.8rem; font-weight: 700;'>${:,.2f}</span>
                        </div>
                    """.format(total_usd), unsafe_allow_html=True)
                
                with col_m2:
                    st.markdown("""
                        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                                padding: 1rem; border-radius: 10px; color: white; text-align: center;'>
                            <span style='font-size: 0.9rem; opacity: 0.9;'>💵 TOTAL BS</span><br>
                            <span style='font-size: 1.8rem; font-weight: 700;'>{:,.0f}</span>
                        </div>
                    """.format(total_bs), unsafe_allow_html=True)
                
                with col_m3:
                    st.markdown("""
                        <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                                padding: 1rem; border-radius: 10px; color: white; text-align: center;'>
                            <span style='font-size: 0.9rem; opacity: 0.9;'>📊 VENTAS</span><br>
                            <span style='font-size: 1.8rem; font-weight: 700;'>{}</span>
                        </div>
                    """.format(cantidad_ventas), unsafe_allow_html=True)
                
                with col_m4:
                    st.markdown("""
                        <div style='background: linear-gradient(135deg, #5f2c82 0%, #49a09d 100%); 
                                padding: 1rem; border-radius: 10px; color: white; text-align: center;'>
                            <span style='font-size: 0.9rem; opacity: 0.9;'>📈 PROMEDIO</span><br>
                            <span style='font-size: 1.8rem; font-weight: 700;'>${:,.2f}</span>
                        </div>
                    """.format(promedio_usd), unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # ============================================
                # TABLA DE VENTAS (DISEÑO PROFESIONAL)
                # ============================================
                st.markdown("""
                    <style>
                    .venta-row {
                        display: flex;
                        align-items: center;
                        padding: 0.8rem;
                        margin: 0.2rem 0;
                        border-radius: 8px;
                        transition: all 0.2s;
                    }
                    .venta-row:hover {
                        transform: translateX(5px);
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    .venta-finalizada {
                        background-color: #ffffff;
                        border-left: 4px solid #28a745;
                    }
                    .venta-anulada {
                        background-color: #f8f9fa;
                        border-left: 4px solid #dc3545;
                        opacity: 0.7;
                    }
                    .badge-finalizada {
                        background-color: #28a745;
                        color: white;
                        padding: 0.2rem 0.6rem;
                        border-radius: 12px;
                        font-size: 0.7rem;
                        font-weight: 600;
                    }
                    .badge-anulada {
                        background-color: #dc3545;
                        color: white;
                        padding: 0.2rem 0.6rem;
                        border-radius: 12px;
                        font-size: 0.7rem;
                        font-weight: 600;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                # Cabecera de la tabla
                col_h1, col_h2, col_h3, col_h4, col_h5, col_h6, col_h7 = st.columns([0.8, 0.8, 2.5, 1.2, 1.2, 0.8, 0.8])
                with col_h1:
                    st.markdown("**ID**")
                with col_h2:
                    st.markdown("**Hora**")
                with col_h3:
                    st.markdown("**Productos**")
                with col_h4:
                    st.markdown("**Total USD**")
                with col_h5:
                    st.markdown("**Total Bs**")
                with col_h6:
                    st.markdown("**Estado**")
                with col_h7:
                    st.markdown("**Acción**")
                
                st.markdown("<hr style='margin:0; margin-bottom:0.5rem;'>", unsafe_allow_html=True)
                
                # Mostrar cada venta
                for idx, venta in df_filtrado.iterrows():
                    es_anulado = venta['estado'] == 'Anulado'
                    
                    # Determinar clase CSS
                    row_class = "venta-anulada" if es_anulado else "venta-finalizada"
                    badge = '<span class="badge-anulada">ANULADA</span>' if es_anulado else '<span class="badge-finalizada">FINALIZADA</span>'
                    
                    # Limitar longitud de productos
                    productos = venta['producto']
                    if len(productos) > 40:
                        productos = productos[:40] + "..."
                    
                    # Crear fila con estilo
                    cols = st.columns([0.8, 0.8, 2.5, 1.2, 1.2, 0.8, 0.8])
                    
                    with cols[0]:
                        st.markdown(f"<span style='font-weight:500;'>#{venta['id']}</span>", unsafe_allow_html=True)
                    
                    with cols[1]:
                        st.markdown(f"<span>{venta['hora']}</span>", unsafe_allow_html=True)
                    
                    with cols[2]:
                        st.markdown(f"<span title='{venta['producto']}'>{productos}</span>", unsafe_allow_html=True)
                    
                    with cols[3]:
                        st.markdown(f"<span style='font-weight:600;'>${venta['total_usd']:,.2f}</span>", unsafe_allow_html=True)
                    
                    with cols[4]:
                        st.markdown(f"<span>{venta['monto_cobrado_bs']:,.0f}</span>", unsafe_allow_html=True)
                    
                    with cols[5]:
                        st.markdown(badge, unsafe_allow_html=True)
                    
                    with cols[6]:
                        if not es_anulado:
                            if st.button("🚫", key=f"btn_anular_{venta['id']}", help="Anular venta"):
                                try:
                                    # Obtener items de la venta
                                    items = venta.get('items')
                                    
                                    # Convertir string a lista si es necesario
                                    if isinstance(items, str):
                                        items = json.loads(items)
                                    
                                    # Verificar que items sea una lista válida
                                    if items and isinstance(items, list):
                                        for item in items:
                                            if 'id' in item and 'cantidad' in item:
                                                # Obtener stock actual
                                                stock_res = db.table("inventario").select("stock").eq("id", item['id']).execute()
                                                if stock_res.data:
                                                    stock_actual = stock_res.data[0]['stock']
                                                    # Devolver stock
                                                    db.table("inventario").update({
                                                        "stock": stock_actual + item['cantidad']
                                                    }).eq("id", item['id']).execute()
                                    
                                    # Marcar venta como anulada
                                    db.table("ventas").update({"estado": "Anulado"}).eq("id", venta['id']).execute()
                                    
                                    st.success(f"✅ Venta #{venta['id']} anulada correctamente")
                                    time.sleep(1)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error al anular: {e}")
                        else:
                            st.markdown("—")
                    
                    # Línea separadora sutil
                    if idx < len(df_filtrado) - 1:
                        st.markdown("<hr style='margin:0.2rem 0; opacity:0.3;'>", unsafe_allow_html=True)
                
                # ============================================
                # PIE DE TABLA CON TOTALES
                # ============================================
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Calcular totales de las ventas mostradas (solo activas)
                df_activas_filtrado = df_filtrado[df_filtrado['estado'] != 'Anulado']
                
                if not df_activas_filtrado.empty:
                    total_usd_filtrado = df_activas_filtrado['total_usd'].sum()
                    total_bs_filtrado = df_activas_filtrado['monto_cobrado_bs'].sum()
                    
                    st.markdown(f"""
                        <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <span style='font-weight:600;'>📊 TOTALES EN PANTALLA (ventas activas):</span>
                                <span>
                                    <span style='color: #28a745; font-weight:600;'>${total_usd_filtrado:,.2f}</span> | 
                                    <span style='color: #007bff; font-weight:600;'>{total_bs_filtrado:,.0f} Bs</span>
                                </span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📭 No hay ventas que coincidan con los filtros seleccionados")
        else:
            st.info("📭 No hay ventas registradas en este turno")
            
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        st.exception(e)  # Solo para depuración, puedes quitarlo después
        
# ============================================
# MÓDULO 5: CIERRE DE CAJA
# ============================================
elif opcion == "📊 CIERRE DE CAJA":
    st.markdown("<h1 class='main-header'>📊 Cierre de Caja</h1>", unsafe_allow_html=True)
    
    if not st.session_state.id_turno:
        st.warning("🔓 No hay turno activo. Complete para abrir caja:")
        with st.form("apertura"):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                tasa_apertura = st.number_input("Tasa del día (Bs/$)", min_value=1.0, value=60.0, step=0.5, format="%.2f")
                fondo_bs = st.number_input("Fondo inicial Bs", min_value=0.0, value=0.0, step=10.0, format="%.2f")
            with col_a2:
                fondo_usd = st.number_input("Fondo inicial USD", min_value=0.0, value=0.0, step=5.0, format="%.2f")
            
            if st.form_submit_button("🚀 Abrir caja", type="primary", use_container_width=True):
                try:
                    data = {
                        "tasa_apertura": tasa_apertura,
                        "fondo_bs": fondo_bs,
                        "fondo_usd": fondo_usd,
                        "monto_apertura": fondo_usd,
                        "estado": "abierto",
                        "fecha_apertura": datetime.now().isoformat()
                    }
                    res = db.table("cierres").insert(data).execute()
                    if res.data:
                        st.session_state.id_turno = res.data[0]['id']
                        st.session_state.tasa_dia = tasa_apertura
                        st.success(f"Turno #{res.data[0]['id']} abierto")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        id_turno = st.session_state.id_turno
        tasa = st.session_state.tasa_dia
        
        # Obtener ventas y gastos
        ventas_res = db.table("ventas").select("*").eq("id_cierre", id_turno).eq("estado", "Finalizado").execute()
        ventas = ventas_res.data if ventas_res.data else []
        total_ventas_usd = sum(v['total_usd'] for v in ventas)
        total_costos = sum(v['costo_venta'] for v in ventas)
        ganancia_bruta = total_ventas_usd - total_costos
        
        gastos_res = db.table("gastos").select("*").eq("id_cierre", id_turno).execute()
        gastos = gastos_res.data if gastos_res.data else []
        total_gastos = sum(g['monto_usd'] for g in gastos)
        
        st.subheader("📈 Resumen del turno")
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        col_r1.metric("Ventas totales", formatear_usd(total_ventas_usd))
        col_r2.metric("Costo de ventas", formatear_usd(total_costos))
        col_r3.metric("Ganancia bruta", formatear_usd(ganancia_bruta))
        col_r4.metric("Gastos", formatear_usd(total_gastos))
        
        ganancia_neta = ganancia_bruta - total_gastos
        st.metric("💰 GANANCIA NETA", formatear_usd(ganancia_neta))
        st.info(f"💰 Para reponer mercancía: {formatear_usd(total_costos)}")
        
        st.divider()
        st.subheader("🧮 Conteo físico para cierre")
        
        with st.form("cierre"):
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                efec_bs_fisico = st.number_input("Efectivo Bs físico", min_value=0.0, value=0.0, format="%.2f")
                efec_usd_fisico = st.number_input("Efectivo USD físico", min_value=0.0, value=0.0, format="%.2f")
            with col_c2:
                pmovil_fisico = st.number_input("Pago Móvil Bs", min_value=0.0, value=0.0, format="%.2f")
                punto_fisico = st.number_input("Punto Venta Bs", min_value=0.0, value=0.0, format="%.2f")
            with col_c3:
                zelle_fisico = st.number_input("Zelle USD", min_value=0.0, value=0.0, format="%.2f")
                otros_fisico = st.number_input("Otros USD", min_value=0.0, value=0.0, format="%.2f")
            
            # Calcular esperados
            esperado_bs = st.session_state.fondo_bs + (total_ventas_usd * tasa) - (total_gastos * tasa)
            esperado_usd = st.session_state.fondo_usd + total_ventas_usd - total_gastos
            fisico_bs = efec_bs_fisico + pmovil_fisico + punto_fisico
            fisico_usd = efec_usd_fisico + zelle_fisico + otros_fisico
            diferencia_bs = fisico_bs - esperado_bs
            diferencia_usd = fisico_usd - esperado_usd
            diferencia_total_usd = diferencia_usd + (diferencia_bs / tasa if tasa else 0)
            
            st.divider()
            st.markdown("**Resultado del conteo**")
            col_d1, col_d2 = st.columns(2)
            col_d1.metric("Esperado Bs", formatear_bs(esperado_bs))
            col_d2.metric("Físico Bs", formatear_bs(fisico_bs), delta=f"{diferencia_bs:+,.2f} Bs")
            col_d1.metric("Esperado USD", formatear_usd(esperado_usd))
            col_d2.metric("Físico USD", formatear_usd(fisico_usd), delta=f"${diferencia_usd:+,.2f}")
            
            if abs(diferencia_total_usd) < 0.1:
                st.success("✅ CAJA CUADRADA")
            elif diferencia_total_usd > 0:
                st.info(f"🟢 SOBRANTE: +${diferencia_total_usd:,.2f} USD")
            else:
                st.error(f"🔴 FALTANTE: -${abs(diferencia_total_usd):,.2f} USD")
            
            st.warning("⚠️ Una vez cerrado, no podrá modificar ventas de este turno.")
            confirmar = st.checkbox("Confirmo que los datos son correctos")
            
            if st.form_submit_button("🔒 CERRAR TURNO", type="primary", disabled=not confirmar):
                try:
                    update_data = {
                        "fecha_cierre": datetime.now().isoformat(),
                        "total_ventas": total_ventas_usd,
                        "total_costos": total_costos,
                        "total_ganancias": ganancia_neta,
                        "diferencia": diferencia_total_usd,
                        "tasa_cierre": tasa,
                        "estado": "cerrado"
                    }
                    db.table("cierres").update(update_data).eq("id", id_turno).execute()
                    db.table("gastos").update({"estado": "cerrado"}).eq("id_cierre", id_turno).execute()
                    
                    st.session_state.id_turno = None
                    st.session_state.carrito = []
                    st.balloons()
                    st.success("Turno cerrado exitosamente")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al cerrar: {e}")
