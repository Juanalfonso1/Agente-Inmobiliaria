import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

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
    "http://localhost:5500",      # para pruebas en local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/preguntar")
async def preguntar(pregunta: str = Query(..., description="Pregunta del usuario")):
    try:
        from cerebro import ejecutar_agente  # ⬅️ import correcto
        respuesta = ejecutar_agente(pregunta)  # ⬅️ llamada directa, sin .run()
        return {"respuesta": respuesta}
    except Exception as e:
        print(f"[ERROR] El agente no pudo responder: {e}")
        return JSONResponse(
            content={"respuesta": "⚠️ Lo siento, ocurrió un error procesando tu solicitud."},
            status_code=500
        )



# ⚠️ Import perezoso de cerebro (no al nivel global, todavía no usado)
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

# --- NUEVO: Endpoint para el chatbot ---
class Pregunta(BaseModel):
    mensaje: str

@app.post("/chat")
async def chat(pregunta: Pregunta):
    agente = cargar_agente_si_es_posible()
    if not agente:
        return {"respuesta": "El agente no está disponible."}
    return {"respuesta": agente.ejecutar_agente(pregunta.mensaje)}
from cerebro import crear_agente  # asegúrate de que cerebro.py tiene esta función
