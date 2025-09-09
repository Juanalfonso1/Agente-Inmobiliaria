# =====================================================
# WHATSAPP_SERVER.PY - Bridge para WhatsApp Business
# Integración con tu agente inmobiliario existente
# =====================================================

import os
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response
import uvicorn
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import logging
from datetime import datetime
import json
from typing import Dict, Any

# =====================================================
# IMPORTAR TU AGENTE EXISTENTE
# =====================================================

# Importar tu sistema existente
from cerebro import ejecutar_agente, inicializar_agente

# =====================================================
# CONFIGURACIÓN Y SETUP
# =====================================================

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')  
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Validar configuración
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    logger.error("❌ Faltan credenciales de Twilio en .env")
    logger.error("   Agrega: TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN")

# Cliente de Twilio (solo si hay credenciales)
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("✅ Cliente de Twilio inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando Twilio: {e}")

# FastAPI app para WhatsApp
app = FastAPI(
    title="WhatsApp Bridge - Agente Inmobiliario",
    description="Conecta tu agente inmobiliario con WhatsApp Business",
    version="2.0.0"
)

# =====================================================
# GESTIÓN DE SESIONES WHATSAPP
# =====================================================

class WhatsAppSessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = 1000  # Límite de sesiones en memoria
    
    def clean_phone(self, phone: str) -> str:
        """Limpia el formato del número de teléfono"""
        return phone.replace('whatsapp:', '').replace('+', '').strip()
    
    def get_session(self, phone: str) -> Dict[str, Any]:
        """Obtiene o crea una sesión"""
        clean_phone = self.clean_phone(phone)
        
        if clean_phone not in self.sessions:
            self.sessions[clean_phone] = {
                'messages': [],
                'context': '',
                'last_activity': datetime.now(),
                'user_name': 'Cliente',
                'total_messages': 0
            }
            
        # Limpiar sesiones viejas si hay muchas
        if len(self.sessions) > self.max_sessions:
            self._clean_old_sessions()
            
        return self.sessions[clean_phone]
    
    def update_session(self, phone: str, user_message: str, bot_response: str, user_name: str = None):
        """Actualiza la sesión"""
        session = self.get_session(phone)
        
        # Actualizar información
        session['messages'].append({
            'user': user_message,
            'bot': bot_response,
            'timestamp': datetime.now()
        })
        
        session['last_activity'] = datetime.now()
        session['total_messages'] += 1
        
        if user_name and user_name != 'Cliente':
            session['user_name'] = user_name
        
        # Mantener solo los últimos 5 intercambios
        if len(session['messages']) > 5:
            session['messages'] = session['messages'][-5:]
        
        # Crear contexto para el agente
        session['context'] = self._build_context(session['messages'])
    
    def _build_context(self, messages: list) -> str:
        """Construye contexto de conversación"""
        if not messages or len(messages) < 2:
            return ""
        
        # Tomar los últimos 2-3 intercambios
        recent = messages[-2:]
        context_parts = []
        
        for msg in recent:
            context_parts.append(f"Cliente: {msg['user']}")
            context_parts.append(f"Agente: {msg['bot'][:100]}...")  # Truncar respuestas largas
        
        return "\n".join(context_parts)
    
    def _clean_old_sessions(self):
        """Limpia sesiones inactivas"""
        cutoff_time = datetime.now()
        cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - 24)  # 24 horas atrás
        
        old_sessions = [
            phone for phone, session in self.sessions.items()
            if session['last_activity'] < cutoff_time
        ]
        
        for phone in old_sessions:
            del self.sessions[phone]
        
        logger.info(f"🧹 Limpiadas {len(old_sessions)} sesiones inactivas")

# Inicializar gestor de sesiones
session_manager = WhatsAppSessionManager()

# =====================================================
# SERVICIOS WHATSAPP
# =====================================================

