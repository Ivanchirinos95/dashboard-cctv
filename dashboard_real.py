import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la interfaz de alto impacto
st.set_page_config(page_title="Sistema de Analítica CCTV", layout="wide")
st.title("🛡️ Centro de Control e Inteligencia Operativa VMT - CCTV")
st.markdown("Interactividad Cruzada Multigráfico: Haz clic en las barras de cualquier gráfico para cruzar información en tiempo real.")

# 2. Carga, Normalización y Mapeo del CSV real
@st.cache_data
def preparar_datos_central():
    ruta = "DATA/OPERADOR/1-15 OP. CÁMARAS JUNIO (TOTAL).csv"
    df = pd.read_csv(ruta, encoding='utf-8', sep=';')
    
    # Limpieza de títulos de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Renombrado de variables del formulario
    df = df.rename(columns={
        'Marca temporal': 'FECHA',
        'TURNO DE OPERACIÓN:': 'TURNO',
        'APELLIDOS Y NOMBRES': 'OPERADOR',
        'NÚMERO DE CÁMARA:': 'CAMARA',
        'SECTOR': 'ZONA',  
        'MODALIDAD': 'MODALIDAD',
        'TÍTULO DE LA OCURRENCIA:': 'TITULO',
        'DESCRIPCIÓN DETALLADA DE LA OCURRENCIA:': 'DESCRIPCIÓN'
    })
    
    # Normalización del formato del número de cámara
    if 'CAMARA' in df.columns:
        df['CAMARA'] = df['CAMARA'].fillna('S/N').astype(str).str.replace('.0', '', regex=False).str.strip()

    # Limpieza de textos generales
    columnas_texto = ['TURNO', 'OPERADOR', 'ZONA', 'MODALIDAD', 'TITULO', 'DESCRIPCIÓN']
    for col in columnas_texto:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Forzamos el formato exacto de tu Google Forms / Excel
    if 'FECHA' in df.columns:
        df['FECHA_LIMPIA'] = df['FECHA'].astype(str).str.strip()
        
        df['FECHA_DT'] = pd.to_datetime(
            df['FECHA_LIMPIA'], 
            format='%d/%m/%Y %H:%M:%S', 
            errors='coerce'
        )
        
        filas_vacias = df['FECHA_DT'].isna()
        if filas_vacias.any():
            df.loc[filas_vacias, 'FECHA_DT'] = pd.to_datetime(
                df.loc[filas_vacias, 'FECHA_LIMPIA'], 
                format='%d/%m/%Y %H:%M', 
                errors='coerce'
            )
            
        df['FECHA'] = df['FECHA_DT'].dt.date
            
    return df

df_base = preparar_datos_central()

