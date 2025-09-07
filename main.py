import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# ⚠️ Import perezoso de cerebro (no al nivel global)
cerebro_mod = None

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro con imports seguros."""
    global cerebro_mod
    if cerebro_mod:
        return cerebro_mod
    try:
        from agente import cerebro as cerebro_module
        cerebro_mod = cerebro_module
        return cerebro_mod
    except Exception as e:
        print(f"[WARN] No se pudo importar agente.cerebro: {e}")
        return None

# --- Ciclo de vida FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    agente = cargar_agente_si_es_posible()
    if agente:
        try:
            agente.inicializar_agente()
        except Exception as e:
            print(f"[ERROR] Falló la inicialización del agente: {e}")
    yield

# --- Configuración FastAPI ---
app = FastAPI(lifespan=lifespan)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta según tus necesidades
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---
@app.get("/")
async def root():
    return {"mensaje": "API Inmobiliaria IA funcionando correctamente."}

@app.get("/preguntar/")
async def preguntar(pregunta: str):
    agente = cargar_agente_si_es_posible()
    if not agente:
        return {"respuesta": "El agente no está disponible."}
    return {"respuesta": agente.ejecutar_agente(pregunta)}
