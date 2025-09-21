# cerebro.py - VERSIÓN FINAL CON DETECCIÓN DE IDIOMA Y RESUMEN

import os
import re
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variable global del agente
agente_executor = None

# Sistema de conversación con estados MEJORADO
estados_conversacion = {}

# NUEVO: Sistema de almacenamiento de consultas para Vanessa
consultas_vanessa = {}

# NUEVO: Configuración del número de la inmobiliaria
NUMERO_INMOBILIARIA = os.getenv("NUMERO_INMOBILIARIA", "")  # Configurar en .env

def limpiar_texto_whatsapp(texto: str) -> str:
    """Limpia y normaliza texto de WhatsApp."""
    if not texto:
        return ""
    
    # Remover emojis y caracteres especiales, mantener texto básico
    texto_limpio = re.sub(r'[^\w\s.?!¿¡áéíóúñüÁÉÍÓÚÑÜ,:]', ' ', texto)
    # Normalizar espacios múltiples
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    return texto_limpio[:500]  # Limitar longitud

def detectar_idioma_mejorado(texto: str, llm, numero_whatsapp: str = None) -> str:
    """Detecta el idioma del texto usando el modelo LLM con memoria de conversación."""
    try:
        # NUEVO: Verificar si hay un idioma previamente detectado en la conversación
        if numero_whatsapp and numero_whatsapp in estados_conversacion:
            idioma_previo = estados_conversacion[numero_whatsapp].get("idioma_detectado")
            
            # Si el cliente cambia de idioma en medio de la conversación
            if idioma_previo:
                # Detectar cambio de idioma comparando con el anterior
                if tiene_cambio_de_idioma(texto, idioma_previo):
                    nuevo_idioma = detectar_idioma_actual(texto, llm)
                    if nuevo_idioma != idioma_previo:
                        logger.info(f"🔄 CAMBIO DE IDIOMA detectado: {idioma_previo} → {nuevo_idioma}")
                        # Actualizar el idioma en el estado
                        estados_conversacion[numero_whatsapp]["idioma_detectado"] = nuevo_idioma
                        estados_conversacion[numero_whatsapp]["cambio_idioma"] = True
                        return nuevo_idioma
                    return idioma_previo
                else:
                    # Mantener el idioma actual si no hay cambio detectado
                    return idioma_previo
        
        # Primera detección o sin número
        return detectar_idioma_actual(texto, llm)
        
    except Exception as e:
        logger.warning(f"Error detectando idioma: {e}")
        return "español"

def tiene_cambio_de_idioma(texto: str, idioma_actual: str) -> bool:
    """Detecta si el texto indica un cambio de idioma respecto al actual."""
    texto_lower = texto.lower()
    
    # Palabras indicadoras por idioma
    indicadores_espanol = ['hola', 'gracias', 'por favor', 'precio', 'casa', 'piso', 'alquiler', 'venta', 'sí', 'no', 'cómo', 'qué', 'cuánto']
    indicadores_ingles = ['hello', 'hi', 'thanks', 'thank you', 'please', 'price', 'house', 'property', 'rent', 'sale', 'yes', 'no', 'how', 'what', 'how much']
    indicadores_aleman = ['hallo', 'danke', 'bitte', 'preis', 'haus', 'wohnung', 'miete', 'verkauf', 'ja', 'nein', 'wie', 'was', 'wie viel']
    
    # Contar indicadores por idioma
    score_es = sum(1 for palabra in indicadores_espanol if palabra in texto_lower)
    score_en = sum(1 for palabra in indicadores_ingles if palabra in texto_lower)
    score_de = sum(1 for palabra in indicadores_aleman if palabra in texto_lower)
    
    # Determinar idioma predominante
    if score_es > score_en and score_es > score_de:
        nuevo_idioma = "español"
    elif score_en > score_de:
        nuevo_idioma = "inglés"
    elif score_de > 0:
        nuevo_idioma = "alemán"
    else:
        return False  # No hay suficientes indicadores
    
    # Verificar si es diferente al actual
    return nuevo_idioma != idioma_actual

def detectar_idioma_actual(texto: str, llm) -> str:
    """Detecta el idioma actual del texto."""
    try:
        texto_lower = texto.lower()
        
        # Palabras clave por idioma
        palabras_espanol = ['hola', 'gracias', 'por favor', 'precio', 'casa', 'piso', 'alquiler', 'venta']
        palabras_ingles = ['hello', 'thanks', 'please', 'price', 'house', 'property', 'rent', 'sale']
        palabras_aleman = ['hallo', 'danke', 'bitte', 'preis', 'haus', 'wohnung', 'miete', 'verkauf']
        
        # Contar coincidencias
        score_es = sum(1 for palabra in palabras_espanol if palabra in texto_lower)
        score_en = sum(1 for palabra in palabras_ingles if palabra in texto_lower)
        score_de = sum(1 for palabra in palabras_aleman if palabra in texto_lower)
        
        if score_es >= score_en and score_es >= score_de:
            return "español"
        elif score_en >= score_de:
            return "inglés"
        elif score_de > 0:
            return "alemán"
        
        # Si no es claro, usar LLM
        if len(texto) > 50:
            consulta = (
                "Detecta en qué idioma está escrito el siguiente texto y "
                "responde con una sola palabra: "
                "español, inglés o alemán.\n"
                f"Texto: {texto[:200]}"
            )
            response = llm.invoke(consulta)
            idioma = response.content.strip().lower().replace('.', '')
            
            if idioma in ['español', 'inglés', 'alemán', 'spanish', 'english', 'german']:
                return idioma
        
        return "español"  # Por defecto
        
    except Exception as e:
        logger.warning(f"Error detectando idioma actual: {e}")
        return "español"

# NUEVO: Función para detectar comando de resumen
def es_comando_resumen(texto: str, numero_whatsapp: str) -> bool:
    """Detecta si el mensaje es el comando 'resumen' desde el número de la inmobiliaria."""
    if not NUMERO_INMOBILIARIA:
        return False
    
    # Verificar si es desde el número de la inmobiliaria
    numero_limpio = numero_whatsapp.replace('+', '').replace(' ', '').replace('-', '')
    numero_inmobiliaria_limpio = NUMERO_INMOBILIARIA.replace('+', '').replace(' ', '').replace('-', '')
    
    if numero_limpio != numero_inmobiliaria_limpio:
        return False
    
    # Verificar si el mensaje es exactamente "resumen"
    return texto.strip().lower() == "resumen"

# NUEVO: Función para generar resumen de consultas
def generar_resumen_consultas() -> str:
    """Genera un resumen de todas las consultas pendientes para Vanessa."""
    if not consultas_vanessa:
        return "📋 No hay consultas pendientes para Vanessa."
    
    resumen = "📋 *RESUMEN DE CONSULTAS PARA VANESSA*\n\n"
    
    for i, (numero, datos) in enumerate(consultas_vanessa.items(), 1):
        resumen += f"*{i}. Cliente:*\n"
        resumen += f"📞 Teléfono: {numero}\n"
        resumen += f"👤 Nombre: {datos.get('nombre', 'No proporcionado')}\n"
        resumen += f"📅 Fecha: {datos.get('fecha', 'N/A')}\n"
        resumen += f"💬 Consulta: {datos.get('mensaje', 'N/A')}\n"
        resumen += f"🌐 Idioma: {datos.get('idioma', 'No detectado')}\n"
        resumen += "─" * 30 + "\n\n"
    
    resumen += f"📊 *Total de consultas: {len(consultas_vanessa)}*"
    return resumen

