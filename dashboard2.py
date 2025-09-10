import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Dashboard Clínico Multietiqueta", layout="wide")

css = """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #2f3437;
    color: white;
}
[data-testid="stSidebar"] {
    background-color: #3f464a;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 2px 2px 8px #00000088;
    color: white;
}
h1, h2, h3 {
    color: #d1d5db;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
h1 {
    font-size: 3rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
    text-align: center;
}
.stDataFrame div[data-testid="stVerticalBlock"] {
    border-radius: 8px;
    box-shadow: 0 0 8px #00000088;
    padding: 0.5rem;
    background-color: #4b5257;
    color: white;
}
table {
    border-collapse: collapse;
    width: 100%;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #4b5257;
    color: white;
}
th, td {
    border: 1px solid #6b7280;
    padding: 8px;
}
th {
    background-color: #3f464a;
    color: #d1d5db;
    text-align: center;
}
td {
    text-align: center;
    color: #e5e7eb;
}
[data-testid="stPlotlyChart"] > div {
    border-radius: 10px;
    box-shadow: 0 0 10px #000000aa;
    background: #4b5257;
    padding: 0.5rem;
    color: white;
}
.stButton>button {
    background-color: #9ca3af;
    color: #2f3437;
    font-weight: bold;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    border: none;
}
.stButton>button:hover {
    background-color: #6b7280;
    color: white;
    cursor: pointer;
}
.css-1k8u8y0 {
    border-radius: 6px !important;
    border: 1px solid #6b7280 !important;
    padding: 0.3rem 0.5rem !important;
    background-color: #6b7280 !important;
    color: white !important;
}
.css-1d391kg input::placeholder {
    color: #d1d5db !important;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- RUTAS FIJAS (ajusta a tu entorno) ---
RUTA_RESULTADOS = r"C:\Users\yyang\Pacientes_por_enfermedad.xlsx"
RUTA_BASE = r"C:\Users\yyang\Downloads\BA.xlsx"
RUTA_RECOMENDACIONES = r"C:\Users\yyang\resultados_BA.xlsx"

@st.cache_data(show_spinner=True)
def cargar_datos(ruta):
    try:
        df = pd.read_excel(ruta)
        return df
    except Exception as e:
        st.error(f"No se pudo cargar el archivo {ruta}: {e}")
        return None

@st.cache_data(show_spinner=True)
def cargar_hojas_resultados(ruta):
    try:
        hojas = pd.read_excel(ruta, sheet_name=None)
        hoja_pacientes = hojas.get("Pacientes")
        recomendaciones = {
            hoja: df[['CÓDIGO', 'COLABORADOR', 'Recomendaciones']]
            for hoja, df in hojas.items()
            if 'Recomendaciones' in df.columns
        }
        return hoja_pacientes, recomendaciones
    except Exception as e:
        st.error(f"No se pudo leer el archivo {ruta}: {e}")
        return None, {}

df_base = cargar_datos(RUTA_BASE)
df_enfermedades = cargar_datos(RUTA_RESULTADOS)
df_pacientes_reco, dict_recomendaciones = cargar_hojas_resultados(RUTA_RECOMENDACIONES)

if df_base is None or df_enfermedades is None:
    st.stop()

# --- Sidebar: filtros ---
with st.sidebar:
    st.header("🔍 Filtros de búsqueda")

    # Autocompletado colaborador
    colaboradores = df_base['COLABORADOR'].dropna().unique()
    colaborador = st.selectbox("Buscar por nombre COLABORADOR", options=[""] + sorted(colaboradores.tolist()))

    codigo = st.text_input("Buscar por CÓDIGO").strip()

    clasificaciones = df_base['CLASIFICACIÓN'].dropna().unique().tolist()
    filtro_clasificacion = st.multiselect("Filtrar por CLASIFICACIÓN", clasificaciones)

    # Filtro por género
    generos = df_base['GENERO'].dropna().unique().tolist()
    filtro_genero = st.multiselect("Filtrar por GÉNERO", generos)

    # Filtro de peso por categorías binarias
    peso_opciones = ['Bajo Peso', 'Normal Peso', 'Sobrepeso', 'Obesidad I', 'Obesidad II', 'Obesidad III']
    filtro_peso = st.multiselect("Filtrar por peso", peso_opciones)

    # Filtro por enfermedades (columnas binarias 1/0)
    columnas_enf = [col for col in df_base.columns if col not in [
        'No.', 'CÓDIGO', 'FECHA INGRESO', 'CLASIFICACIÓN', 'GENERO', 'COLABORADOR', 'PUESTO',
        'Años', 'F.de Nac.', 'Libras', 'cm', 'IMC', 'Frecuencia cardíaca', 'Saturación de Oxígeno',
        'Creatinina', 'TFG', 'Glucosa en ayunas', 'Normal Presión'
    ] + peso_opciones]

    filtro_enfermedad = st.multiselect("Filtrar por enfermedades", columnas_enf)

    if 'FECHA INGRESO' in df_base.columns:
        df_base['AÑO'] = pd.to_datetime(df_base['FECHA INGRESO'], errors='coerce').dt.year
        años = df_base['AÑO'].dropna().unique()
        filtro_anio = st.multiselect("Filtrar por año de ingreso", sorted(años))
    else:
        filtro_anio = []

    ordenar_opciones = st.selectbox(
        "Ordenar pacientes por:",
        options=[
            "Ninguno",
            "Cantidad de enfermedades detectadas (mayor a menor)",
            "Código ascendente",
            "Código descendente",
            "Edad ascendente",
            "Edad descendente"
        ]
    )

# --- Aplicar filtros ---
filtro_base = df_base.copy()

cols_a_eliminar = [col for col in filtro_base.columns if col.endswith("No.")]
filtro_base = filtro_base.drop(columns=cols_a_eliminar)

if colaborador:
    filtro_base = filtro_base[filtro_base['COLABORADOR'].str.contains(colaborador, case=False, na=False)]

if codigo:
    filtro_base = filtro_base[filtro_base['CÓDIGO'].astype(str).str.contains(codigo, case=False, na=False)]

if filtro_clasificacion:
    filtro_base = filtro_base[filtro_base['CLASIFICACIÓN'].isin(filtro_clasificacion)]

if filtro_genero:
    filtro_base = filtro_base[filtro_base['GENERO'].isin(filtro_genero)]

if filtro_peso:
    filtro_peso_mask = filtro_base[filtro_peso].sum(axis=1) > 0
    filtro_base = filtro_base[filtro_peso_mask]

if filtro_enfermedad:
    filtro_enf_mask = filtro_base[filtro_enfermedad].sum(axis=1) > 0
    filtro_base = filtro_base[filtro_enf_mask]

if filtro_anio:
    filtro_base = filtro_base[filtro_base['AÑO'].isin(filtro_anio)]

# Eliminar fila índice 0 si está presente
if 0 in filtro_base.index:
    filtro_base = filtro_base.drop(0)

# Contar enfermedades detectadas (no se usa para KPI real, pero puede quedar)
def contar_enfermedades_paciente(row):
    return row[columnas_enf].sum()

filtro_base['Enfermedades Detectadas'] = filtro_base.apply(contar_enfermedades_paciente, axis=1)

# Función para contar enfermedades reales detectadas según recomendaciones
hojas_no_enfermedad = ['Pacientes', 'Predicciones', 'Resumen', 'Info']

def contar_enfermedades_por_paciente_real(codigo_pac, colaborador_pac):
    if pd.isna(codigo_pac) and pd.isna(colaborador_pac):
        return 0
    count = 0
    hojas_enfermedades = [hoja for hoja in dict_recomendaciones.keys() if hoja not in hojas_no_enfermedad]
    for hoja in hojas_enfermedades:
        df_reco = dict_recomendaciones[hoja]
        filtro = pd.Series([True] * len(df_reco))
        if colaborador_pac:
            filtro = filtro & df_reco['COLABORADOR'].astype(str).str.contains(str(colaborador_pac), case=False, na=False)
        if codigo_pac:
            filtro = filtro & df_reco['CÓDIGO'].astype(str).str.contains(str(codigo_pac), case=False, na=False)
        if not df_reco[filtro].empty:
            count += 1
    return count

# Agregar columna con enfermedades reales detectadas
filtro_base['Posibles Enfermedades Detectadas'] = filtro_base.apply(
    lambda row: contar_enfermedades_por_paciente_real(row['CÓDIGO'], row['COLABORADOR']),
    axis=1
)

# Aplicar ordenamiento según la opción seleccionada
if ordenar_opciones == "Cantidad de enfermedades detectadas (mayor a menor)":
    filtro_base = filtro_base.sort_values(by='Enfermedades Detectadas', ascending=False)
elif ordenar_opciones == "Código ascendente":
    filtro_base = filtro_base.sort_values(by='CÓDIGO', ascending=True)
elif ordenar_opciones == "Código descendente":
    filtro_base = filtro_base.sort_values(by='CÓDIGO', ascending=False)
elif ordenar_opciones == "Edad ascendente":
    if 'Años' in filtro_base.columns:
        filtro_base = filtro_base.sort_values(by='Años', ascending=True)
elif ordenar_opciones == "Edad descendente":
    if 'Años' in filtro_base.columns:
        filtro_base = filtro_base.sort_values(by='Años', ascending=False)

col1, col2, col3 = st.columns([1,4,2])

with col1:
    import requests
    from io import BytesIO
    from PIL import Image

    raw_url = "https://raw.githubusercontent.com/yyangs21/A3eC0Mc0mB3x_Yy/master/Asecom.png"
    try:
        resp = requests.get(raw_url, timeout=10)
        resp.raise_for_status()
        logo_img = Image.open(BytesIO(resp.content))
        st.image(logo_img, width=360)
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar el logo desde GitHub: {e}")


with col2:
    st.title("🩺 Dashboard Clínico Multietiqueta")

with col3:
    total_colaboradores = filtro_base['COLABORADOR'].nunique()
    suma_enfermedades = filtro_base['Posibles Enfermedades Detectadas'].sum()
    total_pacientes = len(filtro_base)
    promedio_enfermedades = suma_enfermedades / total_pacientes if total_pacientes > 0 else 0
    
    st.markdown(f"""
    <div style="display: flex; gap: 1rem; justify-content: flex-end;">
        <div style="background:#1f2937; padding: 1rem 1.5rem; border-radius: 10px; box-shadow: 0 0 10px #000000aa; min-width:150px; color:#60a5fa; font-weight: 700; text-align:center;">
            <div style="font-size: 0.9rem;">Colaboradores filtrados</div>
            <div style="font-size: 2rem;">{total_colaboradores:,}</div>
        </div>
        <div style="background:#1f2937; padding: 1rem 1.5rem; border-radius: 10px; box-shadow: 0 0 10px #000000aa; min-width:220px; color:#f87171; font-weight: 700; text-align:center;">
            <div style="font-size: 0.9rem;">Promedio enfermedades por paciente</div>
            <div style="font-size: 2rem;">{promedio_enfermedades:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Botón para descargar Excel con datos filtrados
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Eliminamos la columna que no quieres exportar
    df_export = df.drop(columns=['Enfermedades Detectadas', 'Posibles Enfermedades Detectadas'], errors='ignore')
    
    df_export.to_excel(writer, index=False, sheet_name='Pacientes')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

if not filtro_base.empty:
    excel_data = to_excel(filtro_base)
    st.download_button(
        label="📥 Descargar datos filtrados en Excel",
        data=excel_data,
        file_name="pacientes_filtrados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Tabs ---

hojas_no_enfermedad = ['Pacientes', 'Predicciones', 'Resumen', 'Info']

tab1, tab2, tab3, tab4 = st.tabs([
    "Datos Paciente",
    "Gráfica Enfermedades",
    "Recomendaciones",
    "Tablas completas"
])

with tab1:
    st.header("Datos generales del paciente")
    if not filtro_base.empty:
        df_a_mostrar = filtro_base.drop(columns=['Enfermedades Detectadas'], errors='ignore')
        st.dataframe(df_a_mostrar.style.set_properties(**{
            'background-color': '#4b5257',
            'color': 'white',
            'border-color': '#6b7280'
        }))
    else:
        st.info("No se encontraron datos con los filtros seleccionados.")

with tab2:
    st.header("Gráfica personalizada de posibles enfermedades")
    if colaborador or codigo or filtro_peso or filtro_enfermedad:
        enfermedades_detectadas = 0
        hojas_enfermedades = [hoja for hoja in dict_recomendaciones.keys() if hoja not in hojas_no_enfermedad]
        enfermedades_totales = len(hojas_enfermedades)

        for hoja in hojas_enfermedades:
            df_reco = dict_recomendaciones[hoja]
            filtro = pd.Series([True] * len(df_reco))
            if colaborador:
                filtro = filtro & df_reco['COLABORADOR'].astype(str).str.contains(colaborador, case=False, na=False)
            if codigo:
                filtro = filtro & df_reco['CÓDIGO'].astype(str).str.contains(codigo, case=False, na=False)
            if not df_reco[filtro].empty:
                enfermedades_detectadas += 1

        enfermedades_no_detectadas = enfermedades_totales - enfermedades_detectadas

        df_graf = pd.DataFrame({
            'Estado': ['Tiene enfermedades', 'No tiene enfermedades'],
            'Cantidad': [enfermedades_detectadas, enfermedades_no_detectadas]
        })

        fig = px.pie(df_graf, values='Cantidad', names='Estado',
                     color='Estado',
                     color_discrete_map={'Tiene enfermedades': '#ef4444', 'No tiene enfermedades': '#22c55e'},
                     title='Enfermedades detectadas vs no detectadas',
                     template='plotly_dark')
        fig.update_traces(textinfo='percent+label', textfont_size=16, marker=dict(line=dict(color='#000000', width=2)))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**Total de enfermedades evaluadas:** {enfermedades_totales}")

    else:
        st.info("Usa algún filtro para ver la gráfica personalizada de enfermedades.")

with tab3:
    st.header("Recomendaciones nutricionales por enfermedad")
    if colaborador or codigo or filtro_peso or filtro_enfermedad:
        encontrados = False
        for hoja, df_reco in dict_recomendaciones.items():
            if 'COLABORADOR' in df_reco.columns and 'CÓDIGO' in df_reco.columns:
                filtro_reco = pd.Series([True]*len(df_reco))
                if colaborador:
                    filtro_reco = filtro_reco & df_reco['COLABORADOR'].astype(str).str.contains(colaborador, case=False, na=False)
                if codigo:
                    filtro_reco = filtro_reco & df_reco['CÓDIGO'].astype(str).str.contains(codigo, case=False, na=False)
                if not df_reco[filtro_reco].empty:
                    encontrados = True
                    st.subheader(f"📝 {hoja}")
                    st.dataframe(df_reco[filtro_reco].style.set_properties(**{
                        'background-color': '#6b7280',
                        'color': 'white',
                        'border-color': '#9ca3af'
                    }))
        if not encontrados:
            st.info("No se encontraron recomendaciones para los filtros aplicados.")
    else:
        st.info("Usa algún filtro para ver recomendaciones.")

with tab4:
    if st.checkbox("Mostrar tabla completa: Pacientes base"):
        st.subheader("Tabla completa: Pacientes base")
        df_base_filtrado = df_base.drop(columns=[col for col in df_base.columns if col.endswith("No.")])
        st.dataframe(df_base_filtrado.style.set_properties(**{
            'background-color': '#4b5257',
            'color': 'white',
            'border-color': '#6b7280'
        }
        ))

    if st.checkbox("Mostrar tabla completa: Pacientes por enfermedad"):
        st.subheader("Tabla completa: Pacientes por enfermedad")
        df_enf_filtrado = df_enfermedades.drop(columns=[col for col in df_enfermedades.columns if col.endswith("No.")], errors='ignore')
        st.dataframe(df_enf_filtrado.style.set_properties(**{
            'background-color': '#3f464a',
            'color': 'white',
            'border-color': '#6b7280'
        }))

    # Gráfica general conteo pacientes por enfermedad
    st.subheader("Distribución general de pacientes por enfermedad")
    cols_no = [col for col in df_enfermedades.columns if col.endswith("No.")]

    conteo_enfermedades = {}
    for col in cols_no:
        conteo = df_enfermedades[col].notna().sum()
        nombre_enfermedad = col.replace(" - No.", "").strip()
        conteo_enfermedades[nombre_enfermedad] = conteo

    df_conteo = pd.DataFrame.from_dict(conteo_enfermedades, orient='index', columns=['Pacientes'])
    df_conteo = df_conteo.sort_values(by='Pacientes', ascending=False)

    if not df_conteo.empty:
        fig_bar = px.bar(
            df_conteo,
            x=df_conteo.index,
            y='Pacientes',
            labels={'x': 'Enfermedad', 'Pacientes': 'Número de pacientes'},
            title="Conteo general de pacientes por enfermedad",
            color='Pacientes',
            color_continuous_scale='gray',
            template='plotly_dark'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No hay datos disponibles para mostrar la distribución de enfermedades.")
