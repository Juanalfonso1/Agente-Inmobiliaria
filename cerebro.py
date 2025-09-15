# cerebro.py - VERSIÓN FINAL OPTIMIZADA

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
        palabras_espanol = ['hola', 'gracias', 'por favor', 'precio', 'casa', 'piso']
        palabras_ingles = ['hello', 'thanks', 'please', 'price', 'house', 'property']
        palabras_aleman = ['hallo', 'danke', 'bitte', 'preis', 'haus', 'wohnung']
        
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

def crear_prompt_optimizado(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea prompt optimizado según idioma y plataforma."""
    
    # Instrucciones base
    if plataforma.lower() == "whatsapp":
        formato_base = "WhatsApp (máx 3900 chars, emojis apropiados, *negritas* importantes)"
    else:
        formato_base = "web (respuesta completa, formato markdown si necesario)"
    
    # Prompts por idioma
    if idioma in ["inglés", "english"]:
        return (
            f"You are a professional, friendly real estate agent. "
            f"Respond in English via {formato_base}. "
            f"Be warm, clear, and helpful. "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            f"Sie sind ein professioneller, freundlicher Immobilienmakler. "
            f"Antworten Sie auf Deutsch via {formato_base}. "
            f"Seien Sie warm, klar und hilfreich. "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español por defecto
        return (
            f"Eres una agente inmobiliaria profesional y amable. "
            f"Responde en español via {formato_base}. "
            f"Sé cálida, clara y útil. "
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
                    
                    # Crear consulta
                    consulta = crear_prompt_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
                    # Ejecutar QA
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
                    
                    consulta = crear_prompt_optimizado(pregunta_procesada, idioma_detectado, plataforma)
                    
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
    """Ejecuta el agente para WhatsApp."""
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