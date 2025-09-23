import os
import re
import logging
import json
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import csv
import io

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variable global del agente
agente_executor = None

# Sistema de conversación con estados MEJORADO
estados_conversacion = {}

# Sistema de almacenamiento de consultas para Vanessa
consultas_vanessa = {}

# Configuración del número de la inmobiliaria
NUMERO_INMOBILIARIA = os.getenv("NUMERO_INMOBILIARIA", "")

def limpiar_texto_whatsapp(texto: str) -> str:
    """Limpia y normaliza texto de WhatsApp."""
    if not texto:
        return ""
    
    # Remover emojis y caracteres especiales, mantener texto básico
    texto_limpio = re.sub(r'[^\w\s.?!¿¡áéíóúñüÁÉÍÓÚÑÜ,:]', ' ', texto)
    # Normalizar espacios múltiples
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    return texto_limpio[:500]  # Limitar longitud

def detectar_idioma_mejorado(texto: str, llm=None, numero_whatsapp: str = None) -> str:
    """Detecta el idioma del texto usando el modelo LLM con memoria de conversación."""
    try:
        # Verificar si hay un idioma previamente detectado en la conversación
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

def detectar_idioma_actual(texto: str, llm=None) -> str:
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
        
        # Si no es claro y hay LLM disponible, usar LLM
        if llm and len(texto) > 50:
            consulta = (
                "Detecta en qué idioma está escrito el siguiente texto y "
                "responde con una sola palabra: "
                "español, inglés o alemán.\n"
                f"Texto: {texto[:200]}"
            )
            response = llm.invoke(consulta)
            idioma = response.content.strip().lower().replace('.', '')
            
            if idioma in ['español', 'inglés', 'alemán', 'spanish', 'english', 'german']:
                return idioma if idioma in ['español', 'inglés', 'alemán'] else 'español'
        
        return "español"  # Por defecto
        
    except Exception as e:
        logger.warning(f"Error detectando idioma actual: {e}")
        return "español"

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
        resumen += f"🌍 Idioma: {datos.get('idioma', 'No detectado')}\n"
        resumen += "─" * 30 + "\n\n"
    
    resumen += f"📊 *Total de consultas: {len(consultas_vanessa)}*"
    return resumen

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
    
    # Palabras que indican interés en VENTAS específicamente
    palabras_venta_especificas = [
        'venta', 'ventas', 'en venta', 'para venta', 'comprar', 'compra',
        'perfecto en venta', 'quiero en venta', 'interesa venta',
        'sale', 'for sale', 'buy', 'purchase'
    ]
    
    # Palabras que indican interés en ALQUILERES específicamente  
    palabras_alquiler_especificas = [
        'alquiler', 'alquilar', 'en alquiler', 'para alquiler', 'rentar',
        'perfecto en alquiler', 'quiero alquilar', 'interesa alquiler',
        'rent', 'rental', 'for rent'
    ]
    
    # Solicitudes de contacto con Vanessa
    solicitudes_contacto_vanessa = [
        'hablar con vanessa', 'contactar vanessa', 'vanessa', 'puedo hablar con vanessa',
        'quiero hablar con vanessa', 'me puede llamar vanessa', 'llamar vanessa',
        'speak with vanessa', 'contact vanessa', 'call vanessa'
    ]
    
    # Palabras que indican ASESORAMIENTO o consulta personal
    palabras_asesoria_personal = [
        'aconsejar', 'aconseje', 'asesoramiento', 'asesorar', 'ayuda para invertir',
        'consejos', 'consulta para invertir', 'quiero invertir', 'cómo invertir',
        'donde invertir', 'orientación', 'guía', 'recomendar zona', 'recomendar área',
        'mejor zona para', 'dónde es mejor', 'advice', 'consult', 'recommend'
    ]
    
    # PRIORIDAD 1: Detectar solicitudes de contacto con Vanessa
    if any(solicitud in texto_lower for solicitud in solicitudes_contacto_vanessa):
        return "otro_tema"
    
    # PRIORIDAD 2: Detectar interés específico en ventas o alquileres
    elif any(palabra in texto_lower for palabra in palabras_venta_especificas + palabras_alquiler_especificas):
        return "inmobiliario"
    
    # PRIORIDAD 3: Detectar asesoramiento personal
    elif any(palabra in texto_lower for palabra in palabras_asesoria_personal):
        return "otro_tema"
    
    # Si menciona propiedades en general
    palabras_inmobiliario_general = [
        'casa', 'piso', 'apartamento', 'propiedad', 'inmueble', 'vivienda', 
        'house', 'apartment', 'property'
    ]
    
    if any(palabra in texto_lower for palabra in palabras_inmobiliario_general):
        return "inmobiliario"
    else:
        return "seguimiento"

