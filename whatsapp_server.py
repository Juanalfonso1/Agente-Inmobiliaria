# whatsapp_server.py
import os
import logging
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
from datetime import datetime
from cerebro_unificado import ejecutar_agente, inicializar_agente

load_dotenv()

# Configuración logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración Twilio - CORREGIDO
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") 
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Validación de credenciales
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    logger.error("❌ Faltan credenciales de Twilio en variables de entorno")
    raise ValueError("Credenciales de Twilio no configuradas")

# Inicializar cliente Twilio
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
request_validator = RequestValidator(TWILIO_AUTH_TOKEN)

# FastAPI app
app = FastAPI(
    title="WhatsApp Bridge",
    version="1.0.0",
    description="Puente entre WhatsApp y asistente virtual via Twilio"
)

@app.get("/")
async def health():
    """Endpoint de salud del servicio"""
    try:
        # Verificar conexión con Twilio
        account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        return {
            "status": "🟢 WhatsApp activo", 
            "twilio": True,
            "account_status": account.status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error verificando Twilio: {e}")
        return {
            "status": "🟡 Servicio activo, Twilio con problemas",
            "twilio": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    MessageSid: str = Form(None)
):
    """Webhook para recibir mensajes de WhatsApp desde Twilio"""
    
    # Log del mensaje recibido
    logger.info(f"📨 Mensaje de {ProfileName or 'Usuario'} ({From}): {Body}")
    logger.info(f"MessageSid: {MessageSid}")
    
    try:
        # Validar webhook de Twilio (opcional pero recomendado)
        # Descomenta estas líneas para mayor seguridad:
        # form_data = await request.form()
        # url = str(request.url)
        # if not request_validator.validate(url, form_data, request.headers.get('X-Twilio-Signature', '')):
        #     logger.warning("❌ Webhook no válido de Twilio")
        #     raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Procesar mensaje con el agente
        logger.info("🤖 Procesando con agente...")
        respuesta = ejecutar_agente(Body)
        
        if not respuesta or respuesta.strip() == "":
            respuesta = "⚠️ Lo siento, no pude procesar tu mensaje en este momento. Intenta de nuevo."
        
        # Enviar respuesta via Twilio
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=respuesta,
            to=From
        )
        
        logger.info(f"✅ Respuesta enviada - SID: {message.sid}")
        logger.info(f"📤 Respuesta: {respuesta[:100]}{'...' if len(respuesta) > 100 else ''}")
        
        # Twilio espera respuesta vacía con status 200
        return Response(content="", media_type="text/xml", status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        
        # Intentar enviar mensaje de error al usuario
        try:
            twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body="🔧 Disculpa, hay un problema técnico. Intenta más tarde.",
                to=From
            )
        except Exception as send_error:
            logger.error(f"❌ No se pudo enviar mensaje de error: {send_error}")
        
        # Siempre devolver 200 a Twilio para evitar reenvíos
        return Response(content="", media_type="text/xml", status_code=200)

@app.get("/test")
async def test_twilio():
    """Endpoint para probar la conexión con Twilio"""
    try:
        account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        return {
            "success": True,
            "account_sid": account.sid,
            "account_status": account.status,
            "friendly_name": account.friendly_name
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar el servidor"""
    try:
        logger.info("🚀 Iniciando WhatsApp Bridge...")
        
        # Verificar conexión con Twilio
        account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        logger.info(f"✅ Twilio conectado - Account: {account.friendly_name}")
        
        # Inicializar agente
        inicializar_agente()
        logger.info("✅ Agente inicializado correctamente")
        
        logger.info("🎉 WhatsApp Bridge listo para recibir mensajes")
        
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar el servidor"""
    logger.info("🔄 Cerrando WhatsApp Bridge...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "whatsapp_server:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        log_level="info"
    )