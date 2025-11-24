import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import os

# --- 1. CONFIGURACIÓN DE PARÁMETROS Y SEGURIDAD ---

# FIX CRÍTICO PARA EL DESPLIEGUE: Cargar la clave de forma segura desde st.secrets
try:
    # La clave 'ibm_watsonx_api_key' debe coincidir con el nombre en secrets.toml o la interfaz web.
    API_KEY_PERSISTENTE = st.secrets["ibm_watsonx_api_key"]
except KeyError:
    st.error("Error de Configuración: La clave 'ibm_watsonx_api_key' no se encontró en Streamlit Secrets. Por favor, revisa la configuración del despliegue.")
    st.stop() 

# URLs de servicio
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
CHAT_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"

# Parámetros del Modelo
WATSONX_PROJECT_ID = "b63957ae-ed14-4732-badd-71bf233c9409"
MODEL_ID = "ibm/granite-3-3-8b-instruct"

# Contenido del Mensaje del Sistemaimport streamlit as st
import requests
import json
from datetime import datetime, timedelta
import os # Importamos os por si acaso

# --- 1. CONFIGURACIÓN DE PARÁMETROS Y SEGURIDAD ---

# FIX CRÍTICO PARA EL DESPLIEGUE: Cargar la clave de forma segura desde st.secrets
# Streamlit Cloud inyectará la clave que configuraste en su interfaz de Secrets.
try:
    # Asegúrate de que el nombre 'ibm_watsonx_api_key' coincida exactamente con el secret.
    API_KEY_PERSISTENTE = st.secrets["ibm_watsonx_api_key"]
except KeyError:
    st.error("Error de Configuración: La clave 'ibm_watsonx_api_key' no se encontró en Streamlit Secrets.")
    st.stop() # Detiene la ejecución si la clave no está disponible.

# URLs de servicio
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
CHAT_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"

# Parámetros del Modelo
WATSONX_PROJECT_ID = "b63957ae-ed14-4732-badd-71bf233c9409"
MODEL_ID = "ibm/granite-3-3-8b-instruct"

# Contenido del Mensaje del Sistema (COMPLETO)
SYSTEM_MESSAGE_CONTENT = (
    "Eres un Asistente Experto en Seguridad Pública y Análisis Delictivo integrado "
    "en un dashboard de inteligencia para la Ciudad de México (CDMX). Tu objetivo es asistir a "
    "ciudadanos, analistas y oficiales de policía interpretando datos delictivos y sugiriendo estrategias operativas.\n\n"
    "Tus responsabilidades son:\n\n"
    "1. ANÁLISIS DE DATOS: Responder preguntas sobre índices delictivos basándote ESTRICTAMENTE en la información "
    "o contexto proporcionado (fechas, alcaldías, colonias, tipos de delito, modus operandi).\n"
    "* Identificar patrones. Si no tienes datos suficientes para responder, indícalo claramente.\n\n"
    "2. SOPORTE OPERATIVO (Para perfiles de seguridad/policía):\n"
    "* Sugiere acciones concretas como: patrullaje preventivo, instalación de puntos de control, revisión de cámaras del C5, o acercamiento con líderes vecinales.\n"
    "* Usa terminología adecuada para la CDMX (Cuadrantes, Sectores, C5, Ministerio Público).\n\n"
    "DIRECTRICES DE TONO Y FORMATO:\n"
    "* Tono: Profesional, objetivo, autoritario pero servicial.\n"
    "* Estilo: **Conciso**. Usa listas (bullet points) para facilitar la lectura rápida en el dashboard.\n"
    "* Seguridad: Prioriza siempre la seguridad de los oficiales y ciudadanos.\n\n"
    "SI EL USUARIO PIDE UN PLAN DE ACCIÓN: Estructura la respuesta en: 'Diagnóstico Situacional', "
    "'Acciones Inmediatas' y 'Recomendaciones de Prevención'."
)

# --- 2. GESTIÓN DE AUTENTICACIÓN Y CHAT (API REST) ---

@st.cache_data(ttl=3540)
def get_iam_token(api_key):
    """Obtiene un Bearer Token de IAM usando la Clave de API persistente."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = (
        f"grant_type=urn:ibm:params:oauth:grant-type:apikey&"
        f"apikey={api_key}"
    )

    try:
        response = requests.post(IAM_URL, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        token_info = response.json()
        return token_info["access_token"]
    
    except Exception as e:
        # En la nube, solo mostramos un error genérico por seguridad
        st.error("Error al obtener Token de IAM. Revise si la API Key es correcta.")
        return None

def get_watsonx_chat_response(chat_history):
    """Llama al endpoint de chat de watsonx.ai con la historia completa."""
    bearer_token = get_iam_token(API_KEY_PERSISTENTE)
    if not bearer_token:
        return "Error: No se pudo obtener el token de acceso IAM. Verifique Streamlit Secrets."
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    body = {
        "messages": chat_history, # Enviamos la historia completa
        "project_id": WATSONX_PROJECT_ID,
        "model_id": MODEL_ID,
        "frequency_penalty": 0,
        "max_tokens": 2000,
        "presence_penalty": 0,
        "temperature": 0,
        "top_p": 1
    }

    try:
        response = requests.post(CHAT_URL, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # FIX FINAL DE PARSEO: Accedemos directamente a la clave 'choices'
        return data["choices"][0]["message"]["content"]
            
    except requests.exceptions.HTTPError as e:
        return f"Error de API (Código {response.status_code}). El servidor rechazó la solicitud."
    except KeyError as e:
        return f"Error de parseo. El formato de respuesta de la API cambió."
    except Exception as e:
        return f"Error de conexión o procesamiento: {e}"

# --- 4. INTERFAZ DE STREAMLIT ---

st.set_page_config(
    page_title="Chatbot de Seguridad CDMX (Granite)",
    layout="wide"
)

col1, col2, col3 = st.columns([1, 4, 1])

with col2:
    st.markdown("<h1 style='text-align: center; color: #1E90FF;'>🤖 Asistente de Inteligencia CDMX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Pregunta sobre análisis delictivo o planes operativos.</p>", unsafe_allow_html=True)
    st.divider()

# 4.1 Inicialización de la Historia del Chat
if "messages" not in st.session_state:
    # El primer mensaje es el del sistema (rol)
    st.session_state.messages = [{"role": "system", "content": SYSTEM_MESSAGE_CONTENT}]
    # Agregamos un mensaje visible de bienvenida
    st.session_state.messages.append({"role": "assistant", "content": "Bienvenido. Soy tu Asistente de Inteligencia CDMX. ¿En qué te puedo ayudar?"})

# 4.2 Mostrar Mensajes Anteriores
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 4.3 Manejar la Entrada del Usuario y Generar Respuesta
prompt = st.chat_input("Escribe tu pregunta o plan de acción...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("El Asistente está analizando los datos..."):
        # Enviamos la historia completa, incluyendo el mensaje del sistema (índice 0)
        assistant_response = get_watsonx_chat_response(st.session_state.messages)

    with st.chat_message("assistant"):
        st.markdown(assistant_response)
        
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    
st.sidebar.info("Aplicación desplegada usando Streamlit Community Cloud y autenticación segura con **Streamlit Secrets**.")