# cerebro_unificado.py - VERSIÓN PARA WEB Y WHATSAPP

import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Variable global del agente
agente_executor = None

def limpiar_texto_whatsapp(texto: str) -> str:
    """Limpia y normaliza texto recibido de WhatsApp."""
    # Remover emojis problemáticos y caracteres especiales
    texto = re.sub(r'[^\w\s\.\?\!¿¡áéíóúñüÁÉÍÓÚÑÜ]', ' ', texto)
    # Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def detectar_idioma(texto: str, llm) -> str:
    """Detecta el idioma del texto usando el modelo LLM."""
    try:
        # PROMPT SÚPER ESTRICTO Y PRECISO - SOLO 3 IDIOMAS
        consulta = (
            "Tu tarea es identificar el idioma de un texto. Debes responder obligatoriamente con una sola palabra de la siguiente lista: "
            "[español, inglés, alemán]. "
            "No añadas puntuación, explicaciones ni ninguna otra palabra. Solo una palabra de la lista. "
            f"Texto a analizar: \"{texto[:200]}\""
        )
        
        response = llm.invoke(consulta)
        idioma = response.content.strip().lower().strip('.,')
        print(f"[INFO] Idioma detectado: {idioma}")
        return idioma
        
    except Exception as e:
        print(f"[WARN] Error detectando idioma: {e}")
        return "español"

def formatear_respuesta_por_plataforma(respuesta: str, plataforma: str = "web") -> str:
    """Formatea la respuesta según la plataforma (web o whatsapp)."""
    if plataforma.lower() == "whatsapp":
        # WhatsApp tiene límite de ~4096 caracteres por mensaje
        MAX_CHARS = 4000
        
        if len(respuesta) <= MAX_CHARS:
            return respuesta
        
        # Si es muy larga, dividir en párrafos y tomar los más importantes
        parrafos = respuesta.split('\n\n')
        respuesta_corta = parrafos[0]
        
        for parrafo in parrafos[1:]:
            if len(respuesta_corta + '\n\n' + parrafo) <= MAX_CHARS:
                respuesta_corta += '\n\n' + parrafo
            else:
                respuesta_corta += '\n\n📱 *Respuesta completa disponible por teléfono o email*'
                break
        
        return respuesta_corta
    else:
        # Para web, devolver respuesta completa sin modificaciones
        return respuesta

def agregar_bandera(respuesta: str, idioma: str) -> str:
    """Agrega bandera según el idioma detectado - SOLO 3 IDIOMAS."""
    # Diccionario simplificado para solo 3 idiomas
    banderas = {
        "español": "🇪🇸",
        "spanish": "🇪🇸",
        "inglés": "🇬🇧",
        "english": "🇬🇧",
        "alemán": "🇩🇪",
        "german": "🇩🇪",
        "deutsch": "🇩🇪"
    }
    
    bandera = banderas.get(idioma.lower(), '🇪🇸')
    return f"{bandera} {respuesta}".strip()