# NUEVO: Función para guardar consulta para Vanessa
def guardar_consulta_vanessa(numero_whatsapp: str, mensaje: str, idioma: str, nombre: str = None):
    """Guarda una consulta que debe ser atendida por Vanessa."""
    consultas_vanessa[numero_whatsapp] = {
        'mensaje': mensaje,
        'idioma': idioma,
        'nombre': nombre or "No proporcionado",
        'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'timestamp': datetime.now()
    }
    logger.info(f"💾 Consulta guardada para Vanessa - Cliente: {numero_whatsapp[-4:]}****")

def detectar_intencion_inicial(texto: str) -> str:
    """Detecta si el mensaje es un saludo inicial o ya indica intención específica."""
    texto_lower = texto.lower().strip()
    
    # Palabras que indican saludo inicial simple
    saludos_simples = ['hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches', 'hey', 'buenas']
    
    # Palabras que indican consulta específica sobre propiedades DISPONIBLES
    inmobiliario_especifico = [
        'tiene propiedades', 'tienen propiedades', 'propiedades disponibles',
        'casas disponibles', 'pisos disponibles', 'apartamentos disponibles',
        'propiedades en alquiler', 'propiedades en venta', 'busco casa', 'busco piso',
        'necesito casa', 'necesito piso', 'quiero alquilar', 'quiero comprar'
    ]
    
    # Palabras que indican ASESORAMIENTO o consulta personal
    asesoramiento = [
        'aconsejar', 'aconseje', 'asesoramiento', 'asesorar', 'ayuda para invertir',
        'consejos', 'consulta para invertir', 'quiero invertir', 'cómo invertir',
        'donde invertir', 'orientación', 'guía', 'recomendar zona'
    ]
    
    # Palabras que indican otros temas específicos
    otros_temas = [
        'consulta legal', 'información legal', 'servicio legal', 'ayuda legal', 
        'contacto', 'vanessa', 'llamar', 'llame', 'teléfono', 'telefono', 
        'call', 'phone', 'hablar con vanessa'
    ]
    
    # Si es exactamente un saludo simple sin más contexto
    if texto_lower in saludos_simples or (any(saludo in texto_lower for saludo in saludos_simples) and len(texto.split()) <= 2):
        return "saludo_inicial"
    
    # PRIORIDAD: Detectar asesoramiento personal primero
    if any(palabra in texto_lower for palabra in asesoramiento):
        return "otro_tema"
    
    # Detectar consulta específica sobre propiedades disponibles
    if any(frase in texto_lower for frase in inmobiliario_especifico):
        return "inmobiliario_directo"
    
    # Detectar otros temas específicamente
    if any(tema in texto_lower for tema in otros_temas):
        return "otro_tema"
    
    # Si el mensaje es más largo o tiene contenido específico, analizar contexto
    if len(texto.split()) > 3:
        # Si menciona inversión sin preguntar por propiedades específicas
        if 'invertir' in texto_lower or 'inversión' in texto_lower:
            return "otro_tema"
        else:
            return "otro_tema"
    
    return "saludo_inicial"

def detectar_respuesta_categoria(texto: str) -> str:
    """Detecta si la respuesta es sobre alquileres/ventas u otro tema."""
    texto_lower = texto.lower().strip()
    
    # Palabras que indican consulta específica sobre propiedades DISPONIBLES
    palabras_inmobiliario_especifico = [
        'tiene propiedades', 'tienen propiedades', 'qué propiedades tienen', 'propiedades disponibles',
        'casas disponibles', 'pisos disponibles', 'apartamentos disponibles',
        'propiedades en alquiler', 'propiedades en venta', 'casas en alquiler', 'casas en venta',
        'pisos en alquiler', 'pisos en venta', 'apartamentos en alquiler', 'apartamentos en venta',
        'mostrar propiedades', 'ver propiedades', 'busco casa', 'busco piso', 'busco apartamento',
        'necesito casa', 'necesito piso', 'necesito apartamento'
    ]
    
    # Palabras que indican ASESORAMIENTO o consulta personal (otro tema)
    palabras_asesoria_personal = [
        'aconsejar', 'aconseje', 'asesoramiento', 'asesorar', 'ayuda para invertir',
        'consejos', 'consulta para invertir', 'quiero invertir', 'cómo invertir',
        'donde invertir', 'orientación', 'guía', 'recomendar zona', 'recomendar área',
        'mejor zona para', 'dónde es mejor', 'advice', 'consult', 'recommend'
    ]
    
    # Palabras que indican otro tema claramente (incluye solicitudes de llamada)
    palabras_otro_tema = [
        'otro tema', 'otra cosa', 'diferente', 'consulta legal', 'información legal', 
        'servicio legal', 'no', 'nada', 'otro asunto', 'legal', 'jurídico',
        'llamar', 'llame', 'teléfono', 'telefono', 'call', 'phone', 'contacto',
        'hablar con vanessa', 'contactar vanessa', 'hablar', 'conversar'
    ]
    
    # Frases que indican seguimiento o más preguntas
    palabras_seguimiento = [
        'algo más', 'otra pregunta', 'más información', 'seguir', 'continuar',
        'gracias', 'perfecto', 'ok', 'vale', 'bien'
    ]
    
    # PRIORIDAD: Detectar primero si es asesoramiento personal
    if any(palabra in texto_lower for palabra in palabras_asesoria_personal):
        return "otro_tema"
    
    # Detectar si pregunta específicamente por propiedades disponibles
    elif any(frase in texto_lower for frase in palabras_inmobiliario_especifico):
        return "inmobiliario"
    
    # Detectar otros temas
    elif any(tema in texto_lower for tema in palabras_otro_tema):
        return "otro_tema"
    
    # Detectar seguimiento
    elif any(palabra in texto_lower for palabra in palabras_seguimiento):
        return "seguimiento"
    
    # Si menciona propiedades pero en contexto de asesoramiento
    elif 'invertir' in texto_lower or 'inversión' in texto_lower:
        return "otro_tema"
    
    else:
        # Si es una pregunta específica y directa sobre propiedades
        palabras_inmobiliario_general = [
            'alquiler', 'alquilar', 'venta', 'vender', 'comprar', 'casa', 'piso', 
            'apartamento', 'propiedad', 'inmueble', 'vivienda', 'rent', 'rental',
            'sale', 'buy', 'house', 'apartment', 'property', 'alquileres', 'ventas'
        ]
        
        if any(palabra in texto_lower for palabra in palabras_inmobiliario_general):
            return "inmobiliario"
        else:
            return "otro_tema"

def obtener_estado_conversacion(numero_whatsapp: str) -> dict:
    """Obtiene el estado actual de la conversación."""
    if numero_whatsapp not in estados_conversacion:
        estados_conversacion[numero_whatsapp] = {
            "estado": "inicial",
            "ultima_interaccion": datetime.now(),
            "contador_mensajes": 0,
            "idioma_detectado": None,
            "bandera_mostrada": False,
            "cambio_idioma": False  # NUEVO: para trackear cambios de idioma
        }
    
    return estados_conversacion[numero_whatsapp]