class WhatsAppService:
    @staticmethod
    def send_message(to: str, message: str) -> bool:
        """Envía mensaje por WhatsApp"""
        if not twilio_client:
            logger.error("❌ Cliente de Twilio no disponible")
            return False
        
        try:
            # Asegurar formato correcto
            if not to.startswith('whatsapp:'):
                to = f'whatsapp:{to}'
            
            message_obj = twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=message,
                to=to
            )
            
            logger.info(f"✅ Mensaje enviado: {message_obj.sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {str(e)}")
            return False
    
    @staticmethod
    def validate_webhook(request: Request) -> bool:
        """Valida que el webhook venga de Twilio (opcional)"""
        # Implementar validación de signature de Twilio si es necesario
        return True

whatsapp_service = WhatsAppService()

# =====================================================
# PROCESADOR DE MENSAJES INTELIGENTE  
# =====================================================

class MessageProcessor:
    
    @staticmethod
    def detect_intent(message: str) -> str:
        """Detecta la intención básica del mensaje"""
        message_lower = message.lower().strip()
        
        # Comandos de sistema
        if message_lower in ['reiniciar', 'reset', 'nuevo', 'empezar', 'start']:
            return 'reset'
        
        if message_lower in ['ayuda', 'help', 'comandos', 'menu']:
            return 'help'
        
        # Saludos
        if any(word in message_lower for word in ['hola', 'hi', 'hello', 'buenas', 'buenos']):
            return 'greeting'
        
        # Búsqueda de propiedades
        if any(word in message_lower for word in ['casa', 'piso', 'apartamento', 'propiedad', 'inmueble', 'buscar', 'quiero']):
            return 'property_search'
        
        # Información de precios
        if any(word in message_lower for word in ['precio', 'cuesta', 'vale', 'coste', 'euros', 'cost']):
            return 'price_info'
        
        # Contacto
        if any(word in message_lower for word in ['contacto', 'llamar', 'teléfono', 'email', 'agente']):
            return 'contact'
        
        return 'general'
    
    @staticmethod
    def handle_system_commands(intent: str, phone: str, user_name: str) -> str:
        """Maneja comandos del sistema"""
        
        if intent == 'reset':
            # Limpiar sesión
            clean_phone = session_manager.clean_phone(phone)
            if clean_phone in session_manager.sessions:
                del session_manager.sessions[clean_phone]
            
            return f"🔄 ¡Hola de nuevo, {user_name}! He reiniciado nuestra conversación.\n\n🏠 Soy tu agente inmobiliario virtual. ¿En qué puedo ayudarte hoy?\n\n• Buscar propiedades\n• Información de precios\n• Consultas generales\n• Contacto con agentes"
        
        elif intent == 'help':
            return f"""🤖 **Comandos disponibles, {user_name}:**

**🏠 Sobre propiedades:**
• "Busco casa en Madrid"
• "¿Cuánto cuesta un piso?"
• "Propiedades cerca del centro"

**💬 Comandos:**
• `reiniciar` - Nueva conversación
• `ayuda` - Este menú
• `contacto` - Información de contacto

**✨ Simplemente escríbeme lo que necesites sobre inmuebles y te ayudo al instante."""
        
        return None
    
    @staticmethod
    def enhance_question_for_agent(message: str, context: str, user_name: str, intent: str) -> str:
        """Mejora la pregunta para tu agente con contexto"""
        
        # Prefijo según la intención
        intent_context = {
            'greeting': f"El cliente {user_name} me saluda",
            'property_search': f"El cliente {user_name} busca información sobre propiedades",
            'price_info': f"El cliente {user_name} quiere información de precios",
            'contact': f"El cliente {user_name} quiere información de contacto",
            'general': f"El cliente {user_name} hace una consulta general"
        }
        
        base_prompt = intent_context.get(intent, f"El cliente {user_name} pregunta")
        
        # Construir pregunta mejorada
        if context:
            enhanced_question = f"""
{base_prompt}:
"{message}"

Contexto de conversación previa:
{context}

Por favor, responde considerando el contexto previo y mantén un tono profesional pero cálido. Si es un saludo, sé breve pero amable.
"""
        else:
            enhanced_question = f'{base_prompt}: "{message}"\n\nResponde de manera profesional y amable.'
        
        return enhanced_question

