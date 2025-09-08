import os
from dotenv import load_dotenv

# Variables globales
agente_executor = None

def inicializar_agente():
    """
    Inicializa el Agente de IA Inmobiliario con OpenAI y base de conocimiento.
    Si no hay API Key o algo falla, responde con un modo seguro.
    """
    global agente_executor
    print("🔄 Iniciando el Agente de IA Inmobiliario...")

    # Cargar variables de entorno (.env)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("⚠️ No se encontró OPENAI_API_KEY en el entorno.")
        agente_executor = lambda pregunta: "⚠️ Falta configurar OPENAI_API_KEY."
        return agente_executor

    try:
        # --- Imports protegidos ---
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_community.document_loaders import DirectoryLoader, TextLoader, Docx2txtLoader, PyPDFLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.chains import RetrievalQA
    except Exception as e:
        print(f"[ERROR] Falló importando librerías LangChain: {e}")
        agente_executor = lambda pregunta: f"[ERROR] Librerías faltantes: {e}"
        return agente_executor

    try:
        # --- Cargar modelo ---
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2
        )
        print("✅ Modelo OpenAI cargado correctamente.")

        # --- Cargar documentos ---
        documentos = []
        try:
            loader_txt = DirectoryLoader("conocimiento", glob="*.txt", loader_cls=TextLoader)
            documentos.extend(loader_txt.load())
            loader_docx = DirectoryLoader("conocimiento", glob="*.docx", loader_cls=Docx2txtLoader)
            documentos.extend(loader_docx.load())
            loader_pdf = DirectoryLoader("conocimiento", glob="*.pdf", loader_cls=PyPDFLoader)
            documentos.extend(loader_pdf.load())
            print(f"📂 conocimiento cargados: {len(documentos)}")
        except Exception as e:
            print(f"[WARN] No se pudieron cargar conocimiento {e}")

        if documentos:
            # --- Preparar índice vectorial ---
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            docs_split = splitter.split_documents(documentos)

            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(docs_split, embeddings)

            qa = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=vectorstore.as_retriever(),
                chain_type="stuff"
            )

            def agente_executor_func(pregunta: str):
                try:
                    consulta = f"""
                    Eres una agente inmobiliaria profesional, elegante y muy amable.
                    Responde siempre con claridad y en un tono cálido y profesional.
                    Pregunta del cliente: {pregunta}
                    """
                    return qa.run(consulta)
                except Exception as e:
                    return f"[ERROR] Fallo en QA: {e}"

            agente_executor = agente_executor_func
            return agente_executor

        else:
            # --- Si no hay documentos, responde solo con el LLM ---
            def agente_executor_func(pregunta: str):
                try:
                    consulta = f"""
                    Eres una agente inmobiliaria profesional, elegante y muy amable.
                    Responde siempre con claridad y en un tono cálido y profesional.
                    Pregunta del cliente: {pregunta}
                    """
                    respuesta = llm.invoke(consulta)
                    return respuesta.content
                except Exception as e:
                    return f"[ERROR] Fallo al invocar el modelo: {e}"

            agente_executor = agente_executor_func
            return agente_executor

    except Exception as e:
        print(f"[ERROR] No se pudo inicializar el modelo OpenAI: {e}")
        agente_executor = lambda pregunta: f"[ERROR] No se pudo inicializar el modelo: {e}"
        return agente_executor


def ejecutar_agente(pregunta: str):
    """
    Ejecuta el agente con la pregunta dada.
    Si el agente no está inicializado, lo carga.
    """
    global agente_executor
    if agente_executor is None:
        inicializar_agente()

    try:
        return agente_executor(pregunta)
    except Exception as e:
        return f"[ERROR] El agente no pudo responder: {e}"
