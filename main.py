
# main.py - Con puerto alternativo

import os
import sys
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# 🔑 Cargar variables de entorno
load_dotenv()

# 🌐 Configurar CORS
ALLOWED_ORIGINS = [
    "https://tenerifemy.com",
    "https://www.tenerifemy.com",
    "https://www.terramagna.net/inmuebles"
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:8080",  # Puerto alternativo agregado
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080"   # Puerto alternativo agregado
]

# ⚠️ Variables globales para el agente
cerebro_mod = None
agente_inicializado = False
error_inicializacion = None

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro con imports seguros."""
    global cerebro_mod, agente_inicializado, error_inicializacion
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        # Verificar si cerebro.py existe
        if not os.path.exists('cerebro.py'):
            error_inicializacion = "No se encuentra el archivo cerebro.py"
            print(f"[ERROR] {error_inicializacion}")
            return None
        
        # Importar cerebro
        import cerebro as cerebro_mod
        print("✅ Módulo cerebro importado correctamente.")
        
        # Inicializar el agente
        resultado = cerebro_mod.inicializar_agente()
        
        if resultado is not None:
            agente_inicializado = True
            error_inicializacion = None
            print("✅ Agente cargado e inicializado correctamente.")
            return cerebro_mod
        else:
            error_inicializacion = "El agente no se inicializó correctamente"
            print(f"[ERROR] {error_inicializacion}")
            return None
            
    except ImportError as e:
        error_inicializacion = f"Error de importación: {str(e)}"
        print(f"[ERROR] {error_inicializacion}")
        return None
        
    except Exception as error:
        error_inicializacion = f"Error inesperado: {str(error)}"
        print(f"[ERROR] {error_inicializacion}")
        return None

# 🔄 Ciclo de vida de la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicación...")
    agente = cargar_agente_si_es_posible()
    
    if agente and agente_inicializado:
        print("✅ Aplicación iniciada correctamente con agente.")
    else:
        print(f"⚠️ Aplicación iniciada sin agente. Error: {error_inicializacion}")
    
    yield
    
    # Shutdown
    print("🔄 Cerrando aplicación...")

# 🚀 Inicializar FastAPI con ciclo de vida
app = FastAPI(
    title="API Inmobiliaria IA",
    description="API para asistente virtual inmobiliario",
    version="1.0.0",
    lifespan=lifespan
)

# 🛡️ Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🏠 Endpoint raíz
@app.get("/")
async def root():
    status = "funcionando" if (cerebro_mod and agente_inicializado) else "sin agente"
    return {
        "mensaje": f"API Inmobiliaria IA {status}.",
        "agente_disponible": bool(cerebro_mod and agente_inicializado),
        "error_inicializacion": error_inicializacion
    }

from fastapi import FastAPI, Query, HTTPException
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = FastAPI()

# 🧠 Módulo de análisis emocional
def detectar_emocion(texto):
    analizador = SentimentIntensityAnalyzer()
    resultado = analizador.polarity_scores(texto)
    compound = resultado['compound']
    
    if compound <= -0.5:
        return "frustrado"
    elif compound >= 0.5:
        return "positivo"
    else:
        return "neutral"

# 🤖 Endpoint GET para preguntas
@app.get("/preguntar")
async def preguntar(pregunta: str = Query(..., description="Pregunta del usuario")):
    # Intentar cargar agente si no está disponible
    agente = cargar_agente_si_es_posible()
    
    if not agente or not agente_inicializado:
        raise HTTPException(
            status_code=503,
            detail=f"El agente no está disponible. Error: {error_inicializacion or 'Desconocido'}"
        )
    
    if not pregunta.strip():
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía."
        )

    # 🔍 Detectar emoción del usuario
    emocion = detectar_emocion(pregunta)

    # 🧠 Ajustar tono del prompt según emoción
    if emocion == "frustrado":
        prompt_extra = "Responde con empatía, el usuario parece frustrado."
    elif emocion == "positivo":
        prompt_extra = "Responde con entusiasmo, el usuario está positivo."
    else:
        prompt_extra = ""

    # 🧾 Construir prompt final
    prompt_final = f"{prompt_extra}\nPregunta del usuario: {pregunta}"

    try:
        # Usar directamente la función ejecutar_agente del módulo
        respuesta = agente.ejecutar_agente(prompt_final)
        return {"respuesta": respuesta}
        
    except Exception as error:
        print(f"[ERROR] Fallo al procesar pregunta: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando la solicitud: {str(error)}"
        )

# 💬 Endpoint POST para chatbot
class PreguntaModel(BaseModel):
    mensaje: str
    
    class Config:
        str_strip_whitespace = True

@app.post("/chat")
async def chat(pregunta: PreguntaModel):
    # Intentar cargar agente si no está disponible
    agente = cargar_agente_si_es_posible()
    
    if not agente or not agente_inicializado:
        raise HTTPException(
            status_code=503,
            detail=f"El agente no está disponible. Error: {error_inicializacion or 'Desconocido'}"
        )
    
    if not pregunta.mensaje.strip():
        raise HTTPException(
            status_code=400,
            detail="El mensaje no puede estar vacío."
        )
    
    try:
        # Usar directamente la función ejecutar_agente del módulo
        respuesta = agente.ejecutar_agente(pregunta.mensaje)
        return {"respuesta": respuesta}
        
    except Exception as error:
        print(f"[ERROR] Fallo en /chat: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el mensaje: {str(error)}"
        )

# 🔧 Endpoint de estado para debugging
@app.get("/status")
async def status():
    return {
        "agente_modulo_cargado": bool(cerebro_mod),
        "agente_inicializado": agente_inicializado,
        "error_inicializacion": error_inicializacion,
        "openai_key_configurada": bool(os.getenv("OPENAI_API_KEY")),
        "directorio_conocimiento_existe": os.path.exists("conocimiento")
    }

# 🧪 Para pruebas en desarrollo
if __name__ == "__main__":
    print("🧪 Modo de prueba...")
    
    # Verificar configuración básica
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY no está configurada")
    else:
        print("✅ OPENAI_API_KEY encontrada")
    
    # Probar agente
    agente = cargar_agente_si_es_posible()
    if agente and agente_inicializado:
        respuesta = agente.ejecutar_agente("Hola, ¿cómo estás?")
        print(f"✅ Respuesta de prueba: {respuesta}")
    else:
        print(f"❌ No se pudo cargar el agente: {error_inicializacion}")
    
    # Ejecutar servidor en puerto alternativo
    try:
        import uvicorn
        print("🚀 Iniciando servidor en http://0.0.0.0:8080")
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")