# main_whatsapp_unificado.py - VERSIÓN PARA WHATSAPP BUSINESS CON CEREBRO UNIFICADO

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

# 🔑 Cargar variables de entorno
load_dotenv()

# 🔐 Configuraciones de WhatsApp Business API
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "mi_token_verificacion")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", WHATSAPP_VERIFY_TOKEN)

# ⚠️ Variables globales para el agente
cerebro_mod = None
agente_inicializado = False
error_inicializacion = None

# 📊 Sistema de tracking de conversaciones
conversaciones_activas = {}
mensajes_procesados = set()

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro_unificado con imports seguros."""
    global cerebro_mod, agente_inicializado, error_inicializacion
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        # CAMBIO PRINCIPAL: Verificar si cerebro_unificado.py existe
        if not os.path.exists('cerebro_unificado.py'):
            error_inicializacion = "No se encuentra el archivo cerebro_unificado.py"
            print(f"[ERROR] {error_inicializacion}")
            return None
        
        # CAMBIO PRINCIPAL: Importar cerebro_unificado
        import cerebro_unificado as cerebro_mod
        print("✅ Módulo cerebro_unificado importado correctamente.")
        
        # Inicializar el agente
        resultado = cerebro_mod.inicializar_agente()
        
        if resultado is not None:
            agente_inicializado = True
            error_inicializacion = None
            print("✅ Agente unificado cargado e inicializado correctamente.")
            return cerebro_mod
        else:
            error_inicializacion = "El agente unificado no se inicializó correctamente"
            print(f"[ERROR] {error_inicializacion}")
            return None
            
    except ImportError as e:
        error_inicializacion = f"Error de importación: {str(e)}"
        print(f"[ERROR] {error_inicializacion}")
        return None
        
    except Exception as error:
        error_inicializacion = f"Error inesperado: {str(error)}"
        print(f"[ERROR] {error_inicializacion}")
        return None

def verificar_configuracion_whatsapp():
    """Verifica que las variables de entorno de WhatsApp estén configuradas."""
    configuracion = {
        "access_token": bool(WHATSAPP_ACCESS_TOKEN),
        "phone_number_id": bool(WHATSAPP_PHONE_NUMBER_ID),
        "verify_token": bool(WHATSAPP_VERIFY_TOKEN)
    }
    
    faltantes = [key for key, value in configuracion.items() if not value]
    
    if faltantes:
        print(f"❌ Faltan configuraciones de WhatsApp: {', '.join(faltantes)}")
        return False
    
    print("✅ Configuración de WhatsApp completa.")
    return True

# 🔄 Ciclo de vida de la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicación WhatsApp Business...")
    
    # Verificar configuración de WhatsApp
    config_ok = verificar_configuracion_whatsapp()
    
    # Cargar agente
    agente = cargar_agente_si_es_posible()
    
    if agente and agente_inicializado and config_ok:
        print("✅ Aplicación WhatsApp iniciada correctamente con agente unificado.")
    else:
        print(f"⚠️ Aplicación iniciada con problemas. Agente: {bool(agente)}, Config: {config_ok}")
        if error_inicializacion:
            print(f"   Error agente: {error_inicializacion}")
    
    yield
    
    # Shutdown
    print("🔄 Cerrando aplicación WhatsApp...")

# 🚀 Inicializar FastAPI con ciclo de vida
app = FastAPI(
    title="WhatsApp Business API - Inmobiliaria IA (Unificado)",
    description="API para asistente virtual inmobiliario en WhatsApp con cerebro unificado",
    version="2.0.0",
    lifespan=lifespan
)

# 🏠 Endpoint raíz
@app.get("/")
async def root():
    status = "funcionando" if (cerebro_mod and agente_inicializado) else "sin agente"
    return {
        "mensaje": f"WhatsApp Business API Inmobiliaria IA {status} (Cerebro Unificado).",
        "agente_disponible": bool(cerebro_mod and agente_inicializado),
        "whatsapp_configurado": verificar_configuracion_whatsapp(),
        "cerebro_tipo": "unificado",
        "error_inicializacion": error_inicializacion
    }

# 🔐 Verificación del webhook de WhatsApp
@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Endpoint para verificación inicial del webhook de WhatsApp."""
    try:
        # Obtener parámetros de la query
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        print(f"[WEBHOOK] Verificación - Mode: {mode}, Token recibido: {token}")
        
        # Verificar que sea una suscripción con el token correcto
        if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente")
            return PlainTextResponse(content=challenge)
        else:
            print(f"❌ Token incorrecto. Esperado: {WEBHOOK_VERIFY_TOKEN}, Recibido: {token}")
            raise HTTPException(status_code=403, detail="Token de verificación incorrecto")
    
    except Exception as e:
        print(f"[ERROR] Error en verificación webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

def enviar_mensaje_whatsapp(numero_telefono: str, mensaje: str):
    """Envía un mensaje a través de WhatsApp Business API."""
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": numero_telefono,
            "type": "text",
            "text": {"body": mensaje}
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Mensaje enviado a {numero_telefono}")
            return True
        else:
            print(f"❌ Error enviando mensaje: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"[ERROR] Excepción enviando mensaje: {e}")
        return False

def procesar_mensaje_whatsapp(numero_telefono: str, mensaje: str, message_id: str):
    """Procesa un mensaje recibido de WhatsApp usando el agente unificado."""
    try:
        # Evitar procesar mensajes duplicados
        if message_id in mensajes_procesados:
            print(f"[INFO] Mensaje {message_id} ya procesado, ignorando")
            return
        
        mensajes_procesados.add(message_id)
        
        # Limitar tamaño del set para evitar consumo excesivo de memoria
        if len(mensajes_procesados) > 1000:
            mensajes_procesados.clear()
        
        # Verificar agente disponible
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            respuesta = "⚠️ El servicio no está disponible temporalmente. Intenta más tarde."
            enviar_mensaje_whatsapp(numero_telefono, respuesta)
            return
        
        print(f"[INFO] Procesando mensaje de {numero_telefono}: {mensaje[:50]}...")
        
        # CAMBIO PRINCIPAL: Usar la función de WhatsApp del cerebro unificado
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, numero_telefono)
        
        # Registrar conversación
        conversaciones_activas[numero_telefono] = {
            "ultimo_mensaje": datetime.now(),
            "total_mensajes": conversaciones_activas.get(numero_telefono, {}).get("total_mensajes", 0) + 1
        }
        
        # Enviar respuesta
        if respuesta:
            enviar_mensaje_whatsapp(numero_telefono, respuesta)
        else:
            enviar_mensaje_whatsapp(numero_telefono, "❌ No pude procesar tu mensaje. Intenta nuevamente.")
    
    except Exception as e:
        print(f"[ERROR] Error procesando mensaje: {e}")
        enviar_mensaje_whatsapp(numero_telefono, "⚠️ Ocurrió un error procesando tu mensaje.")

# 📨 Endpoint principal para recibir mensajes de WhatsApp
@app.post("/webhook")
async def recibir_webhook(request: Request, background_tasks: BackgroundTasks):
    """Endpoint para recibir mensajes de WhatsApp."""
    try:
        # Obtener el cuerpo de la petición
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        
        print(f"[WEBHOOK] Mensaje recibido: {json.dumps(data, indent=2)}")
        
        # Verificar que sea un mensaje
        if "entry" not in data:
            return JSONResponse(content={"status": "ok"})
        
        # Procesar cada entrada
        for entry in data.get("entry", []):
            # Verificar cambios de WhatsApp
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Verificar si hay mensajes
                if "messages" in value:
                    for message in value["messages"]:
                        # Extraer información del mensaje
                        message_id = message.get("id")
                        numero_telefono = message.get("from")
                        
                        # Solo procesar mensajes de texto
                        if message.get("type") == "text":
                            texto_mensaje = message.get("text", {}).get("body", "")
                            
                            # Procesar en background para no bloquear el webhook
                            background_tasks.add_task(
                                procesar_mensaje_whatsapp, 
                                numero_telefono, 
                                texto_mensaje,
                                message_id
                            )
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        print(f"[ERROR] Error en webhook: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 🔧 Endpoint de estado para debugging
@app.get("/status")
async def status():
    return {
        "agente_modulo_cargado": bool(cerebro_mod),
        "agente_inicializado": agente_inicializado,
        "cerebro_tipo": "unificado",
        "error_inicializacion": error_inicializacion,
        "openai_key_configurada": bool(os.getenv("OPENAI_API_KEY")),
        "directorio_conocimiento_existe": os.path.exists("conocimiento"),
        "whatsapp_access_token": bool(WHATSAPP_ACCESS_TOKEN),
        "whatsapp_phone_number_id": bool(WHATSAPP_PHONE_NUMBER_ID),
        "whatsapp_verify_token": bool(WHATSAPP_VERIFY_TOKEN),
        "conversaciones_activas": len(conversaciones_activas),
        "mensajes_procesados": len(mensajes_procesados)
    }

# 📊 Endpoint para estadísticas (opcional)
@app.get("/estadisticas")
async def estadisticas():
    return {
        "conversaciones_totales": len(conversaciones_activas),
        "mensajes_procesados_sesion": len(mensajes_procesados),
        "conversaciones_activas": {
            numero: {
                "ultimo_mensaje": str(info["ultimo_mensaje"]),
                "total_mensajes": info["total_mensajes"]
            }
            for numero, info in list(conversaciones_activas.items())[-10:]  # Últimas 10
        }
    }

# 💬 Endpoint manual para testing (opcional)
@app.post("/test-mensaje")
async def test_mensaje(request: Request):
    """Endpoint para testing manual del agente."""
    try:
        data = await request.json()
        mensaje = data.get("mensaje", "")
        numero_test = data.get("numero", "+34600000000")
        
        if not mensaje:
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        # Verificar agente
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            raise HTTPException(status_code=503, detail="Agente no disponible")
        
        # CAMBIO: Usar función específica de WhatsApp del cerebro unificado
        respuesta = agente.ejecutar_agente_whatsapp(mensaje, numero_test)
        
        return {"pregunta": mensaje, "respuesta": respuesta, "plataforma": "whatsapp"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🧪 Endpoint adicional para comparar respuestas WEB vs WhatsApp
@app.post("/test-comparacion")
async def test_comparacion(request: Request):
    """Endpoint para comparar respuestas entre WEB y WhatsApp."""
    try:
        data = await request.json()
        mensaje = data.get("mensaje", "")
        numero_test = data.get("numero", "+34600000000")
        
        if not mensaje:
            raise HTTPException(status_code=400, detail="Mensaje requerido")
        
        # Verificar agente
        agente = cargar_agente_si_es_posible()
        if not agente or not agente_inicializado:
            raise HTTPException(status_code=503, detail="Agente no disponible")
        
        # Obtener respuesta para WEB
        respuesta_web = agente.ejecutar_agente(mensaje)
        
        # Obtener respuesta para WhatsApp
        respuesta_whatsapp = agente.ejecutar_agente_whatsapp(mensaje, numero_test)
        
        return {
            "pregunta": mensaje,
            "respuesta_web": respuesta_web,
            "respuesta_whatsapp": respuesta_whatsapp,
            "comparacion": {
                "longitud_web": len(respuesta_web),
                "longitud_whatsapp": len(respuesta_whatsapp),
                "diferencia_caracteres": len(respuesta_web) - len(respuesta_whatsapp)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🧪 Para pruebas en desarrollo
if __name__ == "__main__":
    print("🧪 Modo de prueba WhatsApp Business con Cerebro Unificado...")
    
    # Verificar configuración básica
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY no está configurada")
    else:
        print("✅ OPENAI_API_KEY encontrada")
    
    # Verificar configuración WhatsApp
    verificar_configuracion_whatsapp()
    
    # Probar agente
    agente = cargar_agente_si_es_posible()
    if agente and agente_inicializado:
        # Test WhatsApp
        respuesta_whatsapp = agente.ejecutar_agente_whatsapp("Hola, ¿cómo estás?", "+34600000000")
        print(f"✅ Respuesta WhatsApp: {respuesta_whatsapp}")
        
        # Test WEB (para comparar)
        respuesta_web = agente.ejecutar_agente("Hola, ¿cómo estás?")
        print(f"✅ Respuesta WEB: {respuesta_web}")
        
        print(f"📊 Diferencia de longitud: {len(respuesta_web) - len(respuesta_whatsapp)} caracteres")
    else:
        print(f"❌ No se pudo cargar el agente: {error_inicializacion}")
    
    # Ejecutar servidor
    try:
        import uvicorn
        print("🚀 Iniciando servidor WhatsApp Unificado en http://0.0.0.0:8080")
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
