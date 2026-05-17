import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página para celulares
st.set_page_config(page_title="Gym Tracker Cloud", page_icon="💪", layout="centered")

st.title("💪 Mi Monitor de Entrenamiento (Cloud)")
st.write("Conectado en tiempo real con Google Sheets.")

# 1. Establecer la conexión con Google Sheets
# Nota: Streamlit busca automáticamente las credenciales en st.secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Leemos la hoja principal (por defecto la primera pestaña)
    df = conn.read(ttl="0d") # ttl="0d" para que no use caché y lea datos frescos del gimnasio
except Exception as e:
    st.error("Error al conectar con Google Sheets. Verificá tus credenciales en secrets.")
    st.stop()

# Asegurar tipos de datos correctos
if not df.empty:
    df["Fecha"] = df["Fecha"].astype(str)
    df["Serie"] = df["Serie"].astype(int)
    df["Peso"] = df["Peso"].astype(float)
    df["Reps"] = df["Reps"].astype(int)
else:
    # Si la planilla está completamente vacía, creamos la estructura base
    df = pd.DataFrame(columns=["Fecha", "Ejercicio", "Serie", "Peso", "Reps"])

# 2. Selector de Ejercicios
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

# 3. LÓGICA: Recuperar el historial de la última vez desde el Sheet
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
    st.info("💡 No hay registros previos de este ejercicio en tu Google Sheet. ¡Hoy se empieza!")

st.markdown("---")

# 4. INTERFAZ DE CARGA: Registro dinámico
st.subheader("📥 Cargar entrenamiento de hoy")
num_series_hoy = st.number_input("¿Cuántas series vas a hacer hoy?", min_value=1, max_value=6, value=3, step=1)

with st.form("formulario_entrenamiento"):
    nuevos_datos = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(1, int(num_series_hoy) + 1):
        st.markdown(f"**Serie {i}**")
        c1, c2 = st.columns(2)
        
        # Pre-cargar datos anteriores si existen para agilizar el proceso
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
        
    enviar = st.form_submit_button("💾 Guardar en Google Sheets")
    
    if enviar:
        df_nuevos = pd.DataFrame(nuevos_datos)
        # Combinamos los datos históricos con los nuevos
        df_total = pd.concat([df, df_nuevos], ignore_index=True)
        
        # Actualizamos la hoja de cálculo de Google
        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_total)
        st.success(f"¡Entrenamiento de {ejercicio_sel} subido a Google Drive!")
        st.rerun()
