import os
from dotenv import load_dotenv

# Variable global del agente
agente_executor = None

def inicializar_agente():
    """
    Inicializa el agente inmobiliario con OpenAI y base de conocimiento.
    Maneja errores de configuración, carga de documentos y ejecución.
    """
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
    except Exception as error:
        mensaje_error = str(error)
        print(f"[ERROR] Fallo en imports: {mensaje_error}")
        agente_executor = lambda pregunta: f"[ERROR] Librerías faltantes: {mensaje_error}"
        return agente_executor

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        print("✅ Modelo OpenAI cargado.")

        # Cargar documentos
        documentos = []
        try:
            for tipo, glob, loader_cls in [
                ("TXT", "*.txt", TextLoader),
                ("DOCX", "*.docx", Docx2txtLoader),
                ("PDF", "*.pdf", PyPDFLoader)
            ]:
                loader = DirectoryLoader("conocimiento", glob=glob, loader_cls=loader_cls)
                docs = loader.load()
                documentos.extend(docs)
                print(f"📄 {tipo} cargados: {len(docs)}")
        except Exception as error:
            print(f"[WARN] Error al cargar documentos: {error}")

        # Función para detectar idioma
        def detectar_idioma(texto: str) -> str:
            try:
                consulta = (
                    "Detecta en qué idioma está escrito el siguiente texto y responde con una sola palabra: "
                    "Español, Inglés, Alemán, Ruso, Francés o Italiano.\n"
                    f"Texto: {texto}"
                )
                idioma = llm.invoke(consulta).content.strip().lower()
                return idioma
            except Exception:
                return "español"

        # Función para añadir bandera
        def agregar_bandera(respuesta: str, idioma: str) -> str:
            banderas = {
                "inglés": "🇬🇧",
                "alemán": "🇩🇪",
                "ruso": "🇷🇺",
                "francés": "🇫🇷",
                "italiano": "🇮🇹"
            }
            return f"{banderas.get(idioma, '')} {respuesta}".strip()

        # Si hay documentos, usar vectorstore
        if documentos:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            docs_split = splitter.split_documents(documentos)

            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs_split, embeddings)
            retriever = vectorstore.as_retriever()

            qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, chain_type="stuff")

            def agente_executor_func(pregunta: str):
                try:
                    idioma = detectar_idioma(pregunta)
                    consulta = (
                        f"Eres una agente inmobiliaria profesional, elegante y muy amable.\n"
                        f"Responde siempre con claridad y en un tono cálido y profesional.\n"
                        f"El idioma de tu respuesta debe ser: {idioma}.\n"
                        f"Pregunta del cliente: {pregunta}"
                    )
                    respuesta = qa.run(consulta)
                    return agregar_bandera(respuesta, idioma)
                except Exception as error:
                    return f"[ERROR] Fallo en QA: {error}"

        else:
            # Sin documentos, usar solo el modelo
            def agente_executor_func(pregunta: str):
                try:
                    idioma = detectar_idioma(pregunta)
                    consulta = (
                        f"Eres una agente inmobiliaria profesional, elegante y muy amable.\n"
                        f"Responde siempre con claridad y en un tono cálido y profesional.\n"
                        f"El idioma de tu respuesta debe ser: {idioma}.\n"
                        f"Pregunta del cliente: {pregunta}"
                    )
                    respuesta = llm.invoke(consulta)
                    return agregar_bandera(respuesta.content, idioma)
                except Exception as error:
                    return f"[ERROR] Fallo al invocar el modelo: {error}"

        agente_executor = agente_executor_func
        return agente_executor

    except Exception as error:
        mensaje_error = str(error)
        print(f"[ERROR] No se pudo inicializar el agente: {mensaje_error}")
        agente_executor = lambda pregunta: f"[ERROR] No se pudo inicializar el agente: {mensaje_error}"
        return agente_executor

def ejecutar_agente(pregunta: str):
    """
    Ejecuta el agente con la pregunta dada.
    Si no está inicializado, lo carga.
    """
    global agente_executor
    if agente_executor is None:
        inicializar_agente()

    try:
        return agente_executor(pregunta)
    except Exception as error:
        return f"[ERROR] El agente no pudo responder: {error}"
