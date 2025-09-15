# whatsapp_server.py - VERSIÓN CORREGIDA

import os
import logging
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
from datetime import datetime

# IMPORTACIÓN CORREGIDA
from cerebro import ejecutar_agente_whatsapp, inicializar_agente

load_dotenv()

# Configuración logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Validación de credenciales
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    logger.error("❌ Faltan credenciales de Twilio en variables de entorno")
    raise ValueError("Credenciales de Twilio no configuradas")

# Inicializar cliente Twilio
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
    logger.info("✅ Cliente Twilio inicializado")
except Exception as e:
    logger.error(f"❌ Error inicializando Twilio: {e}")
    twilio_client = None
    request_validator = None

# FastAPI app
app = FastAPI(
    title="WhatsApp Business API - Inmobiliaria",
    version="2.0.0",
    description="API optimizada para asistente inmobiliario via WhatsApp"
)

@app.get("/")
async def health():
    """Endpoint de salud del servicio"""
    try:
        twilio_status = False
        if twilio_client:
            try:
                account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                twilio_status = True
            except:
                twilio_status = False
        
        return {
            "status": "🟢 WhatsApp activo" if twilio_status else "🟡 Parcial",
            "twilio_conectado": twilio_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "🔴 Error", "error": str(e)}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    MessageSid: str = Form(None)
):
    """Webhook para recibir mensajes de WhatsApp desde Twilio"""
    
    try:
        # Log del mensaje recibido
        nombre = ProfileName or "Usuario"
        numero_log = From.replace('whatsapp:', '')[-4:] + "****"
        logger.info(f"📨 Mensaje de {nombre} ({numero_log}): {Body[:50]}...")
        
        # Procesar mensaje con el agente
        logger.info("🤖 Procesando con agente...")
        numero_limpio = From.replace('whatsapp:', '')
        respuesta = ejecutar_agente_whatsapp(Body, numero_limpio)
        
        if not respuesta or respuesta.strip() == "":
            respuesta = "⚠️ Lo siento, no pude procesar tu mensaje en este momento. Intenta de nuevo."
        
        # Enviar respuesta via Twilio
        if twilio_client:
            try:
                message = twilio_client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    body=respuesta,
                    to=From
                )
                logger.info(f"✅ Respuesta enviada - SID: {message.sid}")
            except Exception as send_error:
                logger.error(f"❌ Error enviando respuesta: {send_error}")
        
        return Response(content="", media_type="text/xml", status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Error en webhook WhatsApp: {e}")
        return Response(content="", media_type="text/xml", status_code=200)

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar el servidor"""
    try:
        logger.info("🚀 Iniciando WhatsApp Bridge...")
        inicializar_agente()
        logger.info("✅ Agente inicializado correctamente")
    except Exception as e:
        logger.warning(f"⚠️ Agente se inicializará bajo demanda: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("whatsapp_server:app", host="0.0.0.0", port=8001, reload=True)