# 3. BARRA LATERAL - FILTROS NATIVOS CON COMPORTAMIENTO DE BORRADO INTEGRADO
st.sidebar.header("⚙️ Filtros Base")
with st.sidebar.expander("🔍 FILTROS MANUALES COMPLEMENTARIOS", expanded=False):

    # Inicializamos la variable de filtros acumulativos una sola vez
    df_filtros = df_base.copy()

    # --- FILTRO 1: FECHA (Removido 'clearable' conflictivo) ---
    lista_fecha = sorted(df_filtros['FECHA'].dropna().unique().tolist())
    fecha_sel = st.selectbox(
        "Filtrar por Fecha:", 
        lista_fecha,
        index=None,                  # Permite que empiece vacío para habilitar el borrado
        placeholder="Todos los días", 
        format_func=lambda x: x.strftime('%d/%m/%Y') if x is not None else "Todos los días"
    )
    if fecha_sel:
        df_filtros = df_filtros[df_filtros['FECHA'] == fecha_sel]

    # --- FILTRO 2: TURNO ---
    lista_turnos = sorted(df_filtros['TURNO'].dropna().unique().tolist())
    turno_sel = st.selectbox(
        "Filtrar por Turno:", lista_turnos, 
        index=None, placeholder="Todos los turnos"
    )
    if turno_sel:
        df_filtros = df_filtros[df_filtros['TURNO'] == turno_sel]

    # --- FILTRO 3: SECTOR / ZONA ---
    lista_sector = sorted(df_filtros['ZONA'].dropna().unique().tolist())
    sector_sel = st.selectbox(
        "Filtrar por Sector:", lista_sector, 
        index=None, placeholder="Todos los sectores"
    )
    if sector_sel:
        df_filtros = df_filtros[df_filtros['ZONA'] == sector_sel]

    # --- FILTRO 4: OPERADOR ---
    lista_operador = sorted(df_filtros['OPERADOR'].dropna().unique().tolist())
    operador_sel = st.selectbox(
        "Filtrar por Operador:", lista_operador, 
        index=None, placeholder="Todos los operadores"
    )
    if operador_sel:
        df_filtros = df_filtros[df_filtros['OPERADOR'] == operador_sel]

    # --- FILTRO 5: MODALIDAD ---
    lista_modalidad = sorted(df_filtros['MODALIDAD'].dropna().unique().tolist())
    modalidad_Sel = st.selectbox(
        "filtrar por Modalidad", lista_modalidad,
        index=None, placeholder="Todas las Modalidades"
    )   
    if modalidad_Sel:
        df_filtros = df_filtros[df_filtros['MODALIDAD'] == modalidad_Sel]

    # --- FILTRO 5: N° DE CÁMARA ---
    lista_camaras = sorted(df_filtros['CAMARA'].dropna().unique().tolist(), key=lambda x: int(x) if x.isdigit() else 999)
    camara_sel = st.selectbox(
        "Filtrar por N° de Cámara:", lista_camaras, 
        index=None, placeholder="Todas las cámaras"
    )
    if camara_sel:
        df_filtros = df_filtros[df_filtros['CAMARA'] == camara_sel]

    # --- FILTRO 6: TÍTULO DE INCIDENTE ---
    lista_titulos = sorted(df_filtros['TITULO'].dropna().unique().tolist())
    titulo_sel = st.selectbox(
        "Filtrar por Título de Incidente:", lista_titulos, 
        index=None, placeholder="Todos los incidentes"
    )
    if titulo_sel:
        df_filtros = df_filtros[df_filtros['TITULO'] == titulo_sel]

# =============================================================================
# 4. ARQUITECTURA DE INTERACTIVIDAD CRUZADA POR CLICS (CALLBACKS DE SELECCIÓN)
# =============================================================================

# Lista centralizada de modalidades consideradas críticas/fuertes
modalidades_fuertes = [
    'PRESUNTO HOMICIDIO', 'PRESUNTO FEMINICIDIO', 'PRESUNTO SICARIATO', 'PRESUNTAS LESIONES LEVES Y GRAVES',
    'PRESUNTA EXPOSICIÓN A PELIGRO O ABANDONO DE PERSONAS', 'PRESUNTO ROBO DE VEHÍCULOS (MAYORES Y MENORES)', 
    'PRESUNTO ROBO A PERSONAS', 'PRESUNTO ROBO DE CASA HABITADA', 'PRESUNTO ROBO A EMPRESAS PARTICULARES Y ESTATALES', 
    'PRESUNTO HURTO DE VEHÍCULOS (MAYORES Y MENORES)', 'PRESUNTO DELITO DE PELIGRO COMÚN (CREAR INCENDIO O EXPLOSIÓN, CONDUCCIÓN O MANIPULACIÓN EN ESTADO DE EBRIEDAD O DROGADICCIÓN, FABRICACIÓN, TRÁFICO O TENENCIA DE ARMAS, EXPLOSIVOS Y PIROTÉCNICOS)', 
    'PRESUNTAS LESIONES (MUY LEVES)', 'PRESUNTAS PELEAS CALLEJERAS CON LESIONES MUY LEVES O SIN LESIONES', 
    'PRESUNTO ATROPELLO', 'PRESUNTO CHOQUE', 'PRESUNTO DELITO CONTRA LA LIBERTAD PERSONAL',
    'PRESUNTA VIOLACIÓN A LA LIBERTAD SEXUAL', 'OTROS PRESUNTOS DELITOS', 'PRESUNTA ACTIVIDAD CONTRA LA PAZ PÚBLICA '
]

