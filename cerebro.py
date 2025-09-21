# cerebro_inmobiliaria_optimizado.py - VERSIÓN FINAL CON LÓGICA DE CONVERSACIÓN

import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variable global del agente
agente_executor = None

# Sistema de conversación con estados
estados_conversacion = {}

def limpiar_texto_whatsapp(texto: str) -> str:
    """Limpia y normaliza texto de WhatsApp."""
    if not texto:
        return ""
    
    # Remover emojis y caracteres especiales, mantener texto básico
    texto_limpio = re.sub(r'[^\w\s.?!¿¡áéíóúñüÁÉÍÓÚÑÜ,:]', ' ', texto)
    # Normalizar espacios múltiples
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    return texto_limpio[:500]  # Limitar longitud

def detectar_idioma(texto: str, llm) -> str:
    """Detecta el idioma del texto usando el modelo LLM."""
    try:
        # Detección rápida para casos obvios
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
        logger.warning(f"Error detectando idioma: {e}")
        return "español"

def detectar_intencion_inicial(texto: str) -> str:
    """Detecta si el mensaje es un saludo inicial o ya indica intención específica."""
    texto_lower = texto.lower().strip()
    
    # Palabras que indican saludo inicial simple
    saludos_simples = ['hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches', 'hey', 'buenas']
    
    # Palabras que indican intención de propiedades
    inmobiliario = ['alquiler', 'venta', 'casa', 'piso', 'apartamento', 'propiedad', 'inmueble', 
                   'rent', 'sale', 'house', 'apartment', 'property', 'comprar', 'rentar', 'vender']
    
    # Palabras que indican otros temas específicos
    otros_temas = ['consulta legal', 'información legal', 'servicio legal', 'ayuda legal', 'contacto', 'vanessa', 
                   'llamar', 'llame', 'teléfono', 'telefono', 'call', 'phone']
    
    # Si es exactamente un saludo simple sin más contexto
    if texto_lower in saludos_simples or (any(saludo in texto_lower for saludo in saludos_simples) and len(texto.split()) <= 2):
        return "saludo_inicial"
    
    # Verificar si contiene palabras inmobiliarias específicas
    if any(palabra in texto_lower for palabra in inmobiliario):
        return "inmobiliario_directo"
    
    # Verificar si menciona otros temas específicamente (incluye solicitudes de llamada)
    if any(tema in texto_lower for tema in otros_temas):
        return "otro_tema"
    
    # Si el mensaje es más largo o tiene contenido específico, NO es saludo inicial
    if len(texto.split()) > 3:
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
    
    # Palabras que indican otro tema claramente
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
            "bandera_mostrada": False
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

def generar_pregunta_seguimiento(idioma: str) -> str:
    """Genera pregunta de seguimiento después de una respuesta."""
    if idioma in ["inglés", "english"]:
        return "Is there anything else I can help you with? Would you like to know about our rental or sale properties?"
    elif idioma in ["alemán", "german", "deutsch"]:
        return "Gibt es noch etwas, womit ich Ihnen helfen kann? Möchten Sie mehr über unsere Miet- oder Verkaufsimmobilien erfahren?"
    else:  # español
        return "¿Hay algo más en lo que pueda ayudarte? ¿Te gustaría conocer nuestras propiedades en alquiler o venta?"

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