def actualizar_estado_conversacion(numero_whatsapp: str, nuevo_estado: str):
    """Actualiza el estado de la conversación."""
    if numero_whatsapp not in estados_conversacion:
        estados_conversacion[numero_whatsapp] = {}
    
    estados_conversacion[numero_whatsapp].update({
        "estado": nuevo_estado,
        "ultima_interaccion": datetime.now(),
        "contador_mensajes": estados_conversacion[numero_whatsapp].get("contador_mensajes", 0) + 1
    })

def generar_saludo_inicial(idioma: str) -> str:
    """Genera el saludo inicial según el idioma - MENSAJE EXACTO REQUERIDO."""
    if idioma in ["inglés", "english"]:
        return ("🏠 Hello! I'm Vanessa's virtual assistant from TerraMagna Real State Boutique. "
                "Are you looking to inquire about rental or sale properties? Or is it about another topic?")
    elif idioma in ["alemán", "german", "deutsch"]:
        return ("🏠 Hallo! Ich bin Vanessas virtueller Assistent von TerraMagna Real State Boutique. "
                "Möchten Sie sich über Miet- oder Verkaufsimmobilien informieren? Oder geht es um ein anderes Thema?")
    else:  # español
        return ("🏠 Hola, soy el asistente virtual de Vanessa de TerraMagna Real State Boutique. "
                "¿Quieres consultar sobre propiedades en alquiler o en venta? ¿O es por otro tema?")

def generar_respuesta_otro_tema(idioma: str) -> str:
    """Genera respuesta para otros temas."""
    if idioma in ["inglés", "english"]:
        return ("Thank you for your inquiry. Please let us know what you need and "
                "Vanessa will contact you shortly to assist you personally.")
    elif idioma in ["alemán", "german", "deutsch"]:
        return ("Vielen Dank für Ihre Anfrage. Bitte teilen Sie uns mit, was Sie benötigen, "
                "und Vanessa wird sich in Kürze mit Ihnen in Verbindung setzen, um Ihnen persönlich zu helfen.")
    else:  # español
        return ("Gracias por tu consulta. Por favor, expónnos qué necesitas y "
                "Vanessa se pondrá en contacto contigo en breve para ayudarte personalmente.")

# NUEVO: Función para generar mensaje de cambio de idioma
def generar_mensaje_cambio_idioma(idioma_nuevo: str) -> str:
    """Genera un mensaje confirmando el cambio de idioma."""
    if idioma_nuevo in ["inglés", "english"]:
        return "🔄 I've detected you switched to English. I'll continue in English from now on."
    elif idioma_nuevo in ["alemán", "german", "deutsch"]:
        return "🔄 Ich habe bemerkt, dass Sie auf Deutsch gewechselt haben. Ich werde ab jetzt auf Deutsch fortfahren."
    else:  # español
        return "🔄 He detectado que has cambiado al español. Continuaré en español a partir de ahora."

def detectar_datos_contacto(texto: str) -> bool:
    """Detecta si el cliente proporciona nombre y teléfono."""
    texto_lower = texto.lower().strip()
    
    # Patrones que indican datos de contacto
    tiene_nombre = any(palabra in texto_lower for palabra in [
        'mi nombre es', 'me llamo', 'soy', 'my name is', 'i am', 'ich bin', 'ich heiße',
        'nombre es', 'nombre:', 'mi nombre'
    ])
    
    tiene_telefono = any(palabra in texto_lower for palabra in [
        'mi teléfono', 'mi telefono', 'mi número', 'mi numero', 'my phone', 'my number',
        'mein telefon', 'meine nummer', 'tfno', 'telefono', 'teléfono', 'numero', 'número'
    ]) or bool(re.search(r'\d{3}.*\d{3}.*\d{3}', texto))  # Detecta patrones de teléfono
    
    # Si tiene ambos o al menos uno muy claro
    if tiene_nombre and tiene_telefono:
        return True
    
    # Detectar si hay números de teléfono largos en el texto (6+ dígitos consecutivos)
    if re.search(r'\d{6,}', texto):
        return True
    
    # Detectar formato español común
    if re.search(r'6\d{8}|9\d{8}|[+]34\s*6\d{8}|[+]34\s*9\d{8}', texto):
        return True
    
    # Detectar patrón: "nombre + número" en el mismo mensaje
    palabras = texto.split()
    tiene_numero_largo = any(re.search(r'\d{6,}', palabra) for palabra in palabras)
    tiene_palabra_nombre = any(palabra in ['es', 'soy', 'me', 'llamo', 'nombre'] for palabra in palabras[:3])
    
    if tiene_numero_largo and (tiene_palabra_nombre or len(palabras) <= 6):
        return True
    
    return False

# NUEVO: Función para extraer nombre del texto
def extraer_nombre_del_texto(texto: str) -> str:
    """Extrae el nombre del cliente del texto."""
    texto_lower = texto.lower()
    
    # Patrones comunes para extraer nombres
    patrones = [
        r'mi nombre es (\w+)',
        r'me llamo (\w+)',
        r'soy (\w+)',
        r'my name is (\w+)',
        r'i am (\w+)',
        r'ich bin (\w+)',
        r'ich heiße (\w+)'
    ]
    
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            return match.group(1).capitalize()
    
    # Si no encuentra patrón específico, intentar extraer la primera palabra que podría ser un nombre
    palabras = texto.split()
    for palabra in palabras:
        if len(palabra) > 2 and palabra.isalpha() and palabra[0].isupper():
            return palabra
    
    return "No proporcionado"

def generar_confirmacion_llamada(idioma: str) -> str:
    """Genera confirmación de que Vanessa llamará."""
    if idioma in ["inglés", "english"]:
        return ("Perfect! I will let Vanessa know that you want her to call you. "
                "Please provide your name and phone number so she can contact you as soon as possible.")
    elif idioma in ["alemán", "german", "deutsch"]:
        return ("Perfekt! Ich werde Vanessa mitteilen, dass Sie möchten, dass sie Sie anruft. "
                "Bitte geben Sie Ihren Namen und Ihre Telefonnummer an, damit sie Sie so schnell wie möglich kontaktieren kann.")
    else:  # español
        return ("¡Perfecto! Le diré a Vanessa que quieres que te llame. "
                "Por favor, proporciona tu nombre y número de teléfono para que pueda contactarte lo antes posible.")

def detectar_insistencia_contacto_personal(texto: str) -> bool:
    """Detecta si el cliente insiste en hablar con Vanessa después de haber recibido respuesta de otro tema."""
    texto_lower = texto.lower().strip()
    
    frases_insistencia = [
        'nada le puedes decir a vanessa que me llame',
        'le puedes decir a vanessa que me llame',
        'dile a vanessa que me llame',
        'que me llame vanessa',
        'vanessa que me llame',
        'solo quiero que me llame',
        'necesito que me llame',
        'cuando me va a llamar',
        'cuándo me llama'
    ]
    
    return any(frase in texto_lower for frase in frases_insistencia)

def generar_pregunta_seguimiento(idioma: str) -> str:
    """Genera pregunta de seguimiento después de una respuesta."""
    if idioma in ["inglés", "english"]:
        return "Is there anything else I can help you with? Would you like to know about our rental or sale properties?"
    elif idioma in ["alemán", "german", "deutsch"]:
        return "Gibt es noch etwas, womit ich Ihnen helfen kann? Möchten Sie mehr über unsere Miet- oder Verkaufsimmobilien erfahren?"
    else:  # español
        return "¿Hay algo más en lo que pueda ayudarte? ¿Te gustaría conocer nuestras propiedades en alquiler o venta?"