# Inicialización limpia de estados en Session State para evitar el desfase (Delay)
if 'zona_sel_clic' not in st.session_state: st.session_state.zona_sel_clic = None
if 'mod_sel_clic' not in st.session_state: st.session_state.mod_sel_clic = None
if 'op_sel_clic' not in st.session_state: st.session_state.op_sel_clic = None
if 'origen_op_clic' not in st.session_state: st.session_state.origen_op_clic = None # 'general' o 'fuerte'

# --- APLICACIÓN EN CASCADA DE FILTROS POR CLIC ---
df_dinamico = df_filtros.copy()

# Si hay un operador seleccionado abajo, filtramos la data base de los gráficos superiores primero
if st.session_state.op_sel_clic:
    df_dinamico = df_dinamico[df_dinamico['OPERADOR'] == st.session_state.op_sel_clic]
    if st.session_state.origen_op_clic == 'fuerte':
        df_dinamico = df_dinamico[df_dinamico['MODALIDAD'].str.upper().isin([m.upper() for m in modalidades_fuertes])]

# Fila superior de gráficos (Zonas y Modalidades)
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("📍 Filtro 1: Selecciona un Sector")
    conteo_zonas = df_dinamico['ZONA'].value_counts().reset_index()
    conteo_zonas.columns = ['ZONA', 'CANTIDAD']
    
    fig_zonas = px.bar(conteo_zonas, x='CANTIDAD', y='ZONA', orientation='h',
                       text_auto=True, color='ZONA', title="Clic para aislar un Sector Municipal")
    fig_zonas.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
    
    clic_z = st.plotly_chart(fig_zonas, use_container_width=True, on_select="rerun")
    
    # Manejo del estado del Filtro 1
    if clic_z and "selection" in clic_z and "points" in clic_z["selection"] and len(clic_z["selection"]["points"]) > 0:
        nueva_zona = clic_z["selection"]["points"][0]["y"]
        if nueva_zona != st.session_state.zona_sel_clic:
            st.session_state.zona_sel_clic = nueva_zona
            st.rerun()
    elif clic_z and "selection" in clic_z and len(clic_z["selection"]["points"]) == 0 and st.session_state.zona_sel_clic is not None:
        st.session_state.zona_sel_clic = None
        st.rerun()

with col_g2:
    st.subheader("🛠️ Filtro 2: Selecciona una Modalidad")
    df_previo_mod = df_dinamico.copy()
    if st.session_state.zona_sel_clic:
        df_previo_mod = df_previo_mod[df_previo_mod['ZONA'] == st.session_state.zona_sel_clic]
        
    conteo_mod = df_previo_mod['MODALIDAD'].value_counts().head(10).reset_index()
    conteo_mod.columns = ['MODALIDAD', 'CANTIDAD']
    conteo_mod['MODALIDAD_CORTA'] = conteo_mod['MODALIDAD'].apply(lambda x: x if len(str(x)) <= 25 else str(x)[:22] + "...")
    
    fig_mod = px.bar(conteo_mod, x='CANTIDAD', y='MODALIDAD_CORTA', orientation='h',
                     text_auto=True, color='MODALIDAD_CORTA', hover_name='MODALIDAD',
                     title="Clic para aislar una Modalidad de Incidente")
    fig_mod.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending', 'title': 'Modalidad'})
    
    clic_m = st.plotly_chart(fig_mod, use_container_width=True, on_select="rerun")
    
    # Manejo del estado del Filtro 2
    if clic_m and "selection" in clic_m and "points" in clic_m["selection"] and len(clic_m["selection"]["points"]) > 0:
        idx_sel = clic_m["selection"]["points"][0]["point_index"]
        nueva_mod = conteo_mod.loc[idx_sel, 'MODALIDAD']
        if nueva_mod != st.session_state.mod_sel_clic:
            st.session_state.mod_sel_clic = nueva_mod
            st.rerun()
    elif clic_m and "selection" in clic_m and len(clic_m["selection"]["points"]) == 0 and st.session_state.mod_sel_clic is not None:
        st.session_state.mod_sel_clic = None
        st.rerun()

st.divider()


