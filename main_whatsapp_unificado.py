# main_twilio_whatsapp_optimizado.py - VERSIÓN OPTIMIZADA PARA TWILIO WHATSAPP

import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import hashlib
import hmac

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuraciones OBLIGATORIAS de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Verificar configuración crítica
if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
    logger.error("❌ CONFIGURACIÓN CRÍTICA FALTANTE: Credenciales Twilio no configuradas")

# Variables globales para el agente
cerebro_mod = None
agente_inicializado = False
error_inicializacion = None

# Sistema de tracking optimizado
conversaciones_activas = {}
mensajes_procesados = set()
MAX_MENSAJES_CACHE = 500

# Inicializar cliente Twilio
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
    logger.info("✅ Cliente Twilio inicializado")
except Exception as e:
    logger.error(f"❌ Error inicializando Twilio: {e}")
    twilio_client = None
    request_validator = None

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro_unificado con mejor manejo de errores."""
    global cerebro_mod, agente_inicializado, error_inicializacion
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        if not os.path.exists('cerebro_unificado_optimizado.py'):
            error_inicializacion = "cerebro_unificado_optimizado.py no encontrado"
            logger.error(f"❌ {error_inicializacion}")
            return None
        
        import cerebro_unificado_optimizado as cerebro_mod
        logger.info("✅ cerebro_unificado_optimizado importado")
        
        resultado = cerebro_mod.inicializar_agente()
        
        if resultado is not None:
            agente_inicializado = True
            error_inicializacion = None
            logger.info("✅ Agente inicializado correctamente")
            return cerebro_mod
        else:
            error_inicializacion = "Agente no se inicializó"
            logger.error(f"❌ {error_inicializacion}")
            return None
            
    except Exception as error:
        error_inicializacion = f"Error cargando agente: {str(error)}"
        logger.error(f"❌ {error_inicializacion}")
        return None

def verificar_configuracion_twilio():
    """Verifica configuración completa de Twilio."""
    config = {
        "account_sid": bool(TWILIO_ACCOUNT_SID),
        "auth_token": bool(TWILIO_AUTH_TOKEN),
        "whatsapp_number": bool(TWILIO_WHATSAPP_NUMBER),
        "client_initialized": bool(twilio_client)
    }
    
    faltantes = [key for key, value in config.items() if not value]
    
    if faltantes:
        logger.error(f"❌ Configuración Twilio incompleta: {', '.join(faltantes)}")
        return False
    
    logger.info("✅ Configuración Twilio completa")
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando Twilio WhatsApp Service...")
    
    config_ok = verificar_configuracion_twilio()
    agente = cargar_agente_si_es_posible()
    
    # Test conexión Twilio
    if twilio_client and config_ok:
        try:
            account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
            logger.info(f"✅ Twilio conectado - Account: {account.friendly_name}")
        except Exception as e:
            logger.error(f"❌ Error conectando con Twilio: {e}")
    
    if agente and agente_inicializado and config_ok:
        logger.info("✅ Sistema iniciado correctamente")
    else:
        logger.warning(f"⚠️ Sistema con problemas - Agente: {bool(agente)}, Twilio: {config_ok}")
        if error_inicializacion:
            logger.error(f"Error: {error_inicializacion}")
    
    yield
    
    # Shutdown
    logger.info("🔄 Cerrando sistema...")

# Inicializar FastAPI
app = FastAPI(
    title="Twilio WhatsApp Business API - Inmobiliaria IA",
    description="API optimizada para asistente inmobiliario via Twilio WhatsApp",
    version="2.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema."""
    try:
        # Test rápido de Twilio
        twilio_status = False
        if twilio_client:
            try:
                account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                twilio_status = True
            except:
                twilio_status = False
        
        status = "funcionando" if (cerebro_mod and agente_inicializado and twilio_status) else "parcial"
        
        return {
            "servicio": "Twilio WhatsApp Inmobiliaria IA",
            "status": status,
            "agente_disponible": bool(cerebro_mod and agente_inicializado),
            "twilio_conectado": twilio_status,
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "error_agente": error_inicializacion
        }
    except Exception as e:
        logger.error(f"❌ Error en root endpoint: {e}")
        return {"error": str(e)}

