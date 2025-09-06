import os
from dotenv import load_dotenv

# Importaciones de LangChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.retrieval import create_retrieval_tool

# Importación de las herramientas personalizadas
from agente.herramientas import listar_propiedades_disponibles

# --- Variables Globales ---
# Usamos un diccionario para que Render pueda manejar el estado
# de la aplicación de forma segura.
app_state = {}

def inicializar_agente():
    """
    Prepara todo lo necesario para que el agente funcione.
    Se ejecuta una sola vez al iniciar el servidor.
    """
    print("Iniciando el Agente de IA Inmobiliario (v2)...")

    # Carga la API Key de OpenAI de forma segura
    if os.getenv("RENDER") != "true":
        load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la API Key de OpenAI.")

    # Carga los documentos de conocimiento
    loader = DirectoryLoader('./conocimiento/', glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    documentos = loader.load()
    
    # Prepara las herramientas que usará el agente
    herramientas = [listar_propiedades_disponibles]

    if documentos:
        print(f"Se encontraron {len(documentos)} documento(s). Procesando...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs_divididos = text_splitter.split_documents(documentos)
        
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        vectorstore = FAISS.from_documents(docs_divididos, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Crea la herramienta de búsqueda y la añade a la lista
        herramienta_busqueda = create_retrieval_tool(
            retriever,
            "busqueda_de_propiedades",
            "Busca y devuelve información detallada sobre propiedades específicas. Úsala cuando te pregunten por detalles de una propiedad."
        )
        herramientas.append(herramienta_busqueda)
        print("✅ Base de conocimiento cargada y lista.")
    else:
        print("⚠️  ADVERTENCIA: No se encontraron documentos en la carpeta 'conocimiento'.")

    # Configura el modelo de lenguaje (el "cerebro")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)

    # Define la personalidad y las instrucciones del agente
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres 'Álex', un experto asistente inmobiliario para "Inmobiliaria Terramagna".
        Tu objetivo es ayudar a los clientes a encontrar la propiedad perfecta.
        Eres multilingüe y debes responder siempre en el mismo idioma en el que te pregunta el cliente (español, inglés o alemán).
        
        Reglas:
        - Para preguntas generales sobre la cartera, usa la herramienta 'listar_propiedades_disponibles'.
        - Para preguntas específicas sobre una propiedad, usa la herramienta 'busqueda_de_propiedades'.
        - Si no encuentras la información, responde amablemente que no tienes ese dato. Nunca inventes información.
        """),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Construye el agente ejecutor
    agent = create_tool_calling_agent(llm, herramientas, prompt)
    agente_executor = AgentExecutor(agent=agent, tools=herramientas, verbose=True)
    
    # Guarda el agente y la memoria en el estado de la aplicación
    app_state['agente_executor'] = agente_executor
    app_state['conversaciones'] = {}
    print("✅ Cerebro del agente inicializado y listo.")

def ejecutar_agente(pregunta: str, session_id: str):
    """
    Ejecuta el agente con la pregunta del usuario y gestiona la memoria.
    """
    agente_executor = app_state.get('agente_executor')
    if not agente_executor:
        raise RuntimeError("El agente no ha sido inicializado.")

    conversaciones = app_state.get('conversaciones', {})
    if session_id not in conversaciones:
        conversaciones[session_id] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    memoria = conversaciones[session_id]
    historial = memoria.load_memory_variables({})

    respuesta = agente_executor.invoke({
        "input": pregunta,
        "chat_history": historial.get("chat_history", [])
    })

    memoria.save_context({"input": pregunta}, {"output": respuesta["output"]})

    return respuesta["output"]