# =============================================================================
# 5. CONSOLIDACIÓN DE LA DATA FINAL FILTRADA POR CLICS MÚLTIPLES
# =============================================================================
df_final = df_filtros.copy()
filtros_activos_mensajes = []

# Aplicamos los filtros almacenados en el estado de forma síncrona
if st.session_state.zona_sel_clic:
    df_final = df_final[df_final['ZONA'] == st.session_state.zona_sel_clic]
    filtros_activos_mensajes.append(f"📍 Sector: **{st.session_state.zona_sel_clic}**")

if st.session_state.mod_sel_clic:
    df_final = df_final[df_final['MODALIDAD'] == st.session_state.mod_sel_clic]
    filtros_activos_mensajes.append(f"🛠️ Modalidad: **{st.session_state.mod_sel_clic}**")

if st.session_state.op_sel_clic:
    df_final = df_final[df_final['OPERADOR'] == st.session_state.op_sel_clic]
    if st.session_state.origen_op_clic == 'fuerte':
        df_final = df_final[df_final['MODALIDAD'].str.upper().isin([m.upper() for m in modalidades_fuertes])]
        filtros_activos_mensajes.append(f"🚨 Auditoría Crítica: **{st.session_state.op_sel_clic}**")
    else:
        filtros_activos_mensajes.append(f"👤 Carga Operador: **{st.session_state.op_sel_clic}**")

# Despliegue de métricas tácticas (KPIs) en la parte superior
st.subheader("📊 Métricas del Grupo Filtrado")
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

with col_kpi1:
    st.metric(label="Incidentes en Pantalla", value=len(df_final))
    
with col_kpi2:
    camara_top = df_final['CAMARA'].mode()[0] if not df_final.empty else "N/A"
    st.metric(label="Cámara más Reportada", value=f"N° {camara_top}" if camara_top != "N/A" else "N/A")
    
with col_kpi3:
    turno_top = df_final['TURNO'].mode()[0] if not df_final.empty else "N/A"
    st.metric(label="Turno con Mayor Alerta", value=turno_top)

st.divider()


# =============================================================================
# 👥 FILA COMPARATIVA DE PERSONAL: RENDIMIENTO GENERAL VS CASOS FUERTES
# =============================================================================
col_g3, col_g4 = st.columns(2)

# Data base para la sección de operadores (respeta Filtro 1 y Filtro 2 si están activos)
df_ops_base = df_filtros.copy()
if st.session_state.zona_sel_clic:
    df_ops_base = df_ops_base[df_ops_base['ZONA'] == st.session_state.zona_sel_clic]
if st.session_state.mod_sel_clic:
    df_ops_base = df_ops_base[df_ops_base['MODALIDAD'] == st.session_state.mod_sel_clic]

# --- FILTRO 3: RENDIMIENTO GENERAL (IZQUIERDA) ---
with col_g3:
    st.subheader("👤 Filtro 3: Rendimiento y Carga General")
    
    conteo_op = df_ops_base['OPERADOR'].value_counts().reset_index()
    conteo_op.columns = ['OPERADOR', 'CANTIDAD']
    conteo_op['SOLO_APELLIDO'] = conteo_op['OPERADOR'].apply(lambda x: str(x).split()[0] if pd.notna(x) and str(x).strip() != '' else 'S/N')
    conteo_op_top = conteo_op.head(10)
    
    fig_op = px.bar(
        conteo_op_top, x='CANTIDAD', y='SOLO_APELLIDO', orientation='h',
        text_auto=True, color='SOLO_APELLIDO', hover_name='OPERADOR',
        title="Total de registros por Operador (Top 10)"
    )
    fig_op.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending', 'title': 'Personal (Apellido)'}, xaxis={'title': 'Cantidad Total'})
    
    clic_o = st.plotly_chart(fig_op, use_container_width=True, on_select="rerun")
    
    # Control síncrono del Filtro 3
    if clic_o and "selection" in clic_o and "points" in clic_o["selection"] and len(clic_o["selection"]["points"]) > 0:
        idx_op = clic_o["selection"]["points"][0]["point_index"]
        sel_op = conteo_op_top.loc[idx_op, 'OPERADOR']
        if st.session_state.op_sel_clic != sel_op or st.session_state.origen_op_clic != 'general':
            st.session_state.op_sel_clic = sel_op
            st.session_state.origen_op_clic = 'general'
            st.rerun()
    elif clic_o and "selection" in clic_o and len(clic_o["selection"]["points"]) == 0 and st.session_state.origen_op_clic == 'general':
        st.session_state.op_sel_clic = None
        st.session_state.origen_op_clic = None
        st.rerun()


