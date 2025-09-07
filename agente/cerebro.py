import os
from dotenv import load_dotenv

# --- Importaciones de LangChain ---
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool

# --- Herramientas personalizadas ---
from agente.herramientas import listar_propiedades_disponibles

# --- Variables globales ---
agente_executor = None
conversaciones = {}

# --- Plantilla de sistema ---
system_template = """
Eres 'Álex', un experto y amable asistente inmobiliario para "Inmobiliaria Terramagna".
Tu objetivo es ayudar a los clientes a encontrar la propiedad perfecta.
Responde siempre en el idioma en el que te habla el cliente (español, inglés o alemán).

Reglas:
1. Usa SIEMPRE tus herramientas para responder a las preguntas.
2. Para preguntas generales sobre la cartera, usa 'listar_propiedades_disponibles'.
3. Para preguntas específicas sobre una propiedad, usa 'busqueda_de_propiedades'.
4. Si no encuentras la información exacta, responde amablemente que no la tienes (sin inventar).
5. Mantén las respuestas concisas y claras.
"""

def inicializar_agente():
    """
    Inicializa el agente inmobiliario.
    """
    global agente_executor
    print("Iniciando el Agente de IA Inmobiliario (versión optimizada)...")

    # --- Cargar variables de entorno ---
    if os.getenv("RENDER") != "true":
        print("Entorno local detectado: cargando .env")
        load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("CRÍTICO: Falta OPENAI_API_KEY. Configúrala en Render o en .env")

    # --- Herramientas iniciales ---
    herramientas = [listar_propiedades_disponibles]

    # --- Cargar documentos ---
    loader = DirectoryLoader(
        './conocimiento/',
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={'encoding': 'utf-8'}
    )
    documentos = loader.load()

    if documentos:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs_divididos = text_splitter.split_documents(documentos)

        print("Creando embeddings con OpenAI...")
        modelo_embeddings = OpenAIEmbeddings(openai_api_key=api_key)

        print("Indexando documentos en FAISS...")
        base_vectorial = FAISS.from_documents(docs_divididos, modelo_embeddings)
        retriever = base_vectorial.as_retriever(search_kwargs={"k": 3})
        print("✅ Base de conocimiento lista.")

        # --- Crear herramienta de búsqueda ---
        herramienta_busqueda = Tool.from_function(
            func=lambda q: retriever.get_relevant_documents(q),
            name="busqueda_de_propiedades",
            description=(
                "Busca y devuelve información detallada sobre propiedades inmobiliarias. "
                "Úsala cuando te pregunten por características, precios o detalles de una propiedad."
            )
        )
        herramientas.append(herramienta_busqueda)
    else:
        print("⚠️ No se encontraron documentos. No se creará la herramienta de búsqueda.")

    # --- Modelo LLM ---
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, herramientas, prompt)
    agente_executor = AgentExecutor(agent=agent, tools=herramientas, verbose=True)
    print("✅ Cerebro inicializado correctamente.")

def obtener_o_crear_memoria_conversacion(session_id: str):
    if session_id not in conversaciones:
        conversaciones[session_id] = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
    return conversaciones[session_id]

def ejecutar_agente(pregunta: str, session_id: str):
    if not agente_executor:
        raise RuntimeError("El agente no ha sido inicializado.")

    memoria = obtener_o_crear_memoria_conversacion(session_id)
    historial = memoria.load_memory_variables({})

    respuesta = agente_executor.invoke({
        "input": pregunta,
        "chat_history": historial.get("chat_history", [])
    })

    memoria.save_context({"input": pregunta}, {"output": respuesta["output"]})
    return respuesta["output"]