def crear_prompt_multiidioma(pregunta: str, idioma: str, plataforma: str = "web") -> str:
    """Crea el prompt con instrucciones específicas de idioma y plataforma."""
    
    # Instrucciones específicas por plataforma
    if plataforma.lower() == "whatsapp":
        instrucciones_formato = (
            "FORMATO WHATSAPP: Respuesta máximo 4000 caracteres, usa emojis apropiados, "
            "formato claro con *negritas* para palabras importantes, "
            "párrafos cortos separados por líneas en blanco. "
            "Si mencionas precios, usa formato claro con € o $. "
            "Al final incluye una llamada a la acción amigable."
        )
    else:
        instrucciones_formato = (
            "FORMATO WEB: Respuesta completa y detallada, "
            "usa formato markdown si es apropiado, "
            "puedes incluir listas, enlaces y formateo avanzado. "
            "Sé exhaustivo en las explicaciones."
        )
    
    if idioma in ["inglés", "english"]:
        canal = "WhatsApp" if plataforma.lower() == "whatsapp" else "website"
        return (
            f"You are a professional, elegant and very friendly real estate agent responding via {canal}. "
            f"IMPORTANT: You must respond COMPLETELY in English. "
            f"Always respond clearly and in a warm and professional tone. "
            f"{instrucciones_formato} "
            f"Client question: {pregunta}"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        canal = "WhatsApp" if plataforma.lower() == "whatsapp" else "Website"
        return (
            f"Sie sind ein professioneller, eleganter und sehr freundlicher Immobilienmakler der über {canal} antwortet. "
            f"WICHTIG: Sie müssen VOLLSTÄNDIG auf Deutsch antworten. "
            f"Antworten Sie immer klar und in einem warmen und professionellen Ton. "
            f"{instrucciones_formato} "
            f"Kundenfrage: {pregunta}"
        )
    else:  # español por defecto
        canal = "WhatsApp" if plataforma.lower() == "whatsapp" else "web"
        return (
            f"Eres una agente inmobiliaria profesional, elegante y muy amable respondiendo por {canal}. "
            f"IMPORTANTE: Debes responder COMPLETAMENTE en español. "
            f"Responde siempre con claridad y en un tono cálido y profesional. "
            f"{instrucciones_formato} "
            f"Pregunta del cliente: {pregunta}"
        )

def detectar_intencion_urgente(texto: str) -> bool:
    """Detecta si el mensaje requiere respuesta urgente."""
    palabras_urgentes = [
        'urgente', 'emergency', 'notfall', 'rapido', 'quick', 'schnell',
        'ahora', 'now', 'jetzt', 'inmediato', 'immediate', 'sofort'
    ]
    texto_lower = texto.lower()
    return any(palabra in texto_lower for palabra in palabras_urgentes)

def generar_respuesta_fuera_horario(idioma: str) -> str:
    """Genera respuesta automática fuera del horario comercial."""
    if idioma in ["inglés", "english"]:
        return (
            "🇬🇧 Hello! Thank you for contacting us. 🏠\n\n"
            "We're currently outside business hours, but we'll respond to your message first thing tomorrow morning.\n\n"
            "⏰ *Business Hours:* Monday to Friday 9:00-18:00\n\n"
            "For urgent matters, please call: +34 XXX XXX XXX\n\n"
            "Thank you for your patience! 😊"
        )
    elif idioma in ["alemán", "german", "deutsch"]:
        return (
            "🇩🇪 Hallo! Vielen Dank für Ihre Nachricht. 🏠\n\n"
            "Wir sind derzeit außerhalb der Geschäftszeiten, werden aber morgen früh als erstes auf Ihre Nachricht antworten.\n\n"
            "⏰ *Geschäftszeiten:* Montag bis Freitag 9:00-18:00\n\n"
            "Für dringende Angelegenheiten rufen Sie bitte an: +34 XXX XXX XXX\n\n"
            "Vielen Dank für Ihr Verständnis! 😊"
        )
    else:  # español por defecto
        return (
            "🇪🇸 ¡Hola! Gracias por contactarnos. 🏠\n\n"
            "Estamos fuera del horario comercial, pero responderemos tu mensaje a primera hora mañana.\n\n"
            "⏰ *Horario:* Lunes a Viernes 9:00-18:00\n\n"
            "Para asuntos urgentes, puedes llamar: +34 XXX XXX XXX\n\n"
            "¡Gracias por tu paciencia! 😊"
        )

def esta_en_horario_comercial() -> bool:
    """Verifica si estamos en horario comercial (9:00-18:00, L-V)."""
    ahora = datetime.now()
    # Lunes=0, Domingo=6
    if ahora.weekday() >= 5:  # Sábado o Domingo
        return False
    
    hora_actual = ahora.hour
    return 9 <= hora_actual < 18

def inicializar_agente():
    """Inicializa el agente inmobiliario con OpenAI y base de conocimiento."""
    global agente_executor
    
    print("🔄 Iniciando el Agente de IA Inmobiliario Unificado...")
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ Falta OPENAI_API_KEY.")
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
        print(f"[ERROR] Fallo en imports: {mensaje_error}")
        agente_executor = lambda pregunta, **kwargs: f"[ERROR] Librerías faltantes: {mensaje_error}"
        return agente_executor
    
    try:
        # Inicializar LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        print("✅ Modelo OpenAI cargado.")
        
        # Cargar documentos
        documentos = []
        directorio_conocimiento = "conocimiento"
        
        if not os.path.exists(directorio_conocimiento):
            print(f"⚠️ La carpeta '{directorio_conocimiento}' no existe. Creándola...")
            os.makedirs(directorio_conocimiento)
            print("📁 Carpeta creada. Agrega documentos y reinicia el agente.")
        else:
            # Cargar archivos
            tipos_archivo = [
                ("TXT", "*.txt", TextLoader),
                ("DOCX", "*.docx", Docx2txtLoader),
                ("PDF", "*.pdf", PyPDFLoader)
            ]
            
            for tipo, patron, loader_cls in tipos_archivo:
                try:
                    loader_kwargs = {'encoding': 'utf-8'} if loader_cls == TextLoader else {}
                    loader = DirectoryLoader(
                        directorio_conocimiento,
                        glob=patron,
                        loader_cls=loader_cls,
                        loader_kwargs=loader_kwargs,
                        show_progress=False,
                        use_multithreading=False
                    )
                    docs = loader.load()
                    documentos.extend(docs)
                    print(f"📄 {tipo} cargados: {len(docs)} archivos")
                    
                    for doc in docs:
                        filename = os.path.basename(doc.metadata.get('source', 'Desconocido'))
                        content_length = len(doc.page_content)
                        print(f"   ✅ {filename}: {content_length} caracteres")
                        
                except Exception as file_error:
                    print(f"[WARN] Error cargando archivos {tipo}: {file_error}")
        
        if documentos:
            print(f"📚 Procesando {len(documentos)} documentos...")
            
            # Dividir documentos
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            docs_split = splitter.split_documents(documentos)
            
            # Crear vectorstore
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs_split, embeddings)
            retriever = vectorstore.as_retriever()
            
            # Crear cadena QA
            qa = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=retriever,
                chain_type="stuff"
            )
            
            def agente_con_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    # Limpiar pregunta si viene de WhatsApp
                    if plataforma.lower() == "whatsapp":
                        pregunta_limpia = limpiar_texto_whatsapp(pregunta)
                    else:
                        pregunta_limpia = pregunta
                    
                    llm_local = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
                    idioma_detectado = detectar_idioma(pregunta_limpia, llm_local)
                    
                    # Verificar horario comercial SOLO para WhatsApp y mensajes no urgentes
                    if (plataforma.lower() == "whatsapp" and 
                        not esta_en_horario_comercial() and 
                        not detectar_intencion_urgente(pregunta_limpia)):
                        return generar_respuesta_fuera_horario(idioma_detectado)
                    
                    consulta = crear_prompt_multiidioma(pregunta_limpia, idioma_detectado, plataforma)
                    
                    respuesta = qa.invoke({"query": consulta})
                    resultado = respuesta.get("result", str(respuesta))
                    
                    # Formatear según la plataforma
                    resultado_formateado = formatear_respuesta_por_plataforma(resultado, plataforma)
                    
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
                except Exception as qa_error:
                    print(f"[ERROR] Fallo en QA: {qa_error}")
                    return f"⚠️ Lo siento, ocurrió un error procesando tu consulta: {str(qa_error)}"
            
            agente_executor = agente_con_documentos
            
        else:
            print("⚠️ No se encontraron documentos. Usando solo el modelo.")
            
            def agente_sin_documentos(pregunta: str, plataforma: str = "web", numero_whatsapp: str = None):
                try:
                    # Limpiar pregunta si viene de WhatsApp
                    if plataforma.lower() == "whatsapp":
                        pregunta_limpia = limpiar_texto_whatsapp(pregunta)
                    else:
                        pregunta_limpia = pregunta
                    
                    llm_local = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
                    idioma_detectado = detectar_idioma(pregunta_limpia, llm_local)
                    
                    # Verificar horario comercial SOLO para WhatsApp
                    if (plataforma.lower() == "whatsapp" and 
                        not esta_en_horario_comercial() and 
                        not detectar_intencion_urgente(pregunta_limpia)):
                        return generar_respuesta_fuera_horario(idioma_detectado)
                    
                    consulta = crear_prompt_multiidioma(pregunta_limpia, idioma_detectado, plataforma)
                    
                    response = llm_local.invoke(consulta)
                    resultado_formateado = formatear_respuesta_por_plataforma(response.content, plataforma)
                    
                    return agregar_bandera(resultado_formateado, idioma_detectado)
                    
                except Exception as model_error:
                    print(f"[ERROR] Fallo al invocar el modelo: {model_error}")
                    return f"⚠️ Error procesando tu consulta: {str(model_error)}"
            
            agente_executor = agente_sin_documentos
        
        print("✅ Agente unificado inicializado correctamente.")
        return agente_executor
        
    except Exception as init_error:
        mensaje_error = str(init_error)
        print(f"[ERROR] No se pudo inicializar el agente: {mensaje_error}")
        agente_executor = lambda pregunta, **kwargs: f"[ERROR] No se pudo inicializar el agente: {mensaje_error}"
        return agente_executor

