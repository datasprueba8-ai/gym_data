import streamlit as st
import pandas as pd
from datetime import datetime
from github import Github
import io

# Configuración de la página
st.set_page_config(page_title="Gym Tracker GitHub", page_icon="💪", layout="centered")

st.title("💪 Mi Monitor de Entrenamiento (GitHub Cloud)")
st.write("Datos guardados de forma segura y gratuita en tu repositorio.")

# 1. AUTENTICACIÓN CON GITHUB (Usa st.secrets para producción o variables locales)
try:
    # En tu compu lee de .streamlit/secrets.toml, en la nube de los Advanced Settings
    GITHUB_TOKEN = st.secrets["github"]["token"]
    REPO_NAME = st.secrets["github"]["repo"]  # Ej: "tu-usuario/tu-repositorio"
    FILE_PATH = "historial_gym.csv"           # Nombre del archivo en el repo
    
    # Inicializamos el cliente de GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
except Exception as e:
    st.error("Error de configuración de secretos de GitHub. Verificá tu secrets.toml.")
    st.stop()

# 2. FUNCIÓN PARA LEER EL CSV DESDE GITHUB
@st.cache_data(ttl="0d") # Evitamos caché para tener datos frescos en cada serie
def cargar_datos_github():
    try:
        file_content = repo.get_contents(FILE_PATH)
        data = file_content.decoded_content.decode("utf-8")
        df = pd.read_csv(io.StringIO(data))
        return df, file_content.sha
    except Exception:
        # Si el archivo no existe o está vacío, devolvemos un DF base
        return pd.DataFrame(columns=["Fecha", "Ejercicio", "Serie", "Peso", "Reps"]), None

df, file_sha = cargar_datos_github()

# Asegurar tipos de datos correctos
if not df.empty:
    df["Fecha"] = df["Fecha"].astype(str)
    df["Serie"] = df["Serie"].astype(int)
    df["Peso"] = df["Peso"].astype(float)
    df["Reps"] = df["Reps"].astype(int)

# 3. SELECTOR DE EJERCICIOS
lista_ejercicios = [
    "Press de Banca", 
    "Sentadillas Barra Alta", 
    "Peso Muerto Rumano", 
    "Dominadas Lastradas",
    "Press Militar con Mancuernas",
    "Vuelos Laterales"
]
ejercicio_sel = st.selectbox("🏋️‍♂️ Seleccioná el ejercicio:", lista_ejercicios)

st.markdown("---")

# 4. LÓGICA: Recuperar el historial de la última vez
df_ejercicio = df[df["Ejercicio"] == ejercicio_sel]

if not df_ejercicio.empty:
    ultima_fecha = df_ejercicio["Fecha"].max()
    ultimo_entreno = df_ejercicio[df_ejercicio["Fecha"] == ultima_fecha].sort_values(by="Serie")
    
    st.subheader(f"📋 Última vez: {ultima_fecha}")
    
    for _, row in ultimo_entreno.iterrows():
        col_s, col_p, col_r = st.columns([1, 2, 2])
        col_s.markdown(f"**Serie {int(row['Serie'])}**")
        col_p.metric(label="Peso", value=f"{row['Peso']} kg")
        col_r.metric(label="Reps", value=f"{int(row['Reps'])}")
else:
    st.info("💡 No hay registros previos de este ejercicio. ¡Hoy arranca el historial!")

st.markdown("---")

# 5. INTERFAZ DE CARGA
st.subheader("📥 Cargar entrenamiento de hoy")
num_series_hoy = st.number_input("¿Cuántas series vas a hacer hoy?", min_value=1, max_value=6, value=3, step=1)

with st.form("formulario_entrenamiento"):
    nuevos_datos = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(1, int(num_series_hoy) + 1):
        st.markdown(f"**Serie {i}**")
        c1, c2 = st.columns(2)
        
        peso_previo = 0.0
        reps_previas = 0
        if not df_ejercicio.empty and i <= len(ultimo_entreno):
            peso_previo = float(ultimo_entreno.iloc[i-1]["Peso"])
            reps_previas = int(ultimo_entreno.iloc[i-1]["Reps"])
            
        peso = c1.number_input(f"Peso (kg) - S{i}", min_value=0.0, step=0.5, value=peso_previo, key=f"peso_{i}")
        reps = c2.number_input(f"Reps - S{i}", min_value=0, step=1, value=reps_previas, key=f"reps_{i}")
        
        nuevos_datos.append({
            "Fecha": fecha_hoy,
            "Ejercicio": ejercicio_sel,
            "Serie": i,
            "Peso": peso,
            "Reps": reps
        })
        
    enviar = st.form_submit_button("💾 Guardar en GitHub")
    
    if enviar:
        with st.spinner("Subiendo datos a tu repositorio de GitHub..."):
            df_nuevos = pd.DataFrame(nuevos_datos)
            df_total = pd.concat([df, df_nuevos], ignore_index=True)
            
            # Convertimos el DataFrame final a string CSV
            csv_buffer = io.StringIO()
            df_total.to_csv(csv_buffer, index=False)
            csv_string = csv_buffer.getvalue()
            
            # Subimos el cambio haciendo un commit a la API de GitHub
            mensaje_commit = f"Gym Update - {ejercicio_sel} ({fecha_hoy})"
            
            if file_sha:
                repo.update_file(FILE_PATH, mensaje_commit, csv_string, file_sha)
            else:
                repo.create_file(FILE_PATH, mensaje_commit, csv_string)
                
            st.success("¡Entrenamiento sincronizado en GitHub con éxito!")
            st.rerun()