message_processor = MessageProcessor()

# =====================================================
# ENDPOINTS PRINCIPALES
# =====================================================

@app.get("/")
async def health_check():
    """Status del servicio"""
    return {
        "status": "🟢 WhatsApp Bridge Activo",
        "service": "Agente Inmobiliario WhatsApp",
        "version": "2.0.0",
        "timestamp": datetime.now(),
        "twilio_configured": bool(twilio_client),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "total_sessions": len(session_manager.sessions)
    }

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    NumMedia: str = Form('0')
):
    """
    🎯 WEBHOOK PRINCIPAL - Recibe mensajes de WhatsApp
    """
    try:
        # Validación básica
        if not whatsapp_service.validate_webhook(request):
            logger.warning("❌ Webhook inválido")
            return Response(content="", media_type="text/xml", status_code=403)
        
        # Información del usuario
        user_name = ProfileName or "Cliente"
        logger.info(f"📨 Mensaje de {user_name} ({From}): {Body}")
        
        # Detectar intención
        intent = message_processor.detect_intent(Body)
        
        # Manejar comandos del sistema primero
        system_response = message_processor.handle_system_commands(intent, From, user_name)
        if system_response:
            whatsapp_service.send_message(From, system_response)
            session_manager.update_session(From, Body, system_response, user_name)
            return Response(content="", media_type="text/xml")
        
        # Obtener sesión y contexto
        session = session_manager.get_session(From)
        context = session['context']
        
        # Preparar pregunta mejorada para tu agente
        enhanced_question = message_processor.enhance_question_for_agent(
            Body, context, user_name, intent
        )
        
        # 🎯 CONECTAR CON TU AGENTE EXISTENTE
        logger.info("🤖 Procesando con agente inmobiliario...")
        
        try:
            # Usar tu función ejecutar_agente existente
            agent_response = ejecutar_agente(enhanced_question)
            
            # Verificar respuesta
            if not agent_response or agent_response.startswith("[ERROR]"):
                agent_response = f"😅 {user_name}, estoy teniendo dificultades técnicas momentáneas. ¿Podrías intentar reformular tu pregunta?"
            
            # Personalizar respuesta si no incluye el nombre
            if user_name != "Cliente" and not any(name.lower() in agent_response.lower() for name in [user_name.lower()]):
                # Solo agregar nombre si la respuesta no es muy corta
                if len(agent_response) > 50:
                    agent_response = f"{user_name}, {agent_response}"
            
        except Exception as agent_error:
            logger.error(f"❌ Error en agente: {agent_error}")
            agent_response = f"🔧 {user_name}, estoy teniendo problemas técnicos temporales. Intenta de nuevo en un momento, por favor."
        
        # Enviar respuesta por WhatsApp
        success = whatsapp_service.send_message(From, agent_response)
        
        if success:
            # Actualizar sesión
            session_manager.update_session(From, Body, agent_response, user_name)
            logger.info(f"✅ Conversación con {user_name} completada")
        else:
            logger.error(f"❌ Falló envío a {user_name}")
        
        # Respuesta TwiML vacía
        return Response(content="", media_type="text/xml")
        
    except Exception as e:
        logger.error(f"❌ Error crítico en webhook: {str(e)}")
        
        # Mensaje de error al usuario
        try:
            error_msg = f"😔 Disculpa, ocurrió un error inesperado. Por favor, intenta de nuevo."
            whatsapp_service.send_message(From, error_msg)
        except:
            pass
        
        return Response(content="", media_type="text/xml", status_code=500)