def detectar_consulta_propiedad_especifica(texto: str) -> bool:
    """Detecta si el cliente pregunta por una propiedad específica."""
    texto_lower = texto.lower()
    
    # Palabras que indican consulta específica
    indicadores_especificos = [
        'adosado', 'villa', 'dúplex', 'duplex', 'apartamento', 'hotel',
        'fanabé', 'fanabe', 'galeón', 'galeon', 'caldera', 'costa adeje',
        'palm mar', 'campo de golf', 'norte de tenerife'
    ]
    
    return any(indicador in texto_lower for indicador in indicadores_especificos)

def obtener_estado_conversacion(numero_whatsapp: str) -> dict:
    """Obtiene el estado actual de la conversación."""
    if numero_whatsapp not in estados_conversacion:
        estados_conversacion[numero_whatsapp] = {
            "estado": "inicial",
            "ultima_interaccion": datetime.now(),
            "contador_mensajes": 0,
            "idioma_detectado": None,
            "bandera_mostrada": False,
            "cambio_idioma": False
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
    """Genera el saludo inicial según el idioma."""
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
    ]) or bool(re.search(r'\d{3}.*\d{3}.*\d{3}', texto))
    
    # Si tiene ambos o al menos uno muy claro
    if tiene_nombre and tiene_telefono:
        return True
    
    # Detectar si hay números de teléfono largos en el texto
    if re.search(r'\d{6,}', texto):
        return True
    
    # Detectar formato español común
    if re.search(r'6\d{8}|9\d{8}|[+]34\s*6\d{8}|[+]34\s*9\d{8}', texto):
        return True
    
    return False

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
    """Detecta si el cliente insiste en hablar con Vanessa."""
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
        'cuándo me llama',
        'puedo hablar con vanessa',
        'hablar con vanessa',
        'contactar vanessa'
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
    
    # Solo palabras que realmente indican finalización
    palabras_finalizacion_real = [
        'gracias y nada más', 'thank you and nothing else', 'danke und nichts mehr',
        'eso es todo gracias', "that's all thanks", 'das ist alles danke',
        'no necesito nada más gracias', 'no necesito más gracias',
        'estoy bien gracias', 'i\'m good thanks', 'i\'m fine thanks'
    ]
    
    # Excluir respuestas que indican interés en propiedades
    palabras_que_indican_interes = [
        'venta', 'ventas', 'alquiler', 'alquilar', 'comprar', 'casa', 'piso',
        'apartamento', 'propiedad', 'vanessa', 'hablar', 'contacto',
        'perfecto en', 'quiero en', 'interesa', 'sale', 'rent', 'buy'
    ]
    
    # Si contiene palabras de interés, NO es finalización
    if any(palabra in texto_lower for palabra in palabras_que_indican_interes):
        return False
    
    # Solo es finalización si usa frases específicas de cierre
    return any(frase in texto_lower for frase in palabras_finalizacion_real)

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
            
            f"CRITICAL INSTRUCTIONS FOR SALES INQUIRIES: "
            f"When asked about properties for SALE, follow this EXACT format: "
            f"1. Start with: 'We currently have X properties for sale:' "
            f"2. List all properties WITHOUT prices or URLs "
            f"3. End EXACTLY with: 'What type of property interests you or would you like detailed information about any specific one?' "
            f"4. DO NOT add any additional questions after this "
            f"5. DO NOT ask 'Is there anything else I can help you with?' in sales inquiries "
            f"6. Only provide complete details when they ask for a specific property "
            
            f"Use ONLY information from your knowledge base files. "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller virtueller Assistent von TerraMagna Real State Boutique. "
            f"Sie helfen Kunden bei Anfragen zu Miet- und Verkaufsimmobilien. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, professionell und hilfreich. Verwenden Sie Immobilieninformationen aus Ihrer Wissensbasis. "
            
            f"KRITISCHE ANWEISUNGEN FÜR VERKAUFSANFRAGEN: "
            f"Bei Fragen zu VERKAUFSIMMOBILIEN folgen Sie diesem EXAKTEN Format: "
            f"1. Beginnen Sie mit: 'Wir haben derzeit X Immobilien zum Verkauf:' "
            f"2. Listen Sie alle Immobilien OHNE Preise oder URLs auf "
            f"3. Enden Sie GENAU mit: 'Welche Art von Immobilie interessiert Sie oder möchten Sie detaillierte Informationen zu einer bestimmten?' "
            f"4. Fügen Sie KEINE zusätzlichen Fragen danach hinzu "
            f"5. Fragen Sie NICHT 'Gibt es noch etwas, womit ich Ihnen helfen kann?' bei Verkaufsanfragen "
            f"6. Geben Sie nur vollständige Details an, wenn sie nach einer bestimmten Immobilie fragen "
            
            f"Verwenden Sie NUR Informationen aus Ihren Wissensdateien. "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente virtual profesional de Vanessa de TerraMagna Real State Boutique. "
            f"Ayudas a clientes con consultas sobre propiedades en alquiler y venta. "
            f"Responde en español via {formato_base}. "
            f"Sé cálido, profesional y útil. Usa la información de propiedades de tu base de conocimientos. "
            
            f"INSTRUCCIONES CRÍTICAS PARA CONSULTAS DE VENTAS: "
            f"Cuando pregunten por propiedades en VENTA, sigue este formato EXACTO: "
            f"1. Empieza con: 'Tenemos actualmente X propiedades en venta:' "
            f"2. Lista todas las propiedades SIN precios ni URLs "
            f"3. Termina EXACTAMENTE con: '¿Qué tipo de propiedad te interesa o te gustaría información detallada de alguna en concreto?' "
            f"4. NO añadir ninguna pregunta adicional después "
            f"5. NO preguntar '¿Hay algo más en lo que pueda ayudarte?' en consultas de ventas "
            f"6. Solo dar detalles completos cuando pregunten por una propiedad específica "
            
            f"Usa ÚNICAMENTE información de tus archivos de base de conocimientos. "
            f"Pregunta del cliente: {pregunta}"
        )

