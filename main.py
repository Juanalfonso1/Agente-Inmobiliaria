# main.py - El servidor que expone nuestro agente al mundo

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uuid

# Importamos las funciones clave de nuestro cerebro
from agente.cerebro import inicializar_agente, ejecutar_agente

# --- Contexto de Vida de la Aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Esta función se ejecuta cuando el servidor arranca.
    Es el lugar perfecto para inicializar nuestro agente.
    """
    print("Iniciando el Agente de IA...")
    try:
        inicializar_agente()
        print("✅ Arranque completado. El agente está listo.")
    except Exception as e:
        print(f"❌ Error fatal durante la inicialización: {e}")
    yield
    # Código de limpieza (si fuera necesario al apagar)
    print("Servidor apagado.")

# --- Inicialización de la App ---
app = FastAPI(
    title="Asistente Inmobiliario IA",
    description="Un agente de IA para interactuar con clientes de una inmobiliaria.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Modelos de Datos (para las peticiones) ---
class PeticionConversacion(BaseModel):
    pregunta: str
    session_id: str | None = None

class RespuestaConversacion(BaseModel):
    respuesta: str
    session_id: str

# --- Endpoints (las "puertas" de nuestra API) ---
@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Bienvenido al Asistente Inmobiliario IA de Gestiones Ficus!"}

@app.post("/conversar", response_model=RespuestaConversacion)
def conversar_con_agente(peticion: PeticionConversacion):
    """
    Endpoint principal para hablar con el agente.
    """
    session_id = peticion.session_id or str(uuid.uuid4())
    
    if not peticion.pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        # Llamamos a la nueva función del cerebro
        respuesta_agente = ejecutar_agente(peticion.pregunta, session_id)
        return RespuestaConversacion(respuesta=respuesta_agente, session_id=session_id)
    except Exception as e:
        print(f"Error en el endpoint /conversar: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