def enviar_mensaje_twilio(numero: str, mensaje: str) -> bool:
    """Envía mensaje optimizado via Twilio WhatsApp."""
    if not twilio_client:
        logger.error("❌ Cliente Twilio no disponible")
        return False
    
    try:
        # Asegurar formato WhatsApp
        if not numero.startswith('whatsapp:'):
            numero = f"whatsapp:{numero}"
        
        # Truncar mensaje si es muy largo
        if len(mensaje) > 1600:  # Twilio tiene límites más estrictos
            mensaje = mensaje[:1550] + "\n\n📱 *Respuesta completa por teléfono*"
        
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=mensaje,
            to=numero
        )
        
        logger.info(f"✅ Mensaje Twilio enviado - SID: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje Twilio: {e}")
        return False

def limpiar_cache_mensajes():
    """Limpia cache para optimizar memoria."""
    global mensajes_procesados
    if len(mensajes_procesados) > MAX_MENSAJES_CACHE:
        mensajes_procesados = set(list(mensajes_procesados)[-100:])
        logger.info("🧹 Cache de mensajes limpiado")

def procesar_mensaje_twilio(numero: str, mensaje: str, message_sid: str):
    """Procesa mensaje de Twilio WhatsApp con el agente."""
    try:
        # Control de duplicados
        if message_sid in mensajes_procesados:
            logger.info(f"⚠️ Mensaje {message_sid} duplicado, ignorando")
            return
        
        mensajes_procesados.add(message_sid)
        limpiar_cache_mensajes()
        
        # Verificar agente disponible
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            respuesta = "⚠️ Servicio temporalmente no disponible. Intenta en unos minutos."
            enviar_mensaje_twilio(numero, respuesta)
            return
        
        # Limpiar número (remover whatsapp: prefix para logging)
        numero_limpio = numero.replace('whatsapp:', '')
        logger.info(f"🤖 Procesando mensaje de {numero_limpio[-4:]}****: {mensaje[:50]}...")
        
        # Usar función específica de WhatsApp del agente
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, numero_limpio)
        
        # Actualizar estadísticas
        conversaciones_activas[numero] = {
            "ultimo_mensaje": datetime.now(),
            "total_mensajes": conversaciones_activas.get(numero, {}).get("total_mensajes", 0) + 1
        }
        
        # Enviar respuesta
        if respuesta and respuesta.strip():
            if enviar_mensaje_twilio(numero, respuesta):
                logger.info(f"✅ Respuesta enviada ({len(respuesta)} chars)")
            else:
                logger.error("❌ Fallo enviando respuesta")
        else:
            enviar_mensaje_twilio(numero, "❌ No pude procesar tu mensaje. Intenta nuevamente.")
    
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        enviar_mensaje_twilio(numero, "⚠️ Error procesando tu mensaje. Intenta más tarde.")

@app.post("/webhook")
async def twilio_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    ProfileName: str = Form(None)
):
    """Webhook optimizado para recibir mensajes de Twilio WhatsApp."""
    try:
        # Log del mensaje recibido
        nombre = ProfileName or "Usuario"
        numero_log = From.replace('whatsapp:', '')[-4:] + "****"
        logger.info(f"📨 Mensaje de {nombre} ({numero_log}): {Body[:50]}...")
        logger.info(f"MessageSid: {MessageSid}")
        
        # Validación opcional del webhook (recomendado para producción)
        # Descomenta para mayor seguridad:
        # form_data = await request.form()
        # url = str(request.url)
        # signature = request.headers.get('X-Twilio-Signature', '')
        # if not request_validator.validate(url, dict(form_data), signature):
        #     logger.warning("❌ Webhook signature inválida")
        #     raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Procesar mensaje en background para no bloquear Twilio
        background_tasks.add_task(
            procesar_mensaje_twilio,
            From,
            Body,
            MessageSid
        )
        
        # Twilio espera respuesta TwiML vacía
        response = MessagingResponse()
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ Error en webhook Twilio: {e}")
        
        # Siempre devolver respuesta válida a Twilio
        response = MessagingResponse()
        return Response(content=str(response), media_type="application/xml")

@app.get("/health")
async def health_check():
    """Health check completo del sistema."""
    try:
        # Test Twilio
        twilio_ok = False
        account_info = None
        if twilio_client:
            try:
                account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                twilio_ok = True
                account_info = {
                    "status": account.status,
                    "name": account.friendly_name
                }
            except Exception as e:
                logger.error(f"Error testing Twilio: {e}")
        
        # Test agente
        agente_ok = bool(cerebro_mod and agente_inicializado)
        
        overall_status = "healthy" if (twilio_ok and agente_ok) else "degraded"
        
        return {
            "status": overall_status,
            "components": {
                "twilio": {
                    "status": "ok" if twilio_ok else "error",
                    "account": account_info
                },
                "agente": {
                    "status": "ok" if agente_ok else "error",
                    "error": error_inicializacion
                },
                "openai": {
                    "status": "ok" if os.getenv("OPENAI_API_KEY") else "error"
                }
            },
            "stats": {
                "conversaciones_activas": len(conversaciones_activas),
                "mensajes_en_cache": len(mensajes_procesados)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/stats")
async def estadisticas():
    """Estadísticas detalladas del servicio."""
    return {
        "sistema": {
            "conversaciones_totales": len(conversaciones_activas),
            "mensajes_procesados": len(mensajes_procesados),
            "agente_status": "activo" if agente_inicializado else "inactivo",
            "uptime": datetime.now().isoformat()
        },
        "top_conversaciones": [
            {
                "numero": numero.replace('whatsapp:', '')[-4:] + "****",
                "mensajes": info["total_mensajes"],
                "ultimo_contacto": info["ultimo_mensaje"].isoformat()
            }
            for numero, info in sorted(
                conversaciones_activas.items(), 
                key=lambda x: x[1]["total_mensajes"], 
                reverse=True
            )[:5]
        ]
    }

@app.post("/test")
async def test_sistema(request: Request):
    """Test completo del sistema."""
    try:
        data = await request.json()
        mensaje = data.get("mensaje", "Hola, ¿cómo funciona el servicio?").strip()
        numero_test = data.get("numero", "+34600000000")
        
        if not mensaje:
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        if len(mensaje) > 1000:
            raise HTTPException(status_code=400, detail="Mensaje demasiado largo")
        
        # Test del agente
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            raise HTTPException(status_code=503, detail="Agente no disponible")
        
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, numero_test)
        
        # Test opcional de Twilio (sin enviar mensaje real)
        twilio_test = False
        if twilio_client:
            try:
                # Solo test de conectividad, no envía mensaje
                account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                twilio_test = True
            except:
                twilio_test = False
        
        return {
            "test_results": {
                "agente": "ok",
                "twilio": "ok" if twilio_test else "error",
                "respuesta_generada": True
            },
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
        logger.error(f"❌ Error en test: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

@app.post("/send-test-message")
async def enviar_mensaje_test(request: Request):
    """Endpoint para enviar mensaje de prueba real via Twilio."""
    try:
        data = await request.json()
        numero = data.get("numero", "").strip()
        mensaje = data.get("mensaje", "Test desde API").strip()
        
        if not numero:
            raise HTTPException(status_code=400, detail="Número requerido")
        
        if not mensaje:
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        # Validar formato de número
        if not numero.startswith('+'):
            numero = '+' + numero
        
        success = enviar_mensaje_twilio(numero, mensaje)
        
        if success:
            return {
                "status": "enviado",
                "numero": numero,
                "mensaje": mensaje,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Error enviando mensaje")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje test: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

if __name__ == "__main__":
    logger.info("🧪 Modo desarrollo - Twilio WhatsApp")
    
    # Verificaciones básicas
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY no configurada")
    else:
        logger.info("✅ OPENAI_API_KEY encontrada")
    
    verificar_configuracion_twilio()
    
    # Test del agente
    agente = cargar_agente_si_es_posible()
    if agente and agente_inicializado:
        logger.info("✅ Agente listo para pruebas")
    else:
        logger.error(f"❌ Agente no disponible: {error_inicializacion}")
    
    try:
        import uvicorn
        logger.info("🚀 Iniciando servidor Twilio en http://0.0.0.0:8000")
        uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
    except KeyboardInterrupt:
        logger.info("🛑 Servidor detenido")
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor: {e}")