def generar_pregunta_necesita_algo_mas(idioma: str) -> str:
    """Pregunta si necesita algo más después de que explique sus necesidades."""
    if idioma in ["inglés", "english"]:
        return "Is there anything else I can help you with today?"
    elif idioma in ["alemán", "german", "deutsch"]:
        return "Gibt es noch etwas anderes, womit ich Ihnen heute helfen kann?"
    else:  # español
        return "¿Hay algo más en lo que pueda ayudarte hoy?"

def generar_oferta_propiedades_final(idioma: str) -> str:
    """Ofrece propiedades antes de la despedida final."""
    if idioma in ["inglés", "english"]:
        return "Before we say goodbye, would you like to know about our rental and sale properties?"
    elif idioma in ["alemán", "german", "deutsch"]:
        return "Bevor wir uns verabschieden, möchten Sie mehr über unsere Miet- und Verkaufsimmobilien erfahren?"
    else:  # español
        return "Antes de despedirnos, ¿te gustaría conocer nuestras propiedades en alquiler o venta?"

def generar_despedida_final(idioma: str) -> str:
    """Genera despedida final cuando el cliente no necesita más ayuda."""
    if idioma in ["inglés", "english"]:
        return ("Thank you for contacting TerraMagna Real State Boutique. "
                "We are always at your disposal for any questions or needs you may have. "
                "Have a wonderful day!")
    elif idioma in ["alemán", "german", "deutsch"]:
        return ("Vielen Dank, dass Sie TerraMagna Real State Boutique kontaktiert haben. "
                "Wir stehen Ihnen jederzeit für Fragen oder Bedürfnisse zur Verfügung. "
                "Haben Sie einen wunderschönen Tag!")
    else:  # español
        return ("Gracias por contactar con TerraMagna Real State Boutique. "
                "Estamos siempre a tu disposición para cualquier consulta o necesidad que puedas tener. "
                "¡Que tengas un día maravilloso!")

def detectar_respuesta_negativa(texto: str) -> bool:
    """Detecta si el cliente dice que no necesita más ayuda."""
    texto_lower = texto.lower().strip()
    
    respuestas_negativas = [
        'no', 'nada', 'nothing', 'nichts', 'no thanks', 'no gracias', 
        'nein danke', 'that\'s all', 'eso es todo', 'das ist alles',
        'no necesito nada más', 'no necesito más', 'estoy bien',
        'i\'m good', 'i\'m fine', 'that\'s it', 'ya está'
    ]
    
    return any(resp in texto_lower for resp in respuestas_negativas)

def detectar_finalizacion_conversacion(texto: str) -> bool:
    """Detecta si el cliente quiere finalizar la conversación."""
    texto_lower = texto.lower().strip()
    
    palabras_finalizacion = [
        'gracias', 'thank you', 'thanks', 'danke', 'perfecto', 'perfect',
        'ok', 'vale', 'bien', 'good', 'gut', 'nada más', 'nothing else',
        'nichts mehr', 'eso es todo', "that's all", 'das ist alles'
    ]
    
    # Si es una respuesta muy corta con palabras de agradecimiento
    if len(texto.split()) <= 3 and any(palabra in texto_lower for palabra in palabras_finalizacion):
        return True
    
    return False

def aplicar_bandera_si_necesario(respuesta: str, idioma: str, numero_whatsapp: str) -> str:
    """Aplica bandera solo si es el primer mensaje de la conversación."""
    estado = obtener_estado_conversacion(numero_whatsapp)
    
    if not estado.get("bandera_mostrada", False):
        # Primera vez, mostrar bandera
        estados_conversacion[numero_whatsapp]["bandera_mostrada"] = True
        estados_conversacion[numero_whatsapp]["idioma_detectado"] = idioma
        return agregar_bandera(respuesta, idioma)
    else:
        # Ya se mostró la bandera, no agregar más
        return respuesta

def agregar_bandera(respuesta: str, idioma: str) -> str:
    """Agrega bandera según el idioma detectado."""
    banderas = {
        "inglés": "🇬🇧", "english": "🇬🇧",
        "alemán": "🇩🇪", "german": "🇩🇪", "deutsch": "🇩🇪",
        "español": "🇪🇸", "spanish": "🇪🇸"
    }
    
    bandera = banderas.get(idioma.lower(), '🇪🇸')
    return f"{bandera} {respuesta}".strip()

