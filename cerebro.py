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
    texto_lower = texto.lower()
    
    # Palabras que indican saludo inicial
    saludos = ['hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches', 'hey']
    
    # Palabras que indican intención de propiedades
    inmobiliario = ['alquiler', 'venta', 'casa', 'piso', 'apartamento', 'propiedad', 'inmueble', 
                   'rent', 'sale', 'house', 'apartment', 'property', 'comprar', 'rentar']
    
    # Palabras que indican otros temas
    otros_temas = ['consulta', 'información', 'servicio', 'ayuda', 'contacto', 'vanessa']
    
    # Verificar si contiene palabras inmobiliarias
    if any(palabra in texto_lower for palabra in inmobiliario):
        return "inmobiliario_directo"
    
    # Verificar si menciona otros temas
    if any(palabra in texto_lower for palabra in otros_temas):
        return "otro_tema"
    
    # Si es solo saludo
    if any(saludo in texto_lower for saludo in saludos) and len(texto.split()) <= 3:
        return "saludo_inicial"
    
    # Por defecto, tratar como saludo inicial
    return "saludo_inicial"

def detectar_respuesta_categoria(texto: str) -> str:
    """Detecta si la respuesta es sobre alquileres/ventas u otro tema."""
    texto_lower = texto.lower()
    
    # Palabras que indican interés en propiedades
    palabras_inmobiliario = [
        'alquiler', 'alquilar', 'venta', 'vender', 'comprar', 'casa', 'piso', 
        'apartamento', 'propiedad', 'inmueble', 'vivienda', 'rent', 'rental',
        'sale', 'buy', 'house', 'apartment', 'property', 'si', 'sí', 'yes'
    ]
    
    # Palabras que indican otro tema
    palabras_otro_tema = [
        'otro', 'diferente', 'consulta', 'información', 'servicio', 'no', 'nada'
    ]
    
    if any(palabra in texto_lower for palabra in palabras_inmobiliario):
        return "inmobiliario"
    elif any(palabra in texto_lower for palabra in palabras_otro_tema):
        return "otro_tema"
    else:
        return "inmobiliario"  # Por defecto asumir inmobiliario

def obtener_estado_conversacion(numero_whatsapp: str) -> dict:
    """Obtiene el estado actual de la conversación."""
    if numero_whatsapp not in estados_conversacion:
        estados_conversacion[numero_whatsapp] = {
            "estado": "inicial",
            "ultima_interaccion": datetime.now(),
            "contador_mensajes": 0
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
                        
                        # Si es el primer mensaje o estado inicial
                        if estado_conversacion["estado"] == "inicial":
                            intencion = detectar_intencion_inicial(pregunta_procesada)
                            
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
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                resultado = generar_saludo_inicial(idioma_detectado)
                        
                        # Si estamos esperando que elija categoría
                        elif estado_conversacion["estado"] == "esperando_categoria":
                            categoria = detectar_respuesta_categoria(pregunta_procesada)
                            
                            if categoria == "inmobiliario":
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                                respuesta = qa.invoke({"query": consulta})
                                resultado = respuesta.get("result", str(respuesta))
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema")
                                resultado = generar_respuesta_otro_tema(idioma_detectado)
                        
                        # Si ya estamos en modo inmobiliario
                        elif estado_conversacion["estado"] == "inmobiliario":
                            consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                            respuesta = qa.invoke({"query": consulta})
                            resultado = respuesta.get("result", str(respuesta))
                        
                        # Si está en otro tema
                        elif estado_conversacion["estado"] == "otro_tema":
                            resultado = generar_respuesta_otro_tema(idioma_detectado)
                        
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
                    
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
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
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema")
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "esperando_categoria")
                                return agregar_bandera(generar_saludo_inicial(idioma_detectado), idioma_detectado)
                        
                        elif estado_conversacion["estado"] == "esperando_categoria":
                            categoria = detectar_respuesta_categoria(pregunta_procesada)
                            
                            if categoria == "otro_tema":
                                actualizar_estado_conversacion(numero_whatsapp, "otro_tema")
                                return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                            else:
                                actualizar_estado_conversacion(numero_whatsapp, "inmobiliario")
                                # Continuar con consulta inmobiliaria
                        
                        elif estado_conversacion["estado"] == "otro_tema":
                            return agregar_bandera(generar_respuesta_otro_tema(idioma_detectado), idioma_detectado)
                    
                    consulta = crear_prompt_inmobiliario_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
                    response = llm.invoke(consulta)
                    resultado_formateado = formatear_respuesta_por_plataforma(response.content, plataforma)
                    
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
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