# FUNCIONES PÚBLICAS PARA CADA PLATAFORMA

def ejecutar_agente(pregunta: str):
    """Ejecuta el agente para la WEB (función original)."""
    global agente_executor
    
    if agente_executor is None:
        print("🔄 Agente no inicializado, inicializando...")
        inicializar_agente()
    
    if agente_executor is None:
        return "[ERROR] No se pudo inicializar el agente."
    
    try:
        return agente_executor(pregunta, plataforma="web")
    except Exception as exec_error:
        print(f"[ERROR] El agente falló al responder: {exec_error}")
        return f"⚠️ Error ejecutando consulta: {str(exec_error)}"

def ejecutar_agente_whatsapp(pregunta: str, numero_whatsapp: str = None):
    """Ejecuta el agente para WHATSAPP."""
    global agente_executor
    
    if agente_executor is None:
        print("🔄 Agente no inicializado, inicializando...")
        inicializar_agente()
    
    if agente_executor is None:
        return "[ERROR] No se pudo inicializar el agente."
    
    try:
        # Log de la interacción
        print(f"[INFO] Nueva consulta WhatsApp desde {numero_whatsapp}: {pregunta[:100]}...")
        
        respuesta = agente_executor(pregunta, plataforma="whatsapp", numero_whatsapp=numero_whatsapp)
        
        # Log de la respuesta
        print(f"[INFO] Respuesta enviada ({len(respuesta)} chars)")
        
        return respuesta
        
    except Exception as exec_error:
        print(f"[ERROR] El agente falló al responder: {exec_error}")
        return f"⚠️ Error ejecutando consulta: {str(exec_error)}"

# Test básico
if __name__ == "__main__":
    print("🧪 Probando agente unificado...")
    
    # Test WEB
    print("\n--- TEST WEB ---")
    respuesta_web = ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
    print(f"Respuesta WEB: {respuesta_web}")
    
    # Test WhatsApp
    print("\n--- TEST WHATSAPP ---")
    respuesta_whatsapp = ejecutar_agente_whatsapp("¿Cuál es el precio promedio de una casa en Madrid?", "+34600000000")
    print(f"Respuesta WhatsApp: {respuesta_whatsapp}")
