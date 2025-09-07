import os
from dotenv import load_dotenv

# Variables globales
agente_executor = None

def inicializar_agente():
    """
    Inicializa el Agente de IA Inmobiliario.
    Maneja imports de forma perezosa y captura cualquier error para evitar
    que el servidor caiga en Render.
    """
    global agente_executor
    print("Iniciando el Agente de IA Inmobiliario (versión optimizada)...")

    # Cargar variables de entorno
    load_dotenv()

    # --- Imports diferidos y protegidos ---
    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.prompts import ChatPromptTemplate
        from langchain.memory import ConversationBufferMemory
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain.tools import Tool
    except Exception as e:
        print(f"[ERROR] Falló importando librerías base de LangChain: {e}")
        return None

    # Intentar cargar FAISS
    FAISS = None
    try:
        from langchain_community.vectorstores import FAISS as FAISS_impl
        FAISS = FAISS_impl
    except Exception as e:
        print(f"[WARN] No se pudo importar FAISS desde langchain_community: {e}")
        try:
            from langchain.vectorstores import FAISS as FAISS_impl2
            FAISS = FAISS_impl2
        except Exception as e2:
            print(f"[WARN] No se pudo importar FAISS desde langchain: {e2}")

    # Intentar cargar loaders de documentos
    DirectoryLoader = TextLoader = None
    try:
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
    except Exception as e:
        print(f"[WARN] No se pudo importar loaders desde langchain_community: {e}")
        try:
            from langchain.document_loaders import DirectoryLoader, TextLoader
        except Exception as e2:
            print(f"[WARN] No se pudo importar loaders desde langchain: {e2}")

    # TODO: Aquí puedes añadir la lógica de inicialización real del agente
    # usando FAISS, DirectoryLoader, etc. Solo si FAISS y loaders != None.
    if FAISS is None or DirectoryLoader is None:
        print("[WARN] El agente se inicializó parcialmente (sin FAISS/Loaders).")
    else:
        print("[OK] FAISS y loaders disponibles.")

    # Guardar un “dummy executor” para evitar NoneType errors
    agente_executor = lambda pregunta: "Agente en modo seguro. Respuesta simulada."
    return agente_executor

def ejecutar_agente(pregunta: str):
    """
    Ejecuta el agente con la pregunta dada.
    Si el agente no está inicializado, lo inicializa en modo seguro.
    """
    global agente_executor
    if agente_executor is None:
        inicializar_agente()
    try:
        return agente_executor(pregunta)
    except Exception as e:
        return f"[ERROR] El agente no pudo responder: {e}"
