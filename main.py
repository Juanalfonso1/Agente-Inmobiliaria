import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 🔑 Cargar variables de entorno (.env)
load_dotenv()

# 🚀 Inicializar FastAPI
app = FastAPI()

# 🏠 Endpoint raíz (acepta GET y HEAD)
@app.api_route("/", methods=["GET", "HEAD"])
def home():
    return JSONResponse(content={"message": "Agente Inmobiliario en línea 🚀"})

# 🔐 Dominios permitidos para CORS
ALLOWED_ORIGINS = [
    "https://tenerifemy.com",     # ⚡ tu web real
    "http://localhost:5500",      # pruebas en local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🤖 Endpoint del agente
@app.get("/preguntar")
async def preguntar(pregunta: str = Query(..., description="Pregunta del usuario")):
    try:
        from cerebro import ejecutar_agente  # ✅ import correcto
        respuesta = ejecutar_agente(pregunta)
        return {"respuesta": respuesta}
    except Exception as e:
        print(f"[ERROR] El agente no pudo responder: {e}")
        return JSONResponse(
            content={"respuesta": "⚠️ Lo siento, ocurrió un error procesando tu solicitud."},
            status_code=500
        )
