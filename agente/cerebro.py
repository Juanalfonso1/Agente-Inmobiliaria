import os
from dotenv import load_dotenv

# --- Importaciones de LangChain (Cambiamos el modelo de embeddings) ---
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools.retrieval import create_retrieval_tool

# --- Importación de las Herramientas Personalizadas ---
from agente.herramientas import listar_propiedades_disponibles

# --- Variables Globales ---
agente_executor = None
conversaciones = {}

# --- Plantilla de Sistema para la Personalidad del Agente ---
system_template = """
Eres 'Álex', un experto y amable asistente inmobiliario para "Inmobiliaria Terramagna".
Tu objetivo es ayudar a los clientes a encontrar la propiedad perfecta.
Eres multilingüe y debes responder siempre en el mismo idioma en el que te pregunta el cliente (español, inglés o alemán).

Reglas de comportamiento:
1.  Usa SIEMPRE tus herramientas para responder a las preguntas.
2.  Para preguntas generales sobre la cartera ("qué tienes", "muéstrame villas", etc.), usa la herramienta 'listar_propiedades_disponibles'.
3.  Para preguntas específicas sobre una propiedad, usa la herramienta 'busqueda_de_propiedades'.
4.  Si no encuentras la información exacta en tus herramientas, responde amablemente que no tienes esa información, pero nunca te la inventes.
5.  Mantén las respuestas concisas y directas al grano.
"""

def inicializar_agente():
    """
    Esta función prepara todo lo necesario para que el agente funcione.
    Se ejecuta una sola vez al iniciar el servidor.
    """
    global agente_executor
    print("Iniciando el Agente de IA Inmobiliario (Versión Optimizada)...")

    # 1. Cargar las variables de entorno (API Key de OpenAI)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la API Key de OpenAI. Asegúrate de que está en el archivo .env")

    # 2. Cargar los documentos de la base de conocimiento
    print("Cargando documentos de la base de conocimiento...")
    loader = DirectoryLoader('./conocimiento/', glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    documentos = loader.load()
    if not documentos:
        raise ValueError("No se cargaron documentos. Verifica que la carpeta 'conocimiento' no esté vacía y contenga archivos .txt.")

    # 3. Dividir los documentos en trozos más pequeños
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs_divididos = text_splitter.split_documents(documentos)

    # 4. Crear los embeddings usando la API de OpenAI (¡Esta es la optimización!)
    print("Creando embeddings con la API de OpenAI...")
    # Este objeto no carga un modelo pesado, solo se prepara para llamar a la API de OpenAI.
    modelo_embeddings = OpenAIEmbeddings(api_key=api_key)

    # 5. Crear la base de datos vectorial e indexar los documentos
    print("Indexando documentos...")
    base_de_datos_vectorial = FAISS.from_documents(docs_divididos, modelo_embeddings)
    retriever = base_de_datos_vectorial.as_retriever(search_kwargs={"k": 3})
    print("✅ Base de conocimiento preparada y cargada.")

    # 6. Definir las herramientas que el agente podrá usar
    herramienta_busqueda_propiedades = create_retrieval_tool(
        retriever,
        "busqueda_de_propiedades",
        "Busca y devuelve información detallada sobre propiedades inmobiliarias específicas. Úsala cuando te pregunten por características, precios o detalles de una propiedad."
    )
    herramienta_listar_propiedades = listar_propiedades_disponibles

    herramientas = [herramienta_busqueda_propiedades, herramienta_listar_propiedades]

    # 7. Crear el cerebro del agente (Modelo de Lenguaje)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)

    # 8. Crear el prompt (las instrucciones del agente)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # 9. Construir el agente ejecutor
    agent = create_tool_calling_agent(llm, herramientas, prompt)
    agente_executor = AgentExecutor(agent=agent, tools=herramientas, verbose=True)
    print("✅ Cerebro del agente inmobiliario inicializado.")

def obtener_o_crear_memoria_conversacion(session_id: str):
    """Gestiona la memoria para cada conversación."""
    if session_id not in conversaciones:
        conversaciones[session_id] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return conversaciones[session_id]

def ejecutar_agente(pregunta: str, session_id: str):
    """Ejecuta el agente con la pregunta y el historial de conversación."""
    if not agente_executor:
        raise RuntimeError("El agente no ha sido inicializado. Llama a 'inicializar_agente()' al iniciar la aplicación.")

    memoria = obtener_o_crear_memoria_conversacion(session_id)
    historial = memoria.load_memory_variables({})

    respuesta = agente_executor.invoke({
        "input": pregunta,
        "chat_history": historial.get("chat_history", [])
    })

    memoria.save_context({"input": pregunta}, {"output": respuesta["output"]})

    return respuesta["output"]