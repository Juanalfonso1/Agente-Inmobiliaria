# cerebro_unificado_optimizado.py - VERSIÓN OPTIMIZADA PARA WEB Y WHATSAPP

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

def limpiar_texto_whatsapp(texto: str) -> str:
    """Limpia y normaliza texto de WhatsApp de forma más eficiente."""
    if not texto:
        return ""
    
    # Remover emojis y caracteres especiales, mantener texto básico
    texto_limpio = re.sub(r'[^\w\s.?!¿¡áéíóúñüÁÉÍÓÚÑÜ,:]', ' ', texto)
    # Normalizar espacios múltiples
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    return texto_limpio[:500]  # Limitar longitud para eficiencia

def detectar_idioma_simple(texto: str) -> str:
    """Detección rápida de idioma sin usar LLM para casos obvios."""
    texto_lower = texto.lower()
    
    # Palabras clave en español
    palabras_espanol = ['hola', 'gracias', 'por favor', 'precio', 'casa', 'piso', 'inmueble']
    # Palabras clave en inglés  
    palabras_ingles = ['hello', 'thanks', 'please', 'price', 'house', 'property', 'apartment']
    # Palabras clave en alemán
    palabras_aleman = ['hallo', 'danke', 'bitte', 'preis', 'haus', 'wohnung', 'immobilie']
    
    # Contar coincidencias
    score_es = sum(1 for palabra in palabras_espanol if palabra in texto_lower)
    score_en = sum(1 for palabra in palabras_ingles if palabra in texto_lower) 
    score_de = sum(1 for palabra in palabras_aleman if palabra in texto_lower)
    
    if score_es >= score_en and score_es >= score_de:
        return "español"
    elif score_en >= score_de:
        return "inglés"
    else:
        return "alemán"

def detectar_idioma(texto: str, llm) -> str:
    """Detecta idioma usando método híbrido: simple primero, LLM si es necesario."""
    try:
        # Primero, detección simple y rápida
        idioma_simple = detectar_idioma_simple(texto)
        
        # Si el texto es corto o la detección simple es confiable, usar eso
        if len(texto) < 50 or any(palabra in texto.lower() 
                                for palabra in ['hola', 'hello', 'hallo', 'gracias', 'thanks', 'danke']):
            logger.info(f"Idioma detectado (simple): {idioma_simple}")
            return idioma_simple
        
        # Solo usar LLM para casos ambiguos
        consulta = (
            "Identifica el idioma del siguiente texto. Responde SOLO con: español, inglés o alemán. "
            f"Texto: \"{texto[:200]}\""
        )
        
        response = llm.invoke(consulta)
        idioma_llm = response.content.strip().lower().replace('.', '')
        
        # Validar respuesta del LLM
        idiomas_validos = ['español', 'inglés', 'alemán', 'spanish', 'english', 'german']
        if idioma_llm in idiomas_validos:
            logger.info(f"Idioma detectado (LLM): {idioma_llm}")
            return idioma_llm
        else:
            logger.warning(f"LLM devolvió idioma inválido: {idioma_llm}, usando detección simple")
            return idioma_simple
            
    except Exception as e:
        logger.warning(f"Error detectando idioma: {e}, usando español por defecto")
        return "español"

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
        for i, parrafo in enumerate(parrafos[1:], 1):
            nueva_longitud = len(respuesta_corta + '\n\n' + parrafo)
            if nueva_longitud <= MAX_CHARS - 100:  # Margen para mensaje final
                respuesta_corta += '\n\n' + parrafo
            else:
                respuesta_corta += '\n\n📱 *Respuesta completa disponible llamando al teléfono*'
                break
        
        return respuesta_corta
    else:
        # Web: respuesta completa sin limitaciones
        return respuesta

def agregar_bandera(respuesta: str, idioma: str) -> str:
    """Agrega bandera según idioma de forma más eficiente."""
    banderas = {
        "español": "🇪🇸", "spanish": "🇪🇸",
        "inglés": "🇬🇧", "english": "🇬🇧", 
        "alemán": "🇩🇪", "german": "🇩🇪", "deutsch": "🇩🇪"
    }
    
    bandera = banderas.get(idioma.lower(), '🇪🇸')
    return f"{bandera} {respuesta}".strip()

