# cerebro.py - VERSIÓN DEFINITIVA CORREGIDA

import os
from dotenv import load_dotenv

# Variable global del agente
agente_executor = None

def detectar_idioma(texto: str, llm) -> str:
    """Detecta el idioma del texto usando el modelo LLM."""
    try:
        # PROMPT SÚPER ESTRICTO Y PRECISO - SOLO 3 IDIOMAS
        consulta = (
            "Tu tarea es identificar el idioma de un texto. Debes responder obligatoriamente con una sola palabra de la siguiente lista: "
            "[español, inglés, alemán].\n"
            "No añadas puntuación, explicaciones ni ninguna otra palabra. Solo una palabra de la lista.\n"
            f"Texto a analizar: \"{texto[:200]}\""
        )
        
        response = llm.invoke(consulta)
        idioma = response.content.strip().lower().strip('.,')
        print(f"[INFO] Idioma detectado: {idioma}")
        return idioma
        
    except Exception as e:
        print(f"[WARN] Error detectando idioma: {e}")
        return "español"

def obtener_codigo_idioma(idioma: str) -> str:
    """Convierte el idioma detectado a código para el prompt del LLM."""
    codigos_idioma = {
        "español": "español (Spanish)",
        "spanish": "español (Spanish)", 
        "inglés": "inglés (English)",
        "english": "inglés (English)",
        "alemán": "alemán (German)",
        "german": "alemán (German)",
        "deutsch": "alemán (German)"
    }
    return codigos_idioma.get(idioma.lower(), "español (Spanish)")

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

def inicializar_agente():
    """Inicializa el agente inmobiliario con OpenAI y base de conocimiento."""
    global agente_executor
    
    print("🔄 Iniciando el Agente de IA Inmobiliario...")
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ Falta OPENAI_API_KEY.")
        agente_executor = lambda pregunta: "⚠️ Falta configurar OPENAI_API_KEY."
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
        agente_executor = lambda pregunta: f"[ERROR] Librerías faltantes: {mensaje_error}"
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
            
            def agente_con_documentos(pregunta: str):
                try:
                    llm_local = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
                    idioma_detectado = detectar_idioma(pregunta, llm_local)
                    codigo_idioma = obtener_codigo_idioma(idioma_detectado)
                    
                    # PROMPT MEJORADO CON INSTRUCCIONES ESPECÍFICAS DE IDIOMA
                    consulta = (
                        f"Eres una agente inmobiliaria profesional, elegante y muy amable.\n"
                        f"IMPORTANTE: Debes responder OBLIGATORIAMENTE en {codigo_idioma}.\n"
                        f"Si el idioma es inglés, responde completamente en inglés.\n"
                        f"Si el idioma es alemán, responde completamente en alemán.\n"
                        f"Si el idioma es español, responde completamente en español.\n"
                        f"Responde siempre con claridad y en un tono cálido y profesional.\n"
                        f"Pregunta del cliente: {pregunta}"
                    )
                    
                    respuesta = qa.invoke({"query": consulta})
                    resultado = respuesta.get("result", str(respuesta))
                    
                    return agregar_bandera(resultado, idioma_detectado)
                    
                except Exception as qa_error:
                    print(f"[ERROR] Fallo en QA: {qa_error}")
                    return f"⚠️ Lo siento, ocurrió un error procesando tu consulta: {str(qa_error)}"
            
            agente_executor = agente_con_documentos
            
        else:
            print("⚠️ No se encontraron documentos. Usando solo el modelo.")
            
            def agente_sin_documentos(pregunta: str):
                try:
                    llm_local = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
                    idioma_detectado = detectar_idioma(pregunta, llm_local)
                    codigo_idioma = obtener_codigo_idioma(idioma_detectado)
                    
                    # PROMPT MEJORADO CON INSTRUCCIONES ESPECÍFICAS DE IDIOMA
                    consulta = (
                        f"Eres una agente inmobiliaria profesional, elegante y muy amable.\n"
                        f"IMPORTANTE: Debes responder OBLIGATORIAMENTE en {codigo_idioma}.\n"
                        f"Si el idioma es inglés, responde completamente en inglés.\n"
                        f"Si el idioma es alemán, responde completamente en alemán.\n" 
                        f"Si el idioma es español, responde completamente en español.\n"
                        f"Responde siempre con claridad y en un tono cálido y profesional.\n"
                        f"Pregunta del cliente: {pregunta}"
                    )
                    
                    response = llm_local.invoke(consulta)
                    return agregar_bandera(response.content, idioma_detectado)
                    
                except Exception as model_error:
                    print(f"[ERROR] Fallo al invocar el modelo: {model_error}")
                    return f"⚠️ Error procesando tu consulta: {str(model_error)}"
            
            agente_executor = agente_sin_documentos
        
        print("✅ Agente inicializado correctamente.")
        return agente_executor
        
    except Exception as init_error:
        mensaje_error = str(init_error)
        print(f"[ERROR] No se pudo inicializar el agente: {mensaje_error}")
        agente_executor = lambda pregunta: f"[ERROR] No se pudo inicializar el agente: {mensaje_error}"
        return agente_executor

def ejecutar_agente(pregunta: str):
    """Ejecuta el agente con la pregunta dada."""
    global agente_executor
    
    if agente_executor is None:
        print("🔄 Agente no inicializado, inicializando...")
        inicializar_agente()
    
    if agente_executor is None:
        return "[ERROR] No se pudo inicializar el agente."
    
    try:
        return agente_executor(pregunta)
    except Exception as exec_error:
        print(f"[ERROR] El agente falló al responder: {exec_error}")
        return f"⚠️ Error ejecutando consulta: {str(exec_error)}"

# Test básico
if __name__ == "__main__":
    print("🧪 Probando agente...")
    respuesta = ejecutar_agente("¿Cuál es el precio promedio de una casa en Madrid?")
    print(f"Respuesta: {respuesta}")