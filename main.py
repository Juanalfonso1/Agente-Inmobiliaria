from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from contextlib import asynccontextmanager

# Importamos las funciones clave de nuestro agente
from agente.cerebro import inicializar_agente, ejecutar_agente, app_state

# --- Modelo de Datos para las Peticiones ---
# Define qué datos esperamos recibir en cada petición
class PreguntaUsuario(BaseModel):
    pregunta: str
    session_id: str | None = None # El session_id es opcional

# --- Función de Arranque y Apagado (Lifespan) ---
# Esto asegura que el agente se inicialice una sola vez cuando Render arranca el servidor.
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando servidor...")
    inicializar_agente()
    yield
    print("Servidor apagado.")
    # Limpiamos el estado al apagar (buena práctica)
    app_state.clear()

# --- Creación de la Aplicación FastAPI ---
app = FastAPI(lifespan=lifespan)

# --- Endpoints de la API ---

@app.get("/", summary="Endpoint de Bienvenida", description="Verifica que el servidor del agente está funcionando.")
def leer_raiz():
    """Endpoint principal para verificar el estado del servidor."""
    return {"mensaje": "¡Bienvenido al Agente de IA Inmobiliario! El servidor está funcionando."}

@app.post("/conversar/", summary="Mantener una conversación con el agente", description="Envía una pregunta y un session_id para interactuar con el agente.")
async def conversar_con_agente(datos_usuario: PreguntaUsuario):
    """
    Gestiona una conversación con el agente, usando un session_id
    para mantener la memoria.
    """
    try:
        # Si no se proporciona un session_id, creamos uno nuevo.
        session_id = datos_usuario.session_id or str(uuid.uuid4())
        
        # Ejecutamos el agente con la pregunta y el ID de sesión.
        respuesta_agente = ejecutar_agente(datos_usuario.pregunta, session_id)
        
        return {"respuesta": respuesta_agente, "session_id": session_id}

    except Exception as e:
        # Capturamos cualquier error inesperado y devolvemos una respuesta clara.
        print(f"Ha ocurrido un error en el endpoint /conversar/: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")