def generar_pregunta_necesita_algo_mas(idioma: str) -> str:
    """Pregunta si necesita algo más después de que explique sus necesidades."""
    if idioma in ["inglés", "english"]:
        return "Is there anything else I can help you with today?"
    elif idioma in ["alemán", "german", "deutsch"]:
        return "Gibt es noch etwas anderes, womit ich Ihnen heute helfen kann?"
    else:  # español
        return "¿Hay algo más en lo que pueda ayudarte hoy?"

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
            f"A client has a non-real estate inquiry. Respond professionally and helpfully. "
            f"Respond in English via {formato_base}. "
            f"Be warm, professional, and offer appropriate assistance. "
            f"If they want to be contacted personally, ask for their name and phone number. "
            f"Client inquiry: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind Vanessas professioneller virtueller Assistent von TerraMagna Real State Boutique. "
            f"Ein Kunde hat eine Anfrage, die nicht mit Immobilien zusammenhängt. Antworten Sie professionell und hilfreich. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, professionell und bieten Sie angemessene Hilfe an. "
            f"Wenn sie persönlich kontaktiert werden möchten, fragen Sie nach Name und Telefonnummer. "
            f"Kundenanfrage: {pregunta}"
        )
    else:  # español
        return (
            f"Eres el asistente virtual profesional de Vanessa de TerraMagna Real State Boutique. "
            f"Un cliente tiene una consulta que no es sobre inmuebles. Responde de manera profesional y útil. "
            f"Responde en español via {formato_base}. "
            f"Sé cálido, profesional y ofrece la asistencia apropiada. "
            f"Si quieren que les llame personalmente, pide su nombre y número de teléfono. "
            f"Consulta del cliente: {pregunta}"
        )
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
                    
                    # Detectar idioma
                    idioma_detectado = detectar_idioma(pregunta_procesada, llm)
                    
                    # Lógica de conversación para WhatsApp
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        logger.info(f"Estado actual para {numero_whatsapp[-4:]}****: {estado_conversacion['estado']}")
                        
                        # Si es el primer mensaje o estado inicial
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            logger.info(f"Intención detectada: {intencion}")
                            
                            if intencion == "inmobiliario_directo":
                                # Cliente menciona directamente inmuebles
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado = respuesta.get("result", str(respuesta))
                            elif intencion == "otro_tema":
                                # Cliente menciona otro tema
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema")
                                resultado = generar_respuesta_otro_tema(idioma_detectado)
                            else:
                                # Saludo inicial - preguntar qué necesita
                                logger.info("Generando saludo inicial de TerraMagna")
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                resultado = generar_saludo_inicial(idioma_detectado)
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
                                resultado_base = respuesta.get("result", str(respuesta))
                                # Agregar pregunta de seguimiento
                                resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                            elif categoria == "otro_tema":
                                logger.info("Procesando como asesoramiento personal - derivar a Vanessa")
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                resultado = generar_respuesta_otro_tema(idioma_detectado)
                            else:
                                # Si no está claro, preguntar de nuevo
                                logger.info("Categoría no clara, repitiendo saludo")
                                resultado = generar_saludo_inicial(idioma_detectado)
                        
                        # Si ya estamos en modo inmobiliario
                        elif estado_conversacion["estado"] == "inmobiliario":
                            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                            respuesta = qa.invoke({"query": consulta})
                            resultado_base = respuesta.get("result", str(respuesta))
                            # Agregar pregunta de seguimiento después de cada respuesta
                            resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                            actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                        
                        # Si estamos esperando seguimiento después de una respuesta
                        elif estado_conversacion["estado"] == "esperando_seguimiento":
                            # Verificar primero si insiste en contacto personal
                            if detectar_insistencia_contacto_personal(pregunta_procesada):
                                logger.info("Cliente insiste en contacto con Vanessa - confirmar llamada")
                                actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
                                resultado = generar_confirmacion_llamada(idioma_detectado)
                            # Verificar si quiere finalizar o continuar
                            elif detectar_finalizacion_conversacion(pregunta_procesada):
                                # Cliente agradece o dice que está bien
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado = "You're welcome! Don't hesitate to contact us if you need anything else. Have a great day! 😊"
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado = "Gern geschehen! Zögern Sie nicht, uns zu kontaktieren, wenn Sie etwas anderes benötigen. Haben Sie einen schönen Tag! 😊"
                                else:
                                    resultado = "¡De nada! No dudes en contactarnos si necesitas algo más. ¡Que tengas un buen día! 😊"
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                            else:
                                # Detectar nueva categoría
                                nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                                logger.info(f"Nueva categoría en seguimiento: {nueva_categoria}")
                                
                                if nueva_categoria == "inmobiliario":
                                    actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base = respuesta.get("result", str(respuesta))
                                    resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                                elif nueva_categoria == "otro_tema":
                                    logger.info("Cliente vuelve a otro tema - derivar a Vanessa")
                                    actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                    resultado = generar_respuesta_otro_tema(idioma_detectado)
                                else:
                                    # Si no está claro, preguntar qué necesita
                                    if idioma_detectado in ["inglés", "english"]:
                                        resultado = "What would you like to know more about? Our rental properties, properties for sale, or something else?"
                                    elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                        resultado = "Worüber möchten Sie mehr erfahren? Unsere Mietimmobilien, Verkaufsimmobilien oder etwas anderes?"
                                    else:
                                        resultado = "¿Sobre qué te gustaría saber más? ¿Nuestras propiedades en alquiler, propiedades en venta, o algo más?"
                        
                        # Si está confirmando que Vanessa llamará
                        elif estado_conversacion["estado"] == "confirmando_llamada":
                            # Cliente proporciona datos de contacto o insiste más
                            if any(palabra in pregunta_procesada.lower() for palabra in ['mi nombre', 'me llamo', 'soy', 'mi número', 'mi teléfono']):
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado = "Perfect! I have noted your contact information. Vanessa will call you as soon as possible."
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado = "Perfekt! Ich habe Ihre Kontaktdaten notiert. Vanessa wird Sie so schnell wie möglich anrufen."
                                else:
                                    resultado = "¡Perfecto! He anotado tu información de contacto. Vanessa te llamará lo antes posible."
                                
                                # Preguntar si necesita algo más
                                resultado += "\n\n" + generar_pregunta_necesita_algo_mas(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "preguntando_algo_mas")
                            else:
                                # Si no da información, recordar que la necesitamos
                                resultado = generar_confirmacion_llamada(idioma_detectado)
                        
                        # Nuevo estado: preguntando si necesita algo más
                        elif estado_conversacion["estado"] == "preguntando_algo_mas":
                            if detectar_respuesta_negativa(pregunta_procesada):
                                # Cliente dice que no necesita más ayuda
                                resultado = generar_despedida_final(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                            else:
                                # Cliente dice que sí o hace otra consulta
                                nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                                
                                if nueva_categoria == "inmobiliario":
                                    actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base = respuesta.get("result", str(respuesta))
                                    resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                                elif nueva_categoria == "otro_tema":
                                    actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                    consulta = crear_prompt_para_otro_tema(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base = respuesta.get("result", str(respuesta))
                                    resultado = resultado_base + "\n\n" + generar_pregunta_necesita_algo_mas(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "preguntando_algo_mas")
                                else:
                                    # Si no está claro, preguntar qué necesita específicamente
                                    if idioma_detectado in ["inglés", "english"]:
                                        resultado = "What specifically would you like help with?"
                                    elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                        resultado = "Womit genau möchten Sie Hilfe?"
                                    else:
                                        resultado = "¿Con qué específicamente te gustaría que te ayude?"
                        
                        # Si está en otro tema pero puede cambiar de opinión
                        elif estado_conversacion["estado"] == "otro_tema_finalizado":
                            # Verificar primero si insiste en que Vanessa le llame
                            if detectar_insistencia_contacto_personal(pregunta_procesada):
                                logger.info("Cliente insiste en llamada después de otro tema - confirmar")
                                actualizar_estado_conversacion(numero_whatsapp, "confirmando_llamada")
                                resultado = generar_confirmacion_llamada(idioma_detectado)
                            else:
                                # Verificar si ahora menciona inmobiliario
                                nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                                
                                if nueva_categoria == "inmobiliario":
                                    actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base = respuesta.get("result", str(respuesta))
                                    resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                                else:
                                    # Si sigue siendo otro tema, responder específicamente sin repetir bienvenida
                                    logger.info("Cliente continúa con otro tema - respuesta directa")
                                    consulta = crear_prompt_para_otro_tema(pregunta_procesada, idioma_detectado, plataforma)
                                    respuesta = qa.invoke({"query": consulta})
                                    resultado_base = respuesta.get("result", str(respuesta))
                                    resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                    actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                        
                        # Si ya finalizó pero escribe de nuevo
                        elif estado_conversacion["estado"] == "finalizado":
                            # Reiniciar conversación
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
                            if intencion == "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado_base = respuesta.get("result", str(respuesta))
                                resultado = resultado_base + "\n\n" + generar_pregunta_seguimiento(idioma_detectado)
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_seguimiento")
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                resultado = generar_saludo_inicial(idioma_detectado)
                        
                        else:
                            # Estado desconocido, reiniciar
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            resultado = generar_saludo_inicial(idioma_detectado)
                    
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
                    
                    idioma_detectado = detectar_idioma(pregunta_procesada, llm)
                    
                    # Lógica de conversación para WhatsApp (sin documentos)
                    if plataforma.lower() == "whatsapp" and numero_whatsapp:
                        estado_conversacion = obtener_estado_conversacion(numero_whatsapp)
                        
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
                            if intencion == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                            elif intencion == "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria y seguimiento
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return agregar_bandera(generar_saludo_inicial(idioma_detectado), idioma_detectado)
                        
                        elif estado_conversacion["estado"] == "esperando_categoria":
                            categoria = detectar_respuesta_categoria(pregunta_procesada)
                            
                            if categoria == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                        
                        elif estado_conversacion["estado"] == "esperando_seguimiento":
                            if detectar_finalizacion_conversacion(pregunta_procesada):
                                if idioma_detectado in ["inglés", "english"]:
                                    resultado_final = "You're welcome! Don't hesitate to contact us if you need anything else. Have a great day! 😊"
                                elif idioma_detectado in ["alemán", "german", "deutsch"]:
                                    resultado_final = "Gern geschehen! Zögern Sie nicht, uns zu kontaktieren, wenn Sie etwas anderes benötigen. Haben Sie einen schönen Tag! 😊"
                                else:
                                    resultado_final = "¡De nada! No dudes en contactarnos si necesitas algo más. ¡Que tengas un buen día! 😊"
                                actualizar_estado_conversacion(numero_whatsapp, "finalizado")
                                return agregar_bandera(resultado_final, idioma_detectado)
                            
                            nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                            if nueva_categoria == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema_finalizado")
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                        
                        elif estado_conversacion["estado"] == "otro_tema_finalizado":
                            nueva_categoria = detectar_respuesta_categoria(pregunta_procesada)
                            if nueva_categoria == "inmobiliario":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                            else:
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                        
                        elif estado_conversacion["estado"] == "finalizado":
                            # Reiniciar conversación
                            actualizar_estado_conversacion(numero_whatsapp, "inicial")
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            if intencion != "inmobiliario_directo":
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return agregar_bandera(generar_saludo_inicial(idioma_detectado), idioma_detectado)
                    
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

# Test básico
if __name__ == "__main__":
    logger.info("🧪 Probando agente...")
    respuesta = ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
    logger.info(f"Respuesta: {respuesta}")