def crear_prompt_multiidioma_optimizado(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea prompt optimizado con menos tokens y más efectivo."""
    
    # Instrucciones base más concisas
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes, párrafos cortos)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    # Prompts más concisos por idioma
    if idioma in ["inglés", "english"]:
        return (
            f"You are a professional, friendly real estate agent. "
            f"Respond in English via {formato_base}. "
            f"Be warm, clear, and helpful. "
            f"Client: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind ein professioneller, freundlicher Immobilienmakler. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, klar und hilfreich. "
            f"Kunde: {pregunta}"
        )
    else:  # español
        return (
            f"Eres una agente inmobiliaria profesional y amable. "
            f"Responde en español via {formato_base}. "
            f"Sé cálida, clara y útil. "
            f"Cliente: {pregunta}"
        )

def esta_en_horario_comercial() -> bool:
    """Verificación rápida de horario comercial."""
    ahora = datetime.now()
    return ahora.weekday() < 5 and 9 <= ahora.hour < 18  # L-V 9-18h

def generar_respuesta_fuera_horario(idioma: str) -> str:
    """Respuesta fuera de horario más concisa."""
    if idioma in ["inglés", "english"]:
        return (
            "🇬🇧 Hello! We're outside business hours (Mon-Fri 9-18h). "
            "We'll respond first thing tomorrow morning! "
            "For urgent matters: +34 XXX XXX XXX 📞"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            "🇩🇪 Hallo! Wir sind außerhalb der Geschäftszeiten (Mo-Fr 9-18h). "
            "Wir antworten morgen früh! "
            "Dringend: +34 XXX XXX XXX 📞"
        )
    else:
        return (
            "🇪🇸 ¡Hola! Estamos fuera del horario (L-V 9-18h). "
            "Responderemos mañana temprano! "
            "Para urgencias: +34 XXX XXX XXX 📞"
        )

def inicializar_agente():
    """Inicialización optimizada del agente."""
    global agente_executor
    
    logger.info("🔄 Inicializando Agente Inmobiliario...")
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY no configurada")
        agente_executor = lambda pregunta, **kwargs: "⚠️ API Key de OpenAI no configurada"
        return agente_executor
    
    try:
        # Imports con manejo de errores específico
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_community.document_loaders import DirectoryLoader, TextLoader, Docx2txtLoader, PyPDFLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.chains import RetrievalQA
        
    except ImportError as error:
        logger.error(f"❌ Error importando librerías: {error}")
        agente_executor = lambda pregunta, **kwargs: f"❌ Librerías faltantes: {error}"
        return agente_executor
    
    try:
        # Inicializar LLM con configuración optimizada
        llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.1,  # Más consistente
            max_tokens=2000   # Controlar longitud de respuesta
        )
        logger.info("✅ OpenAI configurado")
        
        # Cargar documentos de manera más eficiente
        documentos = []
        directorio_conocimiento = "conocimiento"
        
        if not os.path.exists(directorio_conocimiento):
            logger.warning(f"📁 Creando directorio {directorio_conocimiento}")
            os.makedirs(directorio_conocimiento)
        
        # Cargar archivos con mejor manejo de errores
        loaders_config = [
            ("TXT", "*.txt", TextLoader, {'encoding': 'utf-8'}),
            ("DOCX", "*.docx", Docx2txtLoader, {}),
            ("PDF", "*.pdf", PyPDFLoader, {})
        ]
        
        for tipo, patron, loader_cls, kwargs in loaders_config:
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
        
        # Crear agente con o sin documentos
        if documentos:
            logger.info(f"📚 Procesando {len(documentos)} documentos...")
            
            # Configuración optimizada del text splitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,    # Más pequeño para mejor relevancia
                chunk_overlap=100  # Menos overlap
            )
            docs_split = splitter.split_documents(documentos)
            
            # Crear vectorstore
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs_split, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Top 3 chunks
           # Crear cadena QA optimizada
            qa = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=retriever,
                chain_type="stuff",
                return_source_documents=False  # Más eficiente
            )
            
            def agente_con_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    # Limpiar pregunta si viene de WhatsApp
                    pregunta_procesada = limpiar_texto_whatsapp(pregunta) if plataforma.lower() == "whatsapp" else pregunta
                    
                    if not pregunta_procesada.strip():
                        return "No pude entender tu mensaje. ¿Podrías reformularlo?"
                    
                    # Detección rápida de idioma
                    idioma_detectado = detectar_idioma(pregunta_procesada, llm)
                    
                    # Control de horario solo para WhatsApp
                    if (plataforma.lower() == "whatsapp" and 
                        not esta_en_horario_comercial() and 
                        not any(urgente in pregunta_procesada.lower() 
                               for urgente in ['urgente', 'emergency', 'notfall'])):
                        return generar_respuesta_fuera_horario(idioma_detectado)
                    
                    # Crear consulta optimizada
                    consulta = crear_prompt_multiidioma_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
                    # Ejecutar QA
                    respuesta = qa.invoke({"query": consulta})
                    resultado = respuesta.get("result", str(respuesta))
                    
                    # Formatear según plataforma
                    resultado_formateado = formatear_respuesta_por_plataforma(resultado, plataforma)
                    
                    # Agregar bandera y devolver
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
                except Exception as e:
                    logger.error(f"Error en agente con documentos: {e}")
                    return "Error procesando consulta. Intenta nuevamente."
            
            agente_executor = agente_con_documentos
            logger.info("Agente con documentos inicializado")
            
        else:
            # Agente sin documentos - solo LLM
            logger.info("Sin documentos, usando solo LLM")
            
            def agente_sin_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    pregunta_procesada = limpiar_texto_whatsapp(pregunta) if plataforma.lower() == "whatsapp" else pregunta
                    
                    if not pregunta_procesada.strip():
                        return "Mensaje vacío. ¿Podrías escribir tu consulta?"
                    
                    idioma_detectado = detectar_idioma(pregunta_procesada, llm)
                    
                    if (plataforma.lower() == "whatsapp" and 
                        not esta_en_horario_comercial() and
                        not any(urgente in pregunta_procesada.lower() 
                               for urgente in ['urgente', 'emergency', 'notfall'])):
                        return generar_respuesta_fuera_horario(idioma_detectado)
                    
                    consulta = crear_prompt_multiidioma_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
                    response = llm.invoke(consulta)
                    resultado_formateado = formatear_respuesta_por_plataforma(response.content, plataforma)
                    
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
                except Exception as e:
                    logger.error(f"Error en agente sin documentos: {e}")
                    return "Error procesando consulta. Intenta más tarde."
            
            agente_executor = agente_sin_documentos
            logger.info("Agente sin documentos inicializado")
        
        logger.info("Agente inmobiliario listo")
        return agente_executor
        
    except Exception as e:
        logger.error(f"Error crítico inicializando agente: {e}")
        agente_executor = lambda pregunta, **kwargs: f"Error del sistema: {str(e)}"
        return agente_executor 
