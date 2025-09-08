# main.py

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
    "https://www.tenerifemy.com",  # Con www
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "*"  # Temporalmente permite todos los orígenes (solo para testing)
]

# ⚠️ Variables globales para el agente
cerebro_mod = None
agente_inicializado = False

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro con imports seguros."""
    global cerebro_mod, agente_inicializado
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        import cerebro as cerebro_mod  # Importa directamente cerebro.py
        
        # Inicializar el agente
        cerebro_mod.inicializar_agente()
        agente_inicializado = True
        
        print("✅ Agente cargado e inicializado correctamente.")
        return cerebro_mod
        
    except Exception as error:
        print(f"[WARN] No se pudo importar o inicializar cerebro: {error}")
        return None

# 🔄 Ciclo de vida de la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    agente = cargar_agente_si_es_posible()
    if agente:
        print("✅ Agente inicializado correctamente.")
    else:
        print("⚠️ No se pudo inicializar el agente.")
    
    yield
    
    # Shutdown (si necesitas limpieza)
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
        # Usar directamente la función ejecutar_agente del módulo
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
        # Usar directamente la función ejecutar_agente del módulo
        respuesta = agente.ejecutar_agente(pregunta.mensaje)
        return {"respuesta": respuesta}
        
    except Exception as error:
        print(f"[ERROR] Fallo en /chat: {error}")
        return JSONResponse(
            content={"respuesta": "⚠️ Error interno al procesar el mensaje."},
            status_code=500
        )

# 🧪 Para pruebas en desarrollo
if __name__ == "__main__":
    # Prueba local
    agente = cargar_agente_si_es_posible()
    if agente:
        respuesta = agente.ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
        print("Respuesta de prueba:", respuesta)
    else:
        print("❌ El agente no se pudo cargar.")
        
    # Ejecutar servidor
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)