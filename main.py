import os
from fastapi import FastAPI, Query
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
    "http://localhost:5500"
]

# ⚠️ Import perezoso del módulo cerebro
cerebro_mod = None
ejecutar_agente = None  # Aquí guardaremos la función que responde preguntas

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro con imports seguros."""
    global cerebro_mod, ejecutar_agente
    if cerebro_mod:
        return cerebro_mod
    try:
        from agente import cerebro as cerebro_mod  # Importa el módulo completo
        ejecutar_agente = cerebro_mod.inicializar_agente()  # Obtiene la función ejecutora
        return cerebro_mod
    except Exception as error:
        print(f"[WARN] No se pudo importar cerebro: {error}")
        return None

# 🔄 Ciclo de vida de la app
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    agente = cargar_agente_si_es_posible()
    if agente:
        print("✅ Agente inicializado correctamente.")
    else:
        print("⚠️ No se pudo inicializar el agente.")
    yield

# 🧪 Ejemplo de uso fuera del ciclo de vida (solo para pruebas locales)
if __name__ == "__main__":
    cargar_agente_si_es_posible()
    if ejecutar_agente:
        pregunta = "¿Cuál es el precio promedio de una casa en Madrid?"
        respuesta = ejecutar_agente(pregunta)
        print(respuesta)
    else:
        print("⚠️ El agente no está disponible.")


# 🚀 Inicializar FastAPI con ciclo de vida
app = FastAPI(lifespan=lifespan)

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
    return {"mensaje": "API Inmobiliaria IA funcionando correctamente."}

# 🤖 Endpoint GET para preguntas
@app.get("/preguntar")
async def preguntar(pregunta: str = Query(..., description="Pregunta del usuario")):
    agente = cargar_agente_si_es_posible()
    if not agente:
        return JSONResponse(
            content={"respuesta": "⚠️ El agente no está disponible."},
            status_code=503
        )
    try:
        respuesta = agente.ejecutar_agente(pregunta)
        return {"respuesta": respuesta}
    except Exception as error:
        print(f"[ERROR] Fallo al procesar pregunta: {error}")
        return JSONResponse(
            content={"respuesta": "⚠️ Lo siento, ocurrió un error procesando tu solicitud."},
            status_code=500
        )

# 💬 Endpoint POST para chatbot
class Pregunta(BaseModel):
    mensaje: str

@app.post("/chat")
async def chat(pregunta: Pregunta):
    agente = cargar_agente_si_es_posible()
    if not agente:
        return JSONResponse(
            content={"respuesta": "⚠️ El agente no está disponible."},
            status_code=503
        )
    try:
        respuesta = agente.ejecutar_agente(pregunta.mensaje)
        return {"respuesta": respuesta}
    except Exception as error:
        print(f"[ERROR] Fallo en /chat: {error}")
        return JSONResponse(
            content={"respuesta": "⚠️ Error interno al procesar el mensaje."},
            status_code=500
        )
if __name__ == "__main__":
    cargar_agente_si_es_posible()
    if cerebro_mod:
        respuesta = cerebro_mod.ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
        print(respuesta)
    else:
        print("❌ El agente no se pudo cargar.")
