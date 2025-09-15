# whatsapp_server.py - VERSIÓN COMPLETA FINAL CORREGIDA

import os
import logging
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
from datetime import datetime

# IMPORTACIÓN CORREGIDA - usar cerebro.py
from cerebro import ejecutar_agente_whatsapp, ejecutar_agente, inicializar_agente

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
    logger.error("Faltan credenciales de Twilio en variables de entorno")
    twilio_client = None
else:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
        logger.info("Cliente Twilio inicializado")
    except Exception as e:
        logger.error(f"Error inicializando Twilio: {e}")
        twilio_client = None

# Sistema de tracking
mensajes_procesados = set()
MAX_CACHE_SIZE = 1000

def limpiar_cache():
    """Limpia cache cuando es muy grande."""
    global mensajes_procesados
    if len(mensajes_procesados) > MAX_CACHE_SIZE:
        mensajes_procesados = set(list(mensajes_procesados)[-100:])
        logger.info("Cache de mensajes limpiado")

# FastAPI app
app = FastAPI(
    title="WhatsApp Business API - Inmobiliaria",
    version="2.0.0",
    description="API para asistente inmobiliario via web y WhatsApp"
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
            "status": "WhatsApp activo" if twilio_status else "Parcial",
            "twilio_conectado": twilio_status,
            "agente_disponible": True,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "Error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/preguntar")
async def preguntar_web(pregunta: str):
    """Endpoint para la aplicación web"""
    try:
        if not pregunta or not pregunta.strip():
            raise HTTPException(status_code=400, detail="Pregunta requerida")
        
        logger.info(f"Web query: {pregunta[:50]}...")
        respuesta = ejecutar_agente(pregunta)
        
        if not respuesta:
            respuesta = "Error procesando consulta"
        
        return {"respuesta": respuesta}
        
    except Exception as e:
        logger.error(f"Error en consulta web: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    MessageSid: str = Form(None)
):
    """Webhook para recibir mensajes de WhatsApp desde Twilio"""
    
    try:
        # Control de duplicados
        if MessageSid and MessageSid in mensajes_procesados:
            logger.info(f"Mensaje duplicado {MessageSid}, ignorando")
            return Response(content="", media_type="text/xml", status_code=200)
        
        if MessageSid:
            mensajes_procesados.add(MessageSid)
            limpiar_cache()
        
        # Log del mensaje recibido
        nombre = ProfileName or "Usuario"
        numero_log = From.replace('whatsapp:', '')[-4:] + "****"
        logger.info(f"Mensaje de {nombre} ({numero_log}): {Body[:50]}...")
        
        # Procesar mensaje con el agente
        logger.info("Procesando con agente...")
        numero_limpio = From.replace('whatsapp:', '')
        
        # Usar función específica de WhatsApp
        respuesta = ejecutar_agente_whatsapp(Body, numero_limpio)
        
        if not respuesta or respuesta.strip() == "":
            respuesta = "Lo siento, no pude procesar tu mensaje en este momento. Intenta de nuevo."
        
        # Enviar respuesta via Twilio
        if twilio_client:
            try:
                # Truncar mensaje si es muy largo para Twilio
                if len(respuesta) > 1600:
                    respuesta = respuesta[:1550] + "\n\nRespuesta completa por teléfono"
                
                message = twilio_client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    body=respuesta,
                    to=From
                )
                
                logger.info(f"Respuesta enviada - SID: {message.sid}")
                
            except Exception as send_error:
                logger.error(f"Error enviando respuesta: {send_error}")
                
                # Intentar enviar mensaje de error al usuario
                try:
                    twilio_client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        body="Disculpa, hay un problema técnico. Intenta más tarde.",
                        to=From
                    )
                except Exception as error_send_error:
                    logger.error(f"No se pudo enviar mensaje de error: {error_send_error}")
        else:
            logger.error("Cliente Twilio no disponible")
        
        # Twilio espera respuesta vacía con status 200
        return Response(content="", media_type="text/xml", status_code=200)
        
    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}")
        # Siempre devolver 200 a Twilio para evitar reenvíos
        return Response(content="", media_type="text/xml", status_code=200)

@app.get("/test")
async def test_twilio():
    """Endpoint para probar la conexión con Twilio"""
    try:
        if not twilio_client:
            return {"success": False, "error": "Cliente Twilio no inicializado"}
        
        account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        return {
            "success": True,
            "account_sid": account.sid,
            "account_status": account.status,
            "friendly_name": account.friendly_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/test-agent")
async def test_agent(request: Request):
    """Endpoint para probar el agente directamente"""
    try:
        data = await request.json()
        mensaje = data.get("mensaje", "Hola, como funciona el servicio?")
        numero_test = data.get("numero", "+34600000000")
        
        if not mensaje.strip():
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        if len(mensaje) > 1000:
            raise HTTPException(status_code=400, detail="Mensaje demasiado largo")
        
        # Test del agente
        respuesta = ejecutar_agente_whatsapp(mensaje, numero_test)
        
        return {
            "success": True,
            "pregunta": mensaje,
            "respuesta": respuesta,
            "stats": {
                "chars_respuesta": len(respuesta),
                "es_respuesta_truncada": len(respuesta) >= 1550
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en test agente: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/stats")
async def estadisticas():
    """Estadísticas del servicio"""
    return {
        "sistema": {
            "mensajes_procesados": len(mensajes_procesados),
            "cache_size": len(mensajes_procesados),
            "max_cache_size": MAX_CACHE_SIZE,
            "uptime": datetime.now().isoformat()
        },
        "twilio": {
            "conectado": bool(twilio_client),
            "numero_whatsapp": TWILIO_WHATSAPP_NUMBER
        },
        "version": "2.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar el servidor"""
    try:
        logger.info("Iniciando WhatsApp Bridge...")
        
        # Verificar conexión con Twilio
        if twilio_client:
            try:
                account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                logger.info(f"Twilio conectado - Account: {account.friendly_name}")
            except Exception as e:
                logger.error(f"Error conectando con Twilio: {e}")
        
        # Inicializar agente
        try:
            inicializar_agente()
            logger.info("Agente inicializado correctamente")
        except Exception as e:
            logger.warning(f"Agente se inicializará bajo demanda: {e}")
        
        logger.info("WhatsApp Bridge listo para recibir mensajes")
        
    except Exception as e:
        logger.error(f"Error en startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar el servidor"""
    logger.info("Cerrando WhatsApp Bridge...")

if __name__ == "__main__":
    import uvicorn
    
    # Verificaciones básicas
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY no configurada")
    else:
        logger.info("OPENAI_API_KEY encontrada")
    
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        logger.error("Credenciales Twilio incompletas")
    else:
        logger.info("Credenciales Twilio configuradas")
    
    logger.info("Iniciando servidor en http://0.0.0.0:8080")
    uvicorn.run(
        "whatsapp_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )