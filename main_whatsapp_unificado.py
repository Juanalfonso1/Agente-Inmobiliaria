# main_whatsapp_optimizado.py - VERSIÓN OPTIMIZADA PARA WHATSAPP BUSINESS

import os
import sys
import json
import requests
import hashlib
import hmac
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging

# 🔐 Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔑 Cargar variables de entorno
load_dotenv()

# 🔐 Configuraciones OBLIGATORIAS de WhatsApp Business API
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN") 
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

if not all([WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID]):
    logger.error("❌ CONFIGURACIÓN CRÍTICA FALTANTE: Variables de WhatsApp no configuradas")

# ⚠️ Variables globales para el agente
cerebro_mod = None
agente_inicializado = False
error_inicializacion = None

# 📊 Sistema de tracking de conversaciones mejorado
conversaciones_activas = {}
mensajes_procesados = set()
MAX_MENSAJES_CACHE = 500  # Evitar consumo excesivo de memoria

class MensajeWhatsApp(BaseModel):
    """Modelo para validar mensajes entrantes"""
    numero: str
    texto: str
    message_id: str

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro_unificado con mejor manejo de errores."""
    global cerebro_mod, agente_inicializado, error_inicializacion
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        if not os.path.exists('cerebro_unificado.py'):
            error_inicializacion = "cerebro_unificado.py no encontrado"
            logger.error(f"❌ {error_inicializacion}")
            return None
        
        import cerebro_unificado as cerebro_mod
        logger.info("✅ cerebro_unificado importado")
        
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

def verificar_configuracion_whatsapp():
    """Verifica configuración completa de WhatsApp."""
    config = {
        "access_token": bool(WHATSAPP_ACCESS_TOKEN),
        "phone_number_id": bool(WHATSAPP_PHONE_NUMBER_ID), 
        "verify_token": bool(WHATSAPP_VERIFY_TOKEN)
    }
    
    faltantes = [key for key, value in config.items() if not value]
    
    if faltantes:
        logger.error(f"❌ Configuración WhatsApp incompleta: {', '.join(faltantes)}")
        return False
    
    logger.info("✅ Configuración WhatsApp completa")
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando WhatsApp Business API...")
    
    config_ok = verificar_configuracion_whatsapp()
    agente = cargar_agente_si_es_posible()
    
    if agente and agente_inicializado and config_ok:
        logger.info("✅ Aplicación iniciada correctamente")
    else:
        logger.warning(f"⚠️ Aplicación con problemas - Agente: {bool(agente)}, Config: {config_ok}")
        if error_inicializacion:
            logger.error(f"Error: {error_inicializacion}")
    
    yield
    
    # Shutdown
    logger.info("🔄 Cerrando aplicación...")

# 🚀 Inicializar FastAPI
app = FastAPI(
    title="WhatsApp Business API - Inmobiliaria IA",
    description="API optimizada para asistente inmobiliario en WhatsApp",
    version="2.1.0",
    lifespan=lifespan
)

# 🏠 Endpoint raíz mejorado
@app.get("/")
async def root():
    status = "funcionando" if (cerebro_mod and agente_inicializado) else "sin agente"
    return {
        "servicio": "WhatsApp Business API Inmobiliaria",
        "status": status,
        "agente_disponible": bool(cerebro_mod and agente_inicializado),
        "whatsapp_configurado": verificar_configuracion_whatsapp(),
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0"
    }

# 🔐 Verificación del webhook de WhatsApp
@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Verificación inicial del webhook de WhatsApp."""
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        logger.info(f"🔐 Verificación webhook - Mode: {mode}")
        
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            logger.info("✅ Webhook verificado exitosamente")
            return PlainTextResponse(content=challenge)
        else:
            logger.error(f"❌ Token incorrecto - Esperado: {WHATSAPP_VERIFY_TOKEN}")
            raise HTTPException(status_code=403, detail="Token incorrecto")
    
    except Exception as e:
        logger.error(f"❌ Error verificación webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

def enviar_mensaje_whatsapp(numero_telefono: str, mensaje: str) -> bool:
    """Envía mensaje optimizado vía WhatsApp Business API."""
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Truncar mensaje si es muy largo para WhatsApp
        if len(mensaje) > 4000:
            mensaje = mensaje[:3900] + "\n\n📱 *Mensaje truncado - Contacta para info completa*"
        
        data = {
            "messaging_product": "whatsapp",
            "to": numero_telefono,
            "type": "text",
            "text": {"body": mensaje}
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Mensaje enviado a {numero_telefono}")
            return True
        else:
            logger.error(f"❌ Error enviando mensaje: {response.status_code}")
            logger.error(f"Respuesta: {response.text}")
            return False
    
    except requests.RequestException as e:
        logger.error(f"❌ Error de conexión enviando mensaje: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado enviando mensaje: {e}")
        return False

def limpiar_cache_mensajes():
    """Limpia cache de mensajes para evitar consumo excesivo de memoria."""
    global mensajes_procesados
    if len(mensajes_procesados) > MAX_MENSAJES_CACHE:
        # Mantener solo los últimos 100 mensajes
        mensajes_procesados = set(list(mensajes_procesados)[-100:])
        logger.info("🧹 Cache de mensajes limpiado")

def procesar_mensaje_whatsapp(numero_telefono: str, mensaje: str, message_id: str):
    """Procesa mensaje de WhatsApp con el agente."""
    try:
        # Control de duplicados
        if message_id in mensajes_procesados:
            logger.info(f"⚠️ Mensaje {message_id} duplicado, ignorando")
            return
        
        mensajes_procesados.add(message_id)
        limpiar_cache_mensajes()
        
        # Verificar agente disponible
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            respuesta = "⚠️ Servicio temporalmente no disponible. Intenta en unos minutos."
            enviar_mensaje_whatsapp(numero_telefono, respuesta)
            return
        
        logger.info(f"🤖 Procesando mensaje de {numero_telefono}: {mensaje[:50]}...")
        
        # Usar función específica de WhatsApp
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, numero_telefono)
        
        # Actualizar estadísticas
        conversaciones_activas[numero_telefono] = {
            "ultimo_mensaje": datetime.now(),
            "total_mensajes": conversaciones_activas.get(numero_telefono, {}).get("total_mensajes", 0) + 1
        }
        
        # Enviar respuesta
        if respuesta and respuesta.strip():
            if enviar_mensaje_whatsapp(numero_telefono, respuesta):
                logger.info(f"✅ Respuesta enviada ({len(respuesta)} chars)")
            else:
                logger.error("❌ Fallo enviando respuesta")
        else:
            enviar_mensaje_whatsapp(numero_telefono, "❌ No pude procesar tu mensaje. Intenta nuevamente.")
    
    except Exception as e:
        logger.error(f"❌ Error procesando mensaje: {e}")
        enviar_mensaje_whatsapp(numero_telefono, "⚠️ Error procesando tu mensaje. Intenta más tarde.")

# 📨 Endpoint principal para recibir mensajes
@app.post("/webhook")
async def recibir_webhook(request: Request, background_tasks: BackgroundTasks):
    """Endpoint optimizado para recibir mensajes de WhatsApp."""
    try:
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        
        logger.info("📨 Webhook recibido")
        
        if "entry" not in data:
            return JSONResponse(content={"status": "ok"})
        
        # Procesar mensajes
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                if "messages" in value:
                    for message in value["messages"]:
                        message_id = message.get("id")
                        numero_telefono = message.get("from")
                        
                        # Solo procesar mensajes de texto
                        if message.get("type") == "text":
                            texto_mensaje = message.get("text", {}).get("body", "")
                            
                            # Validar datos mínimos
                            if numero_telefono and texto_mensaje and message_id:
                                # Procesar en background
                                background_tasks.add_task(
                                    procesar_mensaje_whatsapp,
                                    numero_telefono,
                                    texto_mensaje,
                                    message_id
                                )
                            else:
                                logger.warning("⚠️ Mensaje incompleto recibido")
        
        return JSONResponse(content={"status": "ok"})
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing JSON: {e}")
        return JSONResponse(content={"error": "JSON inválido"}, status_code=400)
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}")
        return JSONResponse(content={"error": "Error interno"}, status_code=500)

# 🔧 Endpoints de monitoreo
@app.get("/health")
async def health_check():
    """Health check completo del servicio."""
    try:
        # Test de conectividad WhatsApp
        test_url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        response = requests.get(test_url, headers=headers, timeout=5)
        whatsapp_ok = response.status_code == 200
    except:
        whatsapp_ok = False
    
    return {
        "status": "healthy" if (agente_inicializado and whatsapp_ok) else "degraded",
        "agente": agente_inicializado,
        "whatsapp_api": whatsapp_ok,
        "conversaciones_activas": len(conversaciones_activas),
        "mensajes_en_cache": len(mensajes_procesados),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def estadisticas():
    """Estadísticas del servicio."""
    return {
        "conversaciones_totales": len(conversaciones_activas),
        "mensajes_procesados": len(mensajes_procesados),
        "agente_status": "activo" if agente_inicializado else "inactivo",
        "uptime": datetime.now().isoformat(),
        "top_conversaciones": [
            {
                "numero": numero[-4:] + "****",  # Privacidad
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

# 🧪 Endpoint de testing mejorado
@app.post("/test")
async def test_agente(request: Request):
    """Testing del agente con validación."""
    try:
        data = await request.json()
        mensaje = data.get("mensaje", "").strip()
        
        if not mensaje:
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        if len(mensaje) > 1000:
            raise HTTPException(status_code=400, detail="Mensaje demasiado largo")
        
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            raise HTTPException(status_code=503, detail="Agente no disponible")
        
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, "+34600000000")
        
        return {
            "pregunta": mensaje,
            "respuesta": respuesta,
            "chars_respuesta": len(respuesta),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

if __name__ == "__main__":
    logger.info("🧪 Modo desarrollo - WhatsApp Business")
    
    # Verificaciones básicas
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY no configurada")
    else:
        logger.info("✅ OPENAI_API_KEY encontrada")
    
    verificar_configuracion_whatsapp()
    
    # Test del agente
    agente = cargar_agente_si_es_posible()
    if agente and agente_inicializado:
        logger.info("✅ Agente listo para pruebas")
    else:
        logger.error(f"❌ Agente no disponible: {error_inicializacion}")
    
    try:
        import uvicorn
        logger.info("🚀 Iniciando servidor en http://0.0.0.0:8000")
        uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
    except KeyboardInterrupt:
        logger.info("🛑 Servidor detenido")
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor: {e}")