# --- FILTRO 4: CASOS FUERTES (DERECHA) ---
with col_g4:
    st.subheader("🚨 Filtro 4: Operadores en Casos Fuertes")
    
    df_fuertes = df_ops_base[df_ops_base['MODALIDAD'].str.upper().isin([m.upper() for m in modalidades_fuertes])]
    
    if not df_fuertes.empty:
        conteo_fuertes = df_fuertes['OPERADOR'].value_counts().reset_index()
        conteo_fuertes.columns = ['OPERADOR', 'CANTIDAD']
        conteo_fuertes['SOLO_APELLIDO'] = conteo_fuertes['OPERADOR'].apply(lambda x: str(x).split()[0] if pd.notna(x) and str(x).strip() != '' else 'S/N')
        conteo_fuertes_top = conteo_fuertes.head(10)
        
        fig_fuertes = px.bar(
            conteo_fuertes_top, x='CANTIDAD', y='SOLO_APELLIDO', orientation='h',
            text_auto=True, color_discrete_sequence=['#FF4B4B'], hover_name='OPERADOR',
            title="Incidentes Críticos por Operador (Top 10)"
        )
        fig_fuertes.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending', 'title': 'Personal (Casos Críticos)'}, xaxis={'title': 'Cantidad Críticos'})
        
        clic_f = st.plotly_chart(fig_fuertes, use_container_width=True, on_select="rerun")
        
        # Control síncrono del Filtro 4
        if clic_f and "selection" in clic_f and "points" in clic_f["selection"] and len(clic_f["selection"]["points"]) > 0:
            idx_f = clic_f["selection"]["points"][0]["point_index"]
            sel_op_f = conteo_fuertes_top.loc[idx_f, 'OPERADOR']
            if st.session_state.op_sel_clic != sel_op_f or st.session_state.origen_op_clic != 'fuerte':
                st.session_state.op_sel_clic = sel_op_f
                st.session_state.origen_op_clic = 'fuerte'
                st.rerun()
        elif clic_f and "selection" in clic_f and len(clic_f["selection"]["points"]) == 0 and st.session_state.origen_op_clic == 'fuerte':
            st.session_state.op_sel_clic = None
            st.session_state.origen_op_clic = None
            st.rerun()
    else:
        st.warning("⚠️ No se encontraron incidentes fuertes.")

st.divider()

# Mensajes de control informativos
if filtros_activos_mensajes:
    st.info("🎯 **Filtros por Clic Activos:** " + " | ".join(filtros_activos_mensajes) + " *(Haz un clic en la barra activa para liberar el panel al instante)*")


# =============================================================================
# 6. MÓDULO DE PRECISIÓN: Cálculo dinámico de incidentes por número de cámara
# =============================================================================
if not df_final.empty:
    df_final['INCIDENTES_DE_ESTA_CAMARA'] = df_final.groupby('CAMARA')['CAMARA'].transform('count')
else:
    df_final['INCIDENTES_DE_ESTA_CAMARA'] = 0


# =============================================================================
# 7. REGISTRO DETALLADO CON BLOQUEO DE DESCARGA POR INYECCIÓN CSS
# =============================================================================
st.subheader("📋 Registro Detallado y Bitácora de Eventos")

st.markdown(
    """
    <style>
    button[title="Download as CSV"], 
    .stDataFrame [data-testid="stBaseButton-toolbar"],
    [data-testid="stElementToolbar"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

columnas_vista = [
    'FECHA', 'OPERADOR', 'TURNO', 'CAMARA', 'INCIDENTES_DE_ESTA_CAMARA', 
    'TITULO', 'DESCRIPCIÓN'
]

st.dataframe(df_final[columnas_vista], use_container_width=True)
