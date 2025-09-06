from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from contextlib import asynccontextmanager

# Importamos las funciones clave de nuestro agente
from agente.cerebro import inicializar_agente, ejecutar_agente

# --- Modelo de Datos para las Peticiones ---
class PreguntaUsuario(BaseModel):
    pregunta: str
    session_id: str | None = None

# --- Función de Arranque (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando servidor...")
    inicializar_agente()
    yield
    print("Servidor apagado.")

# --- Creación de la Aplicación FastAPI ---
app = FastAPI(lifespan=lifespan)

# --- Endpoints de la API ---
@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Bienvenido al Agente de IA Inmobiliario! El servidor está funcionando."}

@app.post("/conversar/")
async def conversar_con_agente(datos_usuario: PreguntaUsuario):
    try:
        session_id = datos_usuario.session_id or str(uuid.uuid4())
        respuesta_agente = ejecutar_agente(datos_usuario.pregunta, session_id)
        return {"respuesta": respuesta_agente, "session_id": session_id}
    except Exception as e:
        print(f"Ha ocurrido un error en el endpoint /conversar/: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")