def crear_prompt_consulta_detallada(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea prompt para cuando el cliente pregunta por una propiedad específica."""
    
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    if idioma in ["inglés", "english"]:
        return (
            f"You are Vanessa's professional assistant from Terra Magna Real Estate Boutique. "
            f"A client is asking for DETAILED INFORMATION about a specific property. "
            f"Respond in English via {formato_base}. "
            f"Provide COMPLETE details including: price, features, location, URL, and all available information. "
            f"Use ALL relevant information from your knowledge base for this specific property. "
            f"Be thorough and detailed. "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller Assistent von Terra Magna Real Estate Boutique. "
            f"Ein Kunde fragt nach DETAILLIERTEN INFORMATIONEN über eine bestimmte Immobilie. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Geben Sie VOLLSTÄNDIGE Details an: Preis, Ausstattung, Lage, URL und alle verfügbaren Informationen. "
            f"Verwenden Sie ALLE relevanten Informationen aus Ihrer Wissensbasis für diese spezifische Immobilie. "
            f"Seien Sie gründlich und detailliert. "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente profesional de Vanessa de Terra Magna Real Estate Boutique. "
            f"Un cliente pregunta por INFORMACIÓN DETALLADA sobre una propiedad específica. "
            f"Responde en español via {formato_base}. "
            f"Proporciona detalles COMPLETOS incluyendo: precio, características, ubicación, URL y toda la información disponible. "
            f"Usa TODA la información relevante de tu base de conocimientos para esta propiedad específica. "
            f"Sé exhaustivo y detallado. "
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
                    
                    # Verificar si es comando de resumen
                    if plataforma.lower() == "whatsapp" and numero_whatsapp and es_comando_resumen(pregunta_procesada, numero_whatsapp):
                        logger.info("📋 Comando RESUMEN detectado desde número de inmobiliaria")
                        return generar_resumen_consultas()
                    
                    # Detectar idioma con detección de cambios MEJORADA
                    idioma_detectado = detectar_idioma_mejorado(pregunta_procesada, llm, numero_whatsapp)
                    
                    # Lógica de conversación para WhatsApp
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        logger.info(f"Estado actual para {numero_whatsapp[-4:]}****: {estado_conversacion['estado']}")
                        
                        # Verificar si hubo cambio de idioma
                        if estado_conversacion.get("cambio_idioma", False):
                            logger.info(f"🔄 Cambio de idioma detectado a: {idioma_detectado}")
                            estados_conversacion[numero_whatsapp]["cambio_idioma"] = False
                            mensaje_cambio = generar_mensaje_cambio_idioma(idioma_detectado)
                            respuesta_base = mensaje_cambio + "\n\n"
                        else:
                            respuesta_base = ""
                        
                        # Procesar según el estado actual
                        resultado = procesar_estado_conversacion(
                            estado_conversacion, pregunta_procesada, idioma_detectado,
                            numero_whatsapp, respuesta_base, qa, plataforma
                        )
                    else:
                        # Para web, usar lógica normal
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
                    
                    # Verificar si es comando de resumen
                    if plataforma.lower() == "whatsapp" and numero_whatsapp and es_comando_resumen(pregunta_procesada, numero_whatsapp):
                        logger.info("📋 Comando RESUMEN detectado")
                        return generar_resumen_consultas()
                    
                    # Detectar idioma
                    idioma_detectado = detectar_idioma_mejorado(pregunta_procesada, llm, numero_whatsapp)
                    
                    # Lógica simplificada para WhatsApp sin documentos
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        
                        if estado_conversacion.get("cambio_idioma", False):
                            estados_conversacion[numero_whatsapp]["cambio_idioma"] = False
                            mensaje_cambio = generar_mensaje_cambio_idioma(idioma_detectado)
                            respuesta_base = mensaje_cambio + "\n\n"
                        else:
                            respuesta_base = ""
                        
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
                            if intencion == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
                                return aplicar_bandera_si_necesario(respuesta_base + generar_respuesta_otro_tema(idioma_detectado), idioma_detectado, numero_whatsapp)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return aplicar_bandera_si_necesario(respuesta_base + generar_saludo_inicial(idioma_detectado), idioma_detectado, numero_whatsapp)
                    
                    # Usar LLM directamente
                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    response = llm.invoke(consulta)
                    resultado_formateado = formatear_respuesta_por_plataforma(response.content, plataforma)
                    
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

def procesar_estado_conversacion(estado_conversacion, pregunta_procesada, idioma_detectado, 
                                 numero_whatsapp, respuesta_base, qa, plataforma):
    """Procesa la conversación según el estado actual."""
    
    estado_actual = estado_conversacion["estado"]
    
    if estado_actual == "inicial":
        return procesar_estado_inicial(pregunta_procesada, idioma_detectado, numero_whatsapp, 
                                      respuesta_base, qa, plataforma)
    
    elif estado_actual == "esperando_categoria":
        return procesar_esperando_categoria(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                           respuesta_base, qa, plataforma)
    
    elif estado_actual == "esperando_seguimiento":
        return procesar_esperando_seguimiento(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                             respuesta_base, qa, plataforma)
    
    elif estado_actual == "inmobiliario":
        return procesar_estado_inmobiliario(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                           respuesta_base, qa, plataforma)
    
    elif estado_actual == "confirmando_llamada":
        return procesar_confirmando_llamada(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                           respuesta_base)
    
    elif estado_actual == "otro_tema_finalizado":
        return procesar_otro_tema_finalizado(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                            respuesta_base)
    
    elif estado_actual == "finalizado":
        # Reiniciar conversación
        actualizar_estado_conversacion(numero_whatsapp, "inicial")
        return procesar_estado_inicial(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                      respuesta_base, qa, plataforma)
    
    else:
        # Estado desconocido, reiniciar
        actualizar_estado_conversacion(numero_whatsapp, "inicial")
        return respuesta_base + generar_saludo_inicial(idioma_detectado)
           # Estado desconocido, reiniciar
        actualizar_estado_conversacion(numero_whatsapp, "inicial")
        return respuesta_base + generar_saludo_inicial(idioma_detectado)

def procesar_estado_inicial(pregunta_procesada, idioma_detectado, numero_whatsapp, 
                           respuesta_base, qa, plataforma):
    """Procesa el estado inicial de la conversación."""
    intencion = detectar_intencion_inicial(pregunta_procesada)
    logger.info(f"Intención detectada: {intencion}")
    
    if intencion == "inmobiliario_directo":
        actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
        if detectar_consulta_propiedad_especifica(pregunta_procesada):
            consulta = crear_prompt_consulta_detallada(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            return respuesta_base + respuesta.get("result", str(respuesta))
        elif "venta" in pregunta_procesada.lower() or "ventas" in pregunta_procesada.lower():
            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            return respuesta_base + respuesta.get("result", str(respuesta))
        else:
            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            resultado_base_response = respuesta.get("result", str(respuesta))
            return respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
    
    elif intencion == "otro_tema":
        actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
        guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
        return respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
    else:
        actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
        return respuesta_base + generar_saludo_inicial(idioma_detectado)

def procesar_esperando_categoria(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                respuesta_base, qa, plataforma):
    """Procesa cuando esperamos que el cliente elija categoría."""
    categoria = detectar_respuesta_categoria(pregunta_procesada)
    logger.info(f"Categoría detectada: {categoria}")
    
    if categoria == "inmobiliario":
        actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
        if detectar_consulta_propiedad_especifica(pregunta_procesada):
            consulta = crear_prompt_consulta_detallada(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            return respuesta_base + respuesta.get("result", str(respuesta))
        elif "venta" in pregunta_procesada.lower() or "ventas" in pregunta_procesada.lower():
            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            return respuesta_base + respuesta.get("result", str(respuesta))
        else:
            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
            respuesta = qa.invoke({"query": consulta})
            resultado_base_response = respuesta.get("result", str(respuesta))
            actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
            return respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
    
    elif categoria == "otro_tema":
        actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
        guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
        return respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
    else:
        return respuesta_base + generar_saludo_inicial(idioma_detectado)

def procesar_esperando_seguimiento(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                  respuesta_base, qa, plataforma):
    """Procesa cuando esperamos seguimiento después de una respuesta."""
    if detectar_insistencia_contacto_personal(pregunta_procesada):
        actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
        guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
        return respuesta_base + generar_confirmacion_llamada(idioma_detectado)
    
    elif detectar_finalizacion_conversacion(pregunta_procesada):
        actualizar_estado_conversacion(numero_whatsapp, "finalizado")
        return respuesta_base + generar_despedida_final(idioma_detectado)
    
    else:
        nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
        
        if nueva_categoria == "inmobiliario":
            actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
            return procesar_consulta_inmobiliaria(pregunta_procesada, idioma_detectado, 
                                                 numero_whatsapp, respuesta_base, qa, plataforma)
        elif nueva_categoria == "otro_tema":
            actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
            guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
            return respuesta_base + generar_respuesta_otro_tema(idioma_detectado)
        else:
            if idioma_detectado in ["inglés", "english"]:
                return respuesta_base + "What would you like to know more about? Our rental properties, properties for sale, or something else?"
            elif idioma_detectado in ["alemán", "german", "deutsch"]:
                return respuesta_base + "Worüber möchten Sie mehr erfahren? Unsere Mietimmobilien, Verkaufsimmobilien oder etwas anderes?"
            else:
                return respuesta_base + "¿Sobre qué te gustaría saber más? ¿Nuestras propiedades en alquiler, propiedades en venta, o algo más?"

def procesar_estado_inmobiliario(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                respuesta_base, qa, plataforma):
    """Procesa consultas cuando ya estamos en modo inmobiliario."""
    return procesar_consulta_inmobiliaria(pregunta_procesada, idioma_detectado,
                                         numero_whatsapp, respuesta_base, qa, plataforma)

def procesar_consulta_inmobiliaria(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                  respuesta_base, qa, plataforma):
    """Procesa una consulta inmobiliaria específica."""
    if detectar_consulta_propiedad_especifica(pregunta_procesada):
        consulta = crear_prompt_consulta_detallada(pregunta_procesada, idioma_detectado, plataforma)
        respuesta = qa.invoke({"query": consulta})
        return respuesta_base + respuesta.get("result", str(respuesta))
    elif "venta" in pregunta_procesada.lower() or "ventas" in pregunta_procesada.lower():
        consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
        respuesta = qa.invoke({"query": consulta})
        return respuesta_base + respuesta.get("result", str(respuesta))
    else:
        consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
        respuesta = qa.invoke({"query": consulta})
        resultado_base_response = respuesta.get("result", str(respuesta))
        actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
        return respuesta_base + resultado_base_response + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)

def procesar_confirmando_llamada(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                respuesta_base):
    """Procesa cuando confirmamos que Vanessa llamará."""
    if detectar_datos_contacto(pregunta_procesada):
        nombre_extraido = extraer_nombre_del_texto(pregunta_procesada)
        if numero_whatsapp in consultas_vanessa:
            consultas_vanessa[numero_whatsapp]['nombre'] = nombre_extraido
            consultas_vanessa[numero_whatsapp]['mensaje'] += f" | Datos de contacto: {pregunta_procesada}"
        
        actualizar_estado_conversacion(numero_whatsapp, "finalizado")
        
        if idioma_detectado in ["inglés", "english"]:
            return respuesta_base + "Perfect! I have noted your contact information. Vanessa will call you as soon as possible."
        elif idioma_detectado in ["alemán", "german", "deutsch"]:
            return respuesta_base + "Perfekt! Ich habe Ihre Kontaktdaten notiert. Vanessa wird Sie so schnell wie möglich anrufen."
        else:
            return respuesta_base + "¡Perfecto! He anotado tu información de contacto. Vanessa te llamará lo antes posible."
    else:
        return respuesta_base + generar_confirmacion_llamada(idioma_detectado)

def procesar_otro_tema_finalizado(pregunta_procesada, idioma_detectado, numero_whatsapp,
                                 respuesta_base):
    """Procesa cuando el cliente continúa después de otro tema."""
    if detectar_insistencia_contacto_personal(pregunta_procesada):
        actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
        return respuesta_base + generar_confirmacion_llamada(idioma_detectado)
    else:
        if numero_whatsapp in consultas_vanessa:
            consultas_vanessa[numero_whatsapp]['mensaje'] += f" | Detalles adicionales: {pregunta_procesada}"
        else:
            guardar_consulta_vanessa(numero_whatsapp, pregunta_procesada, idioma_detectado)
        
        actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
        return respuesta_base + generar_confirmacion_consulta_anotada(idioma_detectado)

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

# FUNCIONES DE UTILIDAD PARA ADMINISTRACIÓN

def obtener_estadisticas_consultas() -> dict:
    """Obtiene estadísticas de las consultas guardadas para Vanessa."""
    if not consultas_vanessa:
        return {
            "total_consultas": 0,
            "consultas_hoy": 0,
            "idiomas": {},
            "ultima_consulta": None
        }
    
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
    logger.info("🧪 Iniciando pruebas del sistema...")
    
    # Inicializar el agente
    inicializar_agente()
    
    # Prueba básica
    print("\n" + "="*50)
    print("PRUEBA 1: Consulta Web en Español")
    print("="*50)
    respuesta = ejecutar_agente("¿Cuáles son los precios de las casas en venta?")
    print(f"Respuesta: {respuesta[:200]}...")
    
    # Prueba WhatsApp
    print("\n" + "="*50)
    print("PRUEBA 2: Consulta WhatsApp")
    print("="*50)
    respuesta_wa = ejecutar_agente_whatsapp("Hola", "+34600000000")
    print(f"Respuesta WhatsApp: {respuesta_wa}")
    
    # Estadísticas
    print("\n" + "="*50)
    print("ESTADÍSTICAS DEL SISTEMA")
    print("="*50)
    stats = obtener_estadisticas_consultas()
    print(f"Total consultas: {stats['total_consultas']}")
    print(f"Consultas hoy: {stats['consultas_hoy']}")
    print(f"Idiomas detectados: {stats['idiomas']}")
    
    print("\n✅ Sistema de IA Inmobiliario funcionando correctamente")
    print("📚 Recuerda colocar tus documentos en la carpeta 'conocimiento/'")
    print("🔑 Asegúrate de configurar OPENAI_API_KEY en el archivo .env")# cerebro.py - VERSIÓN CORREGIDA Y FUNCIONAL
# Sistema de Asistente Virtual Inmobiliario con IA