# agente/cerebro.py

import os
from dotenv import load_dotenv

# Importaciones de LangChain
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Importaciones para la base de conocimiento (RAG)
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Importaciones para las herramientas del agente
from langchain.agents import create_tool_calling_agent, AgentExecutor
from . import herramientas

# --- Variables Globales ---
agente_executor = None
conversaciones = {}

# --- Función de Inicialización Principal ---
def inicializar_agente():
    global agente_executor
    print("Iniciando el Agente de IA Inmobiliario...")
    load_dotenv()

    # 1. Preparar la Base de Conocimiento (Vectorstore)
    print("Cargando documentos de la base de conocimiento...")
    loader = DirectoryLoader('./conocimiento/', glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    documentos = loader.load()

    if not documentos:
        raise ValueError("No se cargaron documentos. Verifica que la carpeta 'conocimiento' no esté vacía y contenga archivos .txt.")

    print("Dividiendo y procesando documentos...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs_divididos = text_splitter.split_documents(documentos)
    
    print("Creando embeddings (representaciones numéricas del texto)...")
    modelo_embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print("Indexando documentos en la base de datos vectorial...")
    vectorstore = FAISS.from_documents(docs_divididos, modelo_embeddings)
    retriever = vectorstore.as_retriever(k=4)
    print("✅ Base de conocimiento preparada y cargada.")

    # 2. Definir la Personalidad y las Instrucciones del Agente
    # ¡AQUÍ ESTÁ LA CORRECCIÓN!
    system_template = """
    Eres un experto y amable asistente virtual para 'Inmobiliaria Terramagna'.
    Tu objetivo es ayudar a los clientes a encontrar información sobre propiedades y resolver sus dudas sobre la empresa.
    
    Instrucción Clave: Responde SIEMPRE en el mismo idioma en el que te escribe el cliente. 
    Puedes comunicarte fluidamente en español, inglés, alemán y ruso.
    
    Utiliza las herramientas disponibles para responder a las preguntas. Basa tus respuestas únicamente en la información recuperada de tus herramientas.
    Sé siempre profesional y servicial.
    """
    
    # 3. Crear el "Cerebro" que usa la memoria y el conocimiento
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 4. Crear las herramientas que el agente puede usar
    tool_list = [herramientas.listar_propiedades_disponibles, retriever.as_tool()]
    
    # 5. Crear el Agente Ejecutor
    agent = create_tool_calling_agent(llm, tool_list, prompt)
    agente_executor = AgentExecutor(agent=agent, tools=tool_list, verbose=True)
    print("✅ Cerebro de 'Inmobiliaria Terramagna' inicializado.")

# --- Función de Ejecución ---
def ejecutar_agente(pregunta, session_id):
    if session_id not in conversaciones:
        conversaciones[session_id] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    memoria = conversaciones[session_id]
    
    resultado = agente_executor.invoke({
        "input": pregunta,
        "chat_history": memoria.chat_memory.messages
    })
    
    memoria.save_context({"input": pregunta}, {"output": resultado["output"]})
    
    return resultado["output"]