def formatear_respuesta_por_plataforma(respuesta: str, plataforma: str = "web") -> str:
    """Formateo optimizado por plataforma."""
    if not respuesta:
        return ""
    
    if plataforma.lower() == "whatsapp":
        MAX_CHARS = 3900  # Margen de seguridad para WhatsApp
        
        if len(respuesta) <= MAX_CHARS:
            return respuesta
        
        # División inteligente por párrafos
        parrafos = respuesta.split('\n\n')
        respuesta_corta = parrafos[0] if parrafos else respuesta[:MAX_CHARS//2]
        
        # Agregar párrafos adicionales si caben
        for parrafo in parrafos[1:]:
            nueva_longitud = len(respuesta_corta + '\n\n' + parrafo)
            if nueva_longitud <= MAX_CHARS - 100:
                respuesta_corta += '\n\n' + parrafo
            else:
                respuesta_corta += '\n\n📱 *Respuesta completa disponible por teléfono*'
                break
        
        return respuesta_corta
    else:
        # Web: respuesta completa sin limitaciones
        return respuesta

def crear_prompt_inmobiliario_optimizado(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea prompt optimizado para consultas inmobiliarias."""
    
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    if idioma in ["inglés", "english"]:
        return (
            f"You are Vanessa's professional virtual assistant from TerraMagna Real State Boutique. "
            f"Respond in English via {formato_base}. "
            
            f"CRITICAL INSTRUCTIONS FOR SALES INQUIRIES: "
            f"When asked about properties for SALE/VENTA, follow this EXACT format: "
            f"1. Start with: 'We currently have X properties for sale:' "
            f"2. List properties like: '- 1 Villa 4 bedrooms in Costa Adeje Golf area' "
            f"3. Do NOT include prices or URLs in the initial list "
            f"4. End with: 'Which type of property interests you or would you like details about any specific one?' "
            f"5. Only provide complete details (price, URL) when they ask for a specific property "
            
            f"Use ONLY information from your knowledge base files. "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller virtueller Assistent von TerraMagna Real State Boutique. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            
            f"KRITISCHE ANWEISUNGEN FÜR VERKAUFSANFRAGEN: "
            f"Bei Fragen zu VERKAUFSIMMOBILIEN folgen Sie diesem EXAKTEN Format: "
            f"1. Beginnen Sie mit: 'Wir haben derzeit X Immobilien zum Verkauf:' "
            f"2. Listen Sie auf wie: '- 1 Villa 4 Schlafzimmer in Costa Adeje Golf Bereich' "
            f"3. Keine Preise oder URLs in der ersten Liste "
            f"4. Enden Sie mit: 'Welche Art von Immobilie interessiert Sie oder möchten Sie Details zu einer bestimmten?' "
            f"5. Vollständige Details (Preis, URL) nur wenn sie nach einer bestimmten Immobilie fragen "
            
            f"Verwenden Sie NUR Informationen aus Ihren Wissensdateien. "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente virtual profesional de Vanessa de TerraMagna Real State Boutique. "
            f"Responde en español via {formato_base}. "
            
            f"INSTRUCCIONES CRÍTICAS PARA CONSULTAS DE VENTAS: "
            f"Cuando pregunten por propiedades en VENTA, sigue este formato EXACTO: "
            f"1. Empieza con: 'Tenemos actualmente X propiedades en venta:' "
            f"2. Lista como: '- 1 Villa 4 habitaciones en zona Costa Adeje Golf' "
            f"3. NO incluir precios ni URLs en la lista inicial "
            f"4. Termina con: '¿Qué tipo de propiedad te interesa o te gustaría información detallada de alguna en concreto?' "
            f"5. Solo dar detalles completos (precio, URL) cuando pregunten por una propiedad específica "
            
            f"Usa ÚNICAMENTE información de tus archivos de base de conocimientos. "
            f"Pregunta del cliente: {pregunta}"
        )
    
    # Instrucciones base
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    # Prompts por idioma para consultas inmobiliarias
    if idioma in ["inglés", "english"]:
        return (
            f"You are Vanessa's professional virtual assistant from TerraMagna Real State Boutique. "
            f"You help clients with rental and sale property inquiries. "
            f"Respond in English via {formato_base}. "
            f"Be warm, professional, and helpful. Use property information from your knowledge base. "
            f"Always try to understand what type of property the client is looking for and provide relevant options. "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller virtueller Assistent von TerraMagna Real State Boutique. "
            f"Sie helfen Kunden bei Anfragen zu Miet- und Verkaufsimmobilien. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, professionell und hilfreich. Verwenden Sie Immobilieninformationen aus Ihrer Wissensbasis. "
            f"Versuchen Sie immer zu verstehen, welche Art von Immobilie der Kunde sucht, und bieten Sie relevante Optionen an. "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente virtual profesional de Vanessa de TerraMagna Real State Boutique. "
            f"Ayudas a clientes con consultas sobre propiedades en alquiler y venta. "
            f"Responde en español via {formato_base}. "
            f"Sé cálido, profesional y útil. Usa la información de propiedades de tu base de conocimientos. "
            f"Siempre trata de entender qué tipo de propiedad busca el cliente y proporciona opciones relevantes. "
            f"Pregunta del cliente: {pregunta}"
        )

def crear_prompt_para_otro_tema(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea prompt para consultas de otro tema sin repetir bienvenida."""
    
    # Instrucciones base
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    # Prompts por idioma para otros temas
    if idioma in ["inglés", "english"]:
        return (
            f"You are Vanessa's professional virtual assistant from TerraMagna Real State Boutique. "
            f"A client has a specific inquiry that requires personalized attention from Vanessa. "
            f"Respond in English via {formato_base}. "
            f"Be warm, professional, and accommodating. "
            f"NEVER say that TerraMagna doesn't handle certain types of properties or services. "
            f"NEVER refer clients to other platforms or companies. "
            f"For ANY property or real estate inquiry, say that Vanessa will personally handle their request. "
            f"If they want to be contacted personally, ask for their name and phone number. "
            f"DO NOT repeat greetings or say 'Hello' again. Start directly with the helpful response. "
            f"DO NOT ask about properties at the end - focus only on their specific inquiry. "
            f"Client inquiry: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller virtueller Assistent von TerraMagna Real State Boutique. "
            f"Ein Kunde hat eine spezifische Anfrage, die persönliche Aufmerksamkeit von Vanessa erfordert. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, professionell und entgegenkommend. "
            f"Sagen Sie NIEMALS, dass TerraMagna bestimmte Arten von Immobilien oder Dienstleistungen nicht bearbeitet. "
            f"Verweisen Sie Kunden NIEMALS an andere Plattformen oder Unternehmen. "
            f"Für JEDE Immobilien- oder Immobilienanfrage sagen Sie, dass Vanessa ihre Anfrage persönlich bearbeiten wird. "
            f"Wenn sie persönlich kontaktiert werden möchten, fragen Sie nach Name und Telefonnummer. "
            f"Wiederholen Sie KEINE Begrüßungen und sagen Sie nicht noch einmal 'Hallo'. Beginnen Sie direkt mit der hilfreichen Antwort. "
            f"Fragen Sie am Ende NICHT nach Immobilien - konzentrieren Sie sich nur auf ihre spezifische Anfrage. "
            f"Kundenanfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente virtual profesional de Vanessa de TerraMagna Real State Boutique. "
            f"Un cliente tiene una consulta específica que requiere atención personalizada de Vanessa. "
            f"Responde en español via {formato_base}. "
            f"Sé cálido, profesional y acomodaticio. "
            f"NUNCA digas que TerraMagna no gestiona ciertos tipos de propiedades o servicios. "
            f"NUNCA refiera clientes a otras plataformas o empresas. "
            f"Para CUALQUIER consulta inmobiliaria o de propiedades, di que Vanessa se encargará personalmente de su solicitud. "
            f"Si quieren que les llame personalmente, pide su nombre y número de teléfono. "
            f"NO repitas saludos ni digas 'Hola' de nuevo. Comienza directamente con la respuesta útil. "
            f"NO preguntes sobre propiedades al final - enfócate solo en su consulta específica. "
            f"Consulta del cliente: {pregunta}"
        )

def generar_confirmacion_consulta_anotada(idioma: str) -> str:
    """Confirma que se anotó la consulta para Vanessa y pide datos de contacto."""
    if idioma in ["inglés", "english"]:
        return ("Thank you for the details. I have noted everything for Vanessa. "
                "For her to contact you personally, please provide your name and phone number.")
    elif idioma in ["alemán", "german", "deutsch"]:
        return ("Vielen Dank für die Details. Ich habe alles für Vanessa notiert. "
                "Damit sie Sie persönlich kontaktieren kann, geben Sie bitte Ihren Namen und Ihre Telefonnummer an.")
    else:  # español
        return ("Gracias por los detalles. He anotado todo para Vanessa. "
                "Para que pueda contactarte personalmente, por favor proporciona tu nombre y número de teléfono.")

def esta_en_horario_comercial() -> bool:
    """Verificación de horario comercial - SIEMPRE ACTIVO 24/7."""
    return True  # Siempre disponible       

def inicializar_agente():
    """Inicializa el agente inmobiliario con OpenAI y base de conocimiento."""
    global agente_executor
    
    logger.info("🔄 Iniciando el Agente de IA Inmobiliario...")
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY no configurada")
        agente_executor = lambda pregunta, **kwargs: "⚠️ Falta configurar OPENAI_API_KEY."
        return agente_executor
    
    try:
        # Imports protegidos
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_community.document_loaders import DirectoryLoader, TextLoader, Docx2txtLoader, PyPDFLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.chains import RetrievalQA
        
    except ImportError as error:
        mensaje_error = str(error)
        logger.error(f"❌ Error en imports: {mensaje_error}")
        agente_executor = lambda pregunta, **kwargs: f"❌ Librerías faltantes: {mensaje_error}"
        return agente_executor
    
    try:
        # Inicializar LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.2,
            max_tokens=2000
        )
        logger.info("✅ Modelo OpenAI cargado.")
        
        # Cargar documentos
        documentos = []
        directorio_conocimiento = "conocimiento"
        
        if not os.path.exists(directorio_conocimiento):
            logger.warning(f"📁 Creando directorio {directorio_conocimiento}")
            os.makedirs(directorio_conocimiento)
        else:
            # Cargar archivos
            tipos_archivo = [
                ("TXT", "*.txt", TextLoader, {'encoding': 'utf-8'}),
                ("DOCX", "*.docx", Docx2txtLoader, {}),
                ("PDF", "*.pdf", PyPDFLoader, {})
            ]
            
            for tipo, patron, loader_cls, kwargs in tipos_archivo:
                try:
                    loader = DirectoryLoader(
                        directorio_conocimiento,
                        glob=patron,
                        loader_cls=loader_cls,
                        loader_kwargs=kwargs,
                        show_progress=False
                    )
                    docs = loader.load()
                    if docs:
                        documentos.extend(docs)
                        logger.info(f"📄 {tipo}: {len(docs)} archivos cargados")
                except Exception as e:
                    logger.warning(f"⚠️ Error cargando {tipo}: {e}")
        
        # Crear agente según disponibilidad de documentos
        if documentos:
            logger.info(f"📚 Procesando {len(documentos)} documentos...")
            
            # Dividir documentos
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800, 
                chunk_overlap=100
            )
            docs_split = splitter.split_documents(documentos)
            
            # Crear vectorstore
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs_split, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            
            # Crear cadena QA
            qa = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=retriever,
                chain_type="stuff",
                return_source_documents=False
            )
            
            def agente_con_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    # Limpiar pregunta si viene de WhatsApp
                    pregunta_procesada = limpiar_texto_whatsapp(pregunta) if plataforma.lower() == "whatsapp" else pregunta
                    
                    if not pregunta_procesada.strip():
                        return "No pude entender tu mensaje. ¿Podrías reformularlo?"
                    
                    # NUEVO: Verificar si es comando de resumen
                    if plataforma.lower() == "whatsapp" and numero_whatsapp and es_comando_resumen(pregunta_procesada, numero_whatsapp):
                        logger.info("📋 Comando RESUMEN detectado desde número de inmobiliaria")
                        return generar_resumen_consultas()
                    
                    # Detectar idioma con detección de cambios MEJORADA
                    idioma_detectado = detectar_idioma_mejorado(pregunta_procesada, llm, numero_whatsapp)
                    
                    # Lógica de conversación para WhatsApp
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        logger.info(f"Estado actual para {numero_whatsapp[-4:]}****: {estado_conversacion['estado']}")
                        
                        # NUEVO: Verificar si hubo cambio de idioma
                        if estado_conversacion.get("cambio_idioma", False):
                            logger.info(f"🔄 Cambio de idioma detectado a: {idioma_detectado}")
                            # Resetear la bandera de cambio
                            estados_conversacion[numero_whatsapp]["cambio_idioma"] = False
                            # Mostrar mensaje de cambio de idioma
                            mensaje_cambio = generar_mensaje_cambio_idioma(idioma_detectado)
                            # Continuar con la respuesta normal pero incluir el mensaje de cambio
                            respuesta_base = mensaje_cambio + "\n\n"
                        else:
                            respuesta_base = ""
                        
                        # Si es el primer mensaje o estado inicial
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            logger.info(f"Intención detectada: {intencion}")
                            
                            if intencion == "inmobiliario_directo":
                                # Cliente menciona directamente inmuebles
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado = respuesta_base + respuesta.get("result", str(respuesta))
                            elif intencion == "otro_tema":
                                # Cliente menciona otro tema - GUARDAR CONSULTA
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                resultado = respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
                            else:
                                # Saludo inicial - preguntar qué necesita
                                logger.info("Generando saludo inicial de TerraMagna")
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                resultado = respuesta_base + generar_saludo_inicial(idioma_detectado)
                                logger.info(f"Saludo generado: {resultado[:100]}...")
                        
                        # Si estamos esperando que elija categoría
                        elif estado_conversacion["estado"] == "esperando_categoria":
                            categoria = detectar_respuesta_categoria(pregunta_procesada)
                            logger.info(f"Categoría detectada: {categoria} para mensaje: '{pregunta_procesada}'")
                            
                            if categoria == "inmobiliario":
                                logger.info("Procesando como consulta inmobiliaria específica")
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado_base_response = respuesta.get("result", str(respuesta))
                                # Agregar pregunta de seguimiento
                                resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                            elif categoria == "otro_tema":
                                logger.info("Procesando como asesoramiento personal - derivar a Vanessa")
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                resultado = respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
                            else:
                                # Si no está claro, preguntar de nuevo
                                logger.info("Categoría no clara, repitiendo saludo")
                                resultado = respuesta_base + generar_saludo_inicial(idioma_detectado)
                        
                        # Si ya estamos en modo inmobiliario
                        elif estado_conversacion["estado"] == "inmobiliario":
                            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                            respuesta = qa.invoke({"query": consulta})
                            resultado_base_response = respuesta.get("result", str(respuesta))
                            # Agregar pregunta de seguimiento después de cada respuesta
                            resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                            actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                        
                        # Si estamos esperando seguimiento después de una respuesta
                        elif estado_conversacion["estado"] == "esperando_seguimiento":
                            # Verificar primero si insiste en contacto personal
                            if detectar_insistencia_contacto_personal(pregunta_procesada):
                                logger.info("Cliente insiste en contacto con Vanessa - confirmar llamada")
                                actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                resultado = respuesta_base + generar_confirmacion_llamada(idioma_detectado)
                            # Verificar si quiere finalizar o continuar
                            elif detectar_finalizacion_conversacion(pregunta_procesada):
                                # Cliente agradece o dice que está bien
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado = respuesta_base + "You're welcome! Don't hesitate to contact us if you need anything else. Have a great day!"
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado = respuesta_base + "Gern geschehen! Zögern Sie nicht, uns zu kontaktieren, wenn Sie etwas anderes benötigen. Haben Sie einen schönen Tag!"
                                else:
                                    resultado = respuesta_base + "¡De nada! No dudes en contactarnos si necesitas algo más. ¡Que tengas un buen día!"
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                            else:
                                # Detectar nueva categoría
                                nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                                logger.info(f"Nueva categoría en seguimiento: {nueva_categoria}")
                                
                                if nueva_categoria == "inmobiliario":
                                    actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base_response = respuesta.get("result", str(respuesta))
                                    resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                                elif nueva_categoria == "otro_tema":
                                    logger.info("Cliente vuelve a otro tema - derivar a Vanessa")
                                    actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                    # Guardar la consulta para Vanessa
                                    guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                    resultado = respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
                                else:
                                    # Si no está claro, preguntar qué necesita
                                    if idioma_detectado in ["inglés", "english"]:
                                        resultado = respuesta_base + "What would you like to know more about? Our rental properties, properties for sale, or something else?"
                                    elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                        resultado = respuesta_base + "Worüber möchten Sie mehr erfahren? Unsere Mietimmobilien, Verkaufsimmobilien oder etwas anderes?"
                                    else:
                                        resultado = respuesta_base + "¿Sobre qué te gustaría saber más? ¿Nuestras propiedades en alquiler, propiedades en venta, o algo más?"
                        
                        # Si está confirmando que Vanessa llamará
                        elif estado_conversacion["estado"] == "confirmando_llamada":
                            # Verificar si proporciona datos de contacto
                            if detectar_datos_contacto(pregunta_procesada):
                                logger.info("Cliente proporcionó datos de contacto - confirmar y preguntar si algo más")
                                # NUEVO: Actualizar consulta con nombre extraído
                                nombre_extraido = extraer_nombre_del_texto(pregunta_procesada)
                                if numero_whatsapp in consultas_vanessa:
                                    consultas_vanessa[numero_whatsapp]['nombre'] = nombre_extraido
                                    consultas_vanessa[numero_whatsapp]['mensaje'] += f" | Datos de contacto: {pregunta_procesada}"
                                
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado = respuesta_base + "Perfect! I have noted your contact information. Vanessa will call you as soon as possible."
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado = respuesta_base + "Perfekt! Ich habe Ihre Kontaktdaten notiert. Vanessa wird Sie so schnell wie möglich anrufen."
                                else:
                                    resultado = respuesta_base + "¡Perfecto! He anotado tu información de contacto. Vanessa te llamará lo antes posible."
                                
                                # Preguntar si necesita algo más
                                resultado += "\n\n" + generar_pregunta_necesita_algo_mas(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "preguntando_algo_mas")
                            else:
                                # Si no da información clara, recordar que la necesitamos
                                logger.info("Cliente no proporcionó datos claros - pedir de nuevo")
                                resultado = respuesta_base + generar_confirmacion_llamada(idioma_detectado)
                        
                        # Nuevo estado: preguntando si necesita algo más
                        elif estado_conversacion["estado"] == "preguntando_algo_mas":
                            if detectar_respuesta_negativa(pregunta_procesada):
                                # Cliente dice que no necesita más ayuda - ofrecer propiedades antes de despedir
                                resultado = respuesta_base + generar_oferta_propiedades_final(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "ofreciendo_propiedades_final")
                            else:
                                # Cliente dice que sí o hace otra consulta
                                nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                                
                                if nueva_categoria == "inmobiliario":
                                    actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base_response = respuesta.get("result", str(respuesta))
                                    resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                                elif nueva_categoria == "otro_tema":
                                    actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                    consulta = crear_prompt_para_otro_tema(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base_response = respuesta.get("result", str(respuesta))
                                    # Guardar la consulta para Vanessa
                                    guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                    resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_necesita_algo_mas(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "preguntando_algo_mas")
                                else:
                                    # Si no está claro, preguntar qué necesita específicamente
                                    if idioma_detectado in ["inglés", "english"]:
                                        resultado = respuesta_base + "What specifically would you like help with?"
                                    elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                        resultado = respuesta_base + "Womit genau möchten Sie Hilfe?"
                                    else:
                                        resultado = respuesta_base + "¿Con qué específicamente te gustaría que te ayude?"
                        
                        # Nuevo estado: ofreciendo propiedades antes de despedir
                        elif estado_conversacion["estado"] == "ofreciendo_propiedades_final":
                            if detectar_respuesta_categoria(pregunta_procesada) == "inmobiliario":
                                # Cliente acepta conocer propiedades
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado_base_response = respuesta.get("result", str(respuesta))
                                resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                            else:
                                # Cliente no quiere propiedades, despedir definitivamente
                                resultado = respuesta_base + generar_despedida_final(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                        
                        # Si está en otro tema pero puede cambiar de opinión
                        elif estado_conversacion["estado"] == "otro_tema_finalizado":
                            # Verificar primero si insiste en que Vanessa le llame
                            if detectar_insistencia_contacto_personal(pregunta_procesada):
                                logger.info("Cliente insiste en llamada después de otro tema - confirmar")
                                actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
                                resultado = respuesta_base + generar_confirmacion_llamada(idioma_detectado)
                            else:
                                # El cliente está explicando más detalles sobre su consulta para Vanessa
                                # NO cambiar a inmobiliario aunque mencione propiedades
                                logger.info("Cliente continúa explicando su consulta para Vanessa - anotar y pedir datos")
                                
                                # NUEVO: Actualizar consulta existente con más detalles
                                if numero_whatsapp in consultas_vanessa:
                                    consultas_vanessa[numero_whatsapp]['mensaje'] += f" | Detalles adicionales: {pregunta_procesada}"
                                else:
                                    guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                
                                # Confirmar que se anotó y pedir datos de contacto
                                resultado = respuesta_base + generar_confirmacion_consulta_anotada(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
                        
                        # Si ya finalizó pero escribe de nuevo
                        elif estado_conversacion["estado"] == "finalizado":
                            # Reiniciar conversación
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
                            if intencion == "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado_base_response = respuesta.get("result", str(respuesta))
                                resultado = respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                resultado = respuesta_base + generar_saludo_inicial(idioma_detectado)
                        
                        else:
                            # Estado desconocido, reiniciar
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            resultado = respuesta_base + generar_saludo_inicial(idioma_detectado)
                    
                    else:
                        # Para web, usar lógica normal de consulta inmobiliaria
                        consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                        respuesta = qa.invoke({"query": consulta})
                        resultado = respuesta.get("result", str(respuesta))
                    
                    # Formatear según plataforma
                    resultado_formateado = formatear_respuesta_por_plataforma(resultado, plataforma)
                    
                    # Aplicar bandera solo en el primer mensaje si es WhatsApp
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        return aplicar_bandera_si_necesario(resultado_formateado, idioma_detectado, numero_whatsapp)
                    else:
                        return resultado_formateado
                    
                except Exception as e:
                    logger.error(f"Error en agente con documentos: {e}")
                    return "⚠️ Lo siento, ocurrió un error procesando tu consulta."
            
            agente_executor = agente_con_documentos
            
        else:
            logger.info("⚠️ No se encontraron documentos. Usando solo el modelo.")
            
            def agente_sin_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    pregunta_procesada = limpiar_texto_whatsapp(pregunta) if plataforma.lower() == "whatsapp" else pregunta
                    
                    if not pregunta_procesada.strip():
                        return "Mensaje vacío. ¿Podrías escribir tu consulta?"
                    
                    # NUEVO: Verificar si es comando de resumen
                    if plataforma.lower() == "whatsapp" and numero_whatsapp and es_comando_resumen(pregunta_procesada, numero_whatsapp):
                        logger.info("📋 Comando RESUMEN detectado desde número de inmobiliaria")
                        return generar_resumen_consultas()
                    
                    # Detectar idioma con detección de cambios MEJORADA
                    idioma_detectado = detectar_idioma_mejorado(pregunta_procesada, llm, numero_whatsapp)
                    
                    # Lógica de conversación para WhatsApp (sin documentos)
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        
                        # NUEVO: Verificar si hubo cambio de idioma
                        if estado_conversacion.get("cambio_idioma", False):
                            logger.info(f"🔄 Cambio de idioma detectado a: {idioma_detectado}")
                            # Resetear la bandera de cambio
                            estados_conversacion[numero_whatsapp]["cambio_idioma"] = False
                            # Mostrar mensaje de cambio de idioma
                            mensaje_cambio = generar_mensaje_cambio_idioma(idioma_detectado)
                            respuesta_base = mensaje_cambio + "\n\n"
                        else:
                            respuesta_base = ""
                        
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
                            if intencion == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                return aplicar_bandera_si_necesario(respuesta_base + generar_respuesta_otro_tema(idioma_detectado), idioma_detectado, numero_whatsapp)
                            elif intencion == "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria y seguimiento
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return aplicar_bandera_si_necesario(respuesta_base + generar_saludo_inicial(idioma_detectado), idioma_detectado, numero_whatsapp)
                        
                        elif estado_conversacion["estado"] == "esperando_categoria":
                            categoria = detectar_respuesta_categoria(pregunta_procesada)
                            
                            if categoria == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                return aplicar_bandera_si_necesario(respuesta_base + generar_respuesta_otro_tema(idioma_detectado), idioma_detectado, numero_whatsapp)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                        
                        elif estado_conversacion["estado"] == "esperando_seguimiento":
                            if detectar_finalizacion_conversacion(pregunta_procesada):
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado_final = respuesta_base + "You're welcome! Don't hesitate to contact us if you need anything else. Have a great day!"
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado_final = respuesta_base + "Gern geschehen! Zögern Sie nicht, uns zu kontaktieren, wenn Sie etwas anderes benötigen. Haben Sie einen schönen Tag!"
                                else:
                                    resultado_final = respuesta_base + "¡De nada! No dudes en contactarnos si necesitas algo más. ¡Que tengas un buen día!"
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                                return aplicar_bandera_si_necesario(resultado_final, idioma_detectado, numero_whatsapp)
                            
                            nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                            if nueva_categoria == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                # Guardar la consulta para Vanessa
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                return aplicar_bandera_si_necesario(respuesta_base + generar_respuesta_otro_tema(idioma_detectado), idioma_detectado, numero_whatsapp)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                        
                        elif estado_conversacion["estado"] == "otro_tema_finalizado":
                            nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                            if nueva_categoria == "inmobiliario":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                            else:
                                # Actualizar consulta existente o crear nueva
                                if numero_whatsapp in consultas_vanessa:
                                    consultas_vanessa[numero_whatsapp]['mensaje'] += f" | Detalles adicionales: {pregunta_procesada}"
                                else:
                                    guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                return aplicar_bandera_si_necesario(respuesta_base + generar_respuesta_otro_tema(idioma_detectado), idioma_detectado, numero_whatsapp)
                        
                        elif estado_conversacion["estado"] == "finalizado":
                            # Reiniciar conversación
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            if intencion != "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return aplicar_bandera_si_necesario(respuesta_base + generar_saludo_inicial(idioma_detectado), idioma_detectado, numero_whatsapp)
                    
                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
                    response = llm.invoke(consulta)
                    resultado_formateado = formatear_respuesta_por_plataforma(response.content, plataforma)
                    
                    # Aplicar bandera solo en el primer mensaje si es WhatsApp
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        return aplicar_bandera_si_necesario(resultado_formateado, idioma_detectado, numero_whatsapp)
                    else:
                        return resultado_formateado
                    
                except Exception as e:
                    logger.error(f"Error en agente sin documentos: {e}")
                    return "⚠️ Error procesando tu consulta."
            
            agente_executor = agente_sin_documentos
        
        logger.info("✅ Agente inicializado correctamente.")
        return agente_executor
        
    except Exception as e:
        mensaje_error = str(e)
        logger.error(f"❌ No se pudo inicializar el agente: {mensaje_error}")
        agente_executor = lambda pregunta, **kwargs: f"❌ Error del sistema: {mensaje_error}"
        return agente_executor

def ejecutar_agente(pregunta: str):
    """Ejecuta el agente para la plataforma WEB."""
    global agente_executor
    
    if agente_executor is None:
        logger.info("🔄 Agente no inicializado, inicializando...")
        inicializar_agente()
    
    if agente_executor is None:
        return "❌ No se pudo inicializar el agente."
    
    try:
        return agente_executor(pregunta, plataforma="web")
    except Exception as e:
        logger.error(f"❌ Error ejecutando agente web: {e}")
        return f"⚠️ Error procesando consulta: {str(e)}"

def ejecutar_agente_whatsapp(pregunta: str, numero_whatsapp: str = None):
    """Ejecuta el agente para WhatsApp con lógica de conversación."""
    global agente_executor
    
    if agente_executor is None:
        logger.info("🔄 Inicializando agente...")
        inicializar_agente()
    
    if agente_executor is None:
        return "❌ Servicio temporalmente no disponible"
    
    try:
        # Log de interacción (sin datos sensibles)
        numero_anonimo = numero_whatsapp[-4:] + "****" if numero_whatsapp else "desconocido"
        logger.info(f"📱 WhatsApp de {numero_anonimo}: {pregunta[:50]}...")
        
        respuesta = agente_executor(pregunta, plataforma="whatsapp", numero_whatsapp=numero_whatsapp)
        
        logger.info(f"✅ Respuesta WhatsApp enviada ({len(respuesta)} chars)")
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando agente WhatsApp: {e}")
        return "⚠️ Error procesando tu mensaje. Intenta nuevamente."

# NUEVAS FUNCIONES DE UTILIDAD PARA ADMINISTRACIÓN

def obtener_estadisticas_consultas() -> dict:
    """Obtiene estadísticas de las consultas guardadas para Vanessa."""
    if not consultas_vanessa:
        return {
            "total_consultas": 0,
            "consultas_hoy": 0,
            "idiomas": {},
            "ultima_consulta": None
        }
    
    from datetime import date
    hoy = date.today()
    consultas_hoy = 0
    idiomas = {}
    
    for consulta in consultas_vanessa.values():
        # Contar consultas de hoy
        fecha_consulta = consulta.get('timestamp', datetime.now()).date()
        if fecha_consulta == hoy:
            consultas_hoy += 1
        
        # Contar idiomas
        idioma = consulta.get('idioma', 'No detectado')
        idiomas[idioma] = idiomas.get(idioma, 0) + 1
    
    # Última consulta
    ultima_consulta = None
    if consultas_vanessa:
        ultima = max(consultas_vanessa.values(), key=lambda x: x.get('timestamp', datetime.min))
        ultima_consulta = {
            "fecha": ultima.get('fecha'),
            "idioma": ultima.get('idioma'),
            "nombre": ultima.get('nombre')
        }
    
    return {
        "total_consultas": len(consultas_vanessa),
        "consultas_hoy": consultas_hoy,
        "idiomas": idiomas,
        "ultima_consulta": ultima_consulta
    }

def limpiar_consultas_antiguas(dias: int = 30):
    """Limpia consultas más antiguas que X días."""
    global consultas_vanessa
    
    from datetime import timedelta
    fecha_limite = datetime.now() - timedelta(days=dias)
    
    consultas_a_eliminar = []
    for numero, consulta in consultas_vanessa.items():
        if consulta.get('timestamp', datetime.min) < fecha_limite:
            consultas_a_eliminar.append(numero)
    
    for numero in consultas_a_eliminar:
        del consultas_vanessa[numero]
    
    logger.info(f"🧹 Limpiadas {len(consultas_a_eliminar)} consultas antiguas (>{dias} días)")
    return len(consultas_a_eliminar)

def exportar_consultas_csv() -> str:
    """Exporta las consultas a formato CSV."""
    if not consultas_vanessa:
        return "No hay consultas para exportar"
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow(['Teléfono', 'Nombre', 'Fecha', 'Idioma', 'Consulta'])
    
    # Datos
    for numero, datos in consultas_vanessa.items():
        writer.writerow([
            numero,
            datos.get('nombre', 'No proporcionado'),
            datos.get('fecha', 'N/A'),
            datos.get('idioma', 'No detectado'),
            datos.get('mensaje', 'N/A')
        ])
    
    return output.getvalue()

# Test básico
if __name__ == "__main__":
    logger.info("🧪 Probando agente...")
    respuesta = ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
    logger.info(f"Respuesta: {respuesta}")
    
    # Test de resumen
    logger.info("🧪 Probando función de resumen...")
    print("Estadísticas:", obtener_estadisticas_consultas())
    print("Resumen:", generar_resumen_consultas())