@app.get("/stats")
async def get_detailed_stats():
    """Estadísticas detalladas del servicio"""
    now = datetime.now()
    active_sessions = 0
    total_messages = 0
    
    for session in session_manager.sessions.values():
        total_messages += session['total_messages']
        # Sesión activa si tuvo actividad en las últimas 2 horas
        if (now - session['last_activity']).seconds < 7200:
            active_sessions += 1
    
    return {
        "timestamp": now,
        "total_sessions": len(session_manager.sessions),
        "active_sessions_2h": active_sessions,
        "total_messages_processed": total_messages,
        "twilio_status": "✅ Conectado" if twilio_client else "❌ No configurado",
        "agent_status": "✅ Disponible",  # Tu agente siempre está disponible
        "memory_usage": f"{len(session_manager.sessions)}/{session_manager.max_sessions} sesiones"
    }

@app.post("/test-message")
async def send_test_message(phone: str, message: str):
    """Endpoint para enviar mensajes de prueba"""
    if not phone.startswith('whatsapp:'):
        phone = f'whatsapp:{phone}'
    
    success = whatsapp_service.send_message(phone, message)
    
    return {
        "success": success,
        "phone": phone,
        "message": message,
        "timestamp": datetime.now()
    }

# =====================================================
# INICIALIZACIÓN DEL AGENTE
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Inicializa servicios al arrancar"""
    logger.info("🚀 Iniciando WhatsApp Bridge...")
    
    # Verificar configuración
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY no configurada")
    else:
        logger.info("✅ OpenAI API Key encontrada")
    
    if not twilio_client:
        logger.warning("⚠️ Twilio no configurado - solo modo desarrollo")
    else:
        logger.info("✅ Twilio configurado correctamente")
    
    # Inicializar tu agente
    try:
        logger.info("🧠 Inicializando agente inmobiliario...")
        inicializar_agente()
        logger.info("✅ Agente inmobiliario listo")
    except Exception as e:
        logger.error(f"❌ Error inicializando agente: {e}")
    
    logger.info("🎉 WhatsApp Bridge listo para recibir mensajes")
    logger.info("📱 Webhook URL: /webhook/whatsapp")

# =====================================================
# EJECUCIÓN
# =====================================================

if __name__ == "__main__":
    print("🏠📱 Iniciando WhatsApp Bridge para Agente Inmobiliario")
    print("=" * 60)
    print("📋 Configuración:")
    print(f"   • OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"   • Twilio: {'✅' if twilio_client else '❌'}")
    print()
    print("🔗 URLs importantes:")
    print("   • Health: http://localhost:8001/")
    print("   • Stats: http://localhost:8001/stats")  
    print("   • Webhook: http://localhost:8001/webhook/whatsapp")
    print()
    print("📱 Para conectar con WhatsApp:")
    print("   1. Configura webhook en Twilio Console")
    print("   2. URL: https://tu-dominio.com/webhook/whatsapp")
    print("=" * 60)
    
    uvicorn.run(
        "whatsapp_server:app",  # Cambiar por el nombre de este archivo
        host="0.0.0.0",
        port=8001,  # Puerto diferente a tu main.py (8080)
        reload=True,
        log_level="info"
    )

# main.py - Con puerto alternativo

import os
import sys
from fastapi import FastAPI, Query, HTTPException
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
    "https://www.tenerifemy.com",
    "https://www.terramagna.net/inmuebles"
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:8080",  # Puerto alternativo agregado
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080"   # Puerto alternativo agregado
]

# ⚠️ Variables globales para el agente
cerebro_mod = None
agente_inicializado = False
error_inicializacion = None

def cargar_agente_si_es_posible():
    """Carga el módulo cerebro con imports seguros."""
    global cerebro_mod, agente_inicializado, error_inicializacion
    
    if cerebro_mod and agente_inicializado:
        return cerebro_mod
    
    try:
        # Verificar si cerebro.py existe
        if not os.path.exists('cerebro.py'):
            error_inicializacion = "No se encuentra el archivo cerebro.py"
            print(f"[ERROR] {error_inicializacion}")
            return None
        
        # Importar cerebro
        import cerebro as cerebro_mod
        print("✅ Módulo cerebro importado correctamente.")
        
        # Inicializar el agente
        resultado = cerebro_mod.inicializar_agente()
        
        if resultado is not None:
            agente_inicializado = True
            error_inicializacion = None
            print("✅ Agente cargado e inicializado correctamente.")
            return cerebro_mod
        else:
            error_inicializacion = "El agente no se inicializó correctamente"
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

# 🔄 Ciclo de vida de la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicación...")
    agente = cargar_agente_si_es_posible()
    
    if agente and agente_inicializado:
        print("✅ Aplicación iniciada correctamente con agente.")
    else:
        print(f"⚠️ Aplicación iniciada sin agente. Error: {error_inicializacion}")
    
    yield
    
    # Shutdown
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
    status = "funcionando" if (cerebro_mod and agente_inicializado) else "sin agente"
    return {
        "mensaje": f"API Inmobiliaria IA {status}.",
        "agente_disponible": bool(cerebro_mod and agente_inicializado),
        "error_inicializacion": error_inicializacion
    }

# 🤖 Endpoint GET para preguntas
@app.get("/preguntar")
async def preguntar(pregunta: str = Query(..., description="Pregunta del usuario")):
    # Intentar cargar agente si no está disponible
    agente = cargar_agente_si_es_posible()
    
    if not agente or not agente_inicializado:
        raise HTTPException(
            status_code=503,
            detail=f"El agente no está disponible. Error: {error_inicializacion or 'Desconocido'}"
        )
    
    if not pregunta.strip():
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía."
        )
    
    try:
        # Usar directamente la función ejecutar_agente del módulo
        respuesta = agente.ejecutar_agente(pregunta)
        return {"respuesta": respuesta}
        
    except Exception as error:
        print(f"[ERROR] Fallo al procesar pregunta: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando la solicitud: {str(error)}"
        )

# 💬 Endpoint POST para chatbot
class PreguntaModel(BaseModel):
    mensaje: str
    
    class Config:
        str_strip_whitespace = True

@app.post("/chat")
async def chat(pregunta: PreguntaModel):
    # Intentar cargar agente si no está disponible
    agente = cargar_agente_si_es_posible()
    
    if not agente or not agente_inicializado:
        raise HTTPException(
            status_code=503,
            detail=f"El agente no está disponible. Error: {error_inicializacion or 'Desconocido'}"
        )
    
    if not pregunta.mensaje.strip():
        raise HTTPException(
            status_code=400,
            detail="El mensaje no puede estar vacío."
        )
    
    try:
        # Usar directamente la función ejecutar_agente del módulo
        respuesta = agente.ejecutar_agente(pregunta.mensaje)
        return {"respuesta": respuesta}
        
    except Exception as error:
        print(f"[ERROR] Fallo en /chat: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el mensaje: {str(error)}"
        )

# 🔧 Endpoint de estado para debugging
@app.get("/status")
async def status():
    return {
        "agente_modulo_cargado": bool(cerebro_mod),
        "agente_inicializado": agente_inicializado,
        "error_inicializacion": error_inicializacion,
        "openai_key_configurada": bool(os.getenv("OPENAI_API_KEY")),
        "directorio_conocimiento_existe": os.path.exists("conocimiento")
    }

# 🧪 Para pruebas en desarrollo
if __name__ == "__main__":
    print("🧪 Modo de prueba...")
    
    # Verificar configuración básica
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY no está configurada")
    else:
        print("✅ OPENAI_API_KEY encontrada")
    
    # Probar agente
    agente = cargar_agente_si_es_posible()
    if agente and agente_inicializado:
        respuesta = agente.ejecutar_agente("Hola, ¿cómo estás?")
        print(f"✅ Respuesta de prueba: {respuesta}")
    else:
        print(f"❌ No se pudo cargar el agente: {error_inicializacion}")
    
    # Ejecutar servidor en puerto alternativo
    try:
        import uvicorn
        print("🚀 Iniciando servidor en http://0.0.0.0:8080")
        uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")