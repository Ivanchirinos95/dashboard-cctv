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
    ruta = r"D:\DATOS IVAN NO TOCAR\VS CODE\DATA\OPERADOR\1-13 OP. CÁMARAS JUNIO (CULMINADO)TOTAL.csv"
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


# 4. ARQUITECTURA DE INTERACTIVIDAD CRUZADA POR CLICS (CALLBACKS DE SELECCIÓN)
zona_clic = None
modalidad_clic = None
operador_clic = None

# Fila superior de gráficos (Zonas y Modalidades)
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("📍 Filtro 1: Selecciona un Sector")
    conteo_zonas = df_filtros['ZONA'].value_counts().reset_index()
    conteo_zonas.columns = ['ZONA', 'CANTIDAD']
    
    fig_zonas = px.bar(conteo_zonas, x='CANTIDAD', y='ZONA', orientation='h',
                       text_auto=True, color='ZONA', title="Clic para aislar un Sector Municipal")
    fig_zonas.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
    
    clic_z = st.plotly_chart(fig_zonas, use_container_width=True, on_select="rerun")
    if clic_z and "selection" in clic_z and "points" in clic_z["selection"] and len(clic_z["selection"]["points"]) > 0:
        zona_clic = clic_z["selection"]["points"][0]["y"]

with col_g2:
    st.subheader("🛠️ Filtro 2: Selecciona una Modalidad")
    df_previo_mod = df_filtros.copy()
    if zona_clic:
        df_previo_mod = df_previo_mod[df_previo_mod['ZONA'] == zona_clic]
        
    conteo_mod = df_previo_mod['MODALIDAD'].value_counts().head(10).reset_index()
    conteo_mod.columns = ['MODALIDAD', 'CANTIDAD']
    conteo_mod['MODALIDAD_CORTA'] = conteo_mod['MODALIDAD'].apply(lambda x: x if len(str(x)) <= 25 else str(x)[:22] + "...")
    
    fig_mod = px.bar(conteo_mod, x='CANTIDAD', y='MODALIDAD_CORTA', orientation='h',
                     text_auto=True, color='MODALIDAD_CORTA', hover_name='MODALIDAD',
                     title="Clic para aislar una Modalidad de Incidente")
    fig_mod.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending', 'title': 'Modalidad'})
    
    clic_m = st.plotly_chart(fig_mod, use_container_width=True, on_select="rerun")
    if clic_m and "selection" in clic_m and "points" in clic_m["selection"] and len(clic_m["selection"]["points"]) > 0:
        idx_seleccionado = clic_m["selection"]["points"][0]["point_index"]
        modalidad_clic = conteo_mod.loc[idx_seleccionado, 'MODALIDAD']

st.divider()

# Fila intermedia para el gráfico de Operadores (Apellidos y Top 10)
col_g3, col_kpis = st.columns([2, 1])

with col_g3:
    st.subheader("👤 Filtro 3: Rendimiento y Carga del Personal")
    df_previo_op = df_filtros.copy()
    if zona_clic:
        df_previo_op = df_previo_op[df_previo_op['ZONA'] == zona_clic]
    if modalidad_clic:
        df_previo_op = df_previo_op[df_previo_op['MODALIDAD'] == modalidad_clic]
        
    conteo_op = df_previo_op['OPERADOR'].value_counts().reset_index()
    conteo_op.columns = ['OPERADOR', 'CANTIDAD']

    conteo_op['SOLO_APELLIDO'] = conteo_op['OPERADOR'].apply(lambda x: str(x).split()[0] if pd.notna(x) and str(x).strip() != '' else 'S/N')
    conteo_op_top = conteo_op.head(10)
    
    fig_op = px.bar(
        conteo_op_top, x='CANTIDAD', y='SOLO_APELLIDO', orientation='h',
        text_auto=True, color='SOLO_APELLIDO', hover_name='OPERADOR',
        title="Clic para auditar las bitácoras de un Operador específico (Top 10)"
    )
    fig_op.update_layout(
        showlegend=False, 
        yaxis={'categoryorder': 'total ascending', 'title': 'Personal (Apellido)'},
        xaxis={'title': 'Cantidad de Incidentes'}
    )
    
    clic_o = st.plotly_chart(fig_op, use_container_width=True, on_select="rerun")
    if clic_o and "selection" in clic_o and "points" in clic_o["selection"] and len(clic_o["selection"]["points"]) > 0:
        idx_op = clic_o["selection"]["points"][0]["point_index"]
        operador_clic = conteo_op_top.loc[idx_op, 'OPERADOR']

# 5. CONSOLIDACIÓN DE LA DATA FINAL FILTRADA POR CLICS MÚLTIPLES
df_final = df_filtros.copy()
filtros_activos_mensajes = []

if zona_clic:
    df_final = df_final[df_final['ZONA'] == zona_clic]
    filtros_activos_mensajes.append(f"📍 Sector: **{zona_clic}**")
if modalidad_clic:
    df_final = df_final[df_final['MODALIDAD'] == modalidad_clic]
    filtros_activos_mensajes.append(f"🛠️ Modalidad: **{modalidad_clic}**")
if operador_clic:
    df_final = df_final[df_final['OPERADOR'] == operador_clic]
    filtros_activos_mensajes.append(f"👤 Operador: **{operador_clic}**")

if filtros_activos_mensajes:
    st.info("🎯 **Filtros por Clic Activos:** " + " | ".join(filtros_activos_mensajes) + " *(Vuelve a hacer clic en la barra activa para liberar el filtro)*")

with col_kpis:
    st.markdown("#### 📊 Métricas del Grupo Filtrado")
    st.metric(label="Incidentes en Pantalla", value=len(df_final))
    
    camara_top = df_final['CAMARA'].mode()[0] if not df_final.empty else "N/A"
    st.metric(label="Cámara más Reportada", value=f"N° {camara_top}" if camara_top != "N/A" else "N/A")
    
    turno_top = df_final['TURNO'].mode()[0] if not df_final.empty else "N/A"
    st.metric(label="Turno con Mayor Alerta", value=turno_top)

st.divider()

# 6. MÓDULO DE PRECISIÓN: Cálculo dinámico de incidentes por número de cámara
if not df_final.empty:
    df_final['INCIDENTES_DE_ESTA_CAMARA'] = df_final.groupby('CAMARA')['CAMARA'].transform('count')
else:
    df_final['INCIDENTES_DE_ESTA_CAMARA'] = 0

# 7. REGISTRO DETALLADO CON LAS NUEVAS COLUMNAS REQUERIDAS
st.subheader("📋 Registro Detallado y Bitácora de Eventos")

columnas_vista = [
    'FECHA', 'OPERADOR', 'TURNO', 'CAMARA', 'INCIDENTES_DE_ESTA_CAMARA', 
    'TITULO', 'DESCRIPCIÓN'
]

st.dataframe(df_final[columnas_vista], use_container_width=True)