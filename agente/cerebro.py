import os
from dotenv import load_dotenv

# Variables globales
agente_executor = None


def inicializar_agente():
    """
    Inicializa el Agente de IA Inmobiliario con OpenAI.
    Si no hay API Key o algo falla, crea un modo seguro con mensaje claro.
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

    # --- Imports diferidos y protegidos ---
    try:
        from langchain_openai import ChatOpenAI
    except Exception as e:
        print(f"[ERROR] Falló importando langchain_openai: {e}")
        agente_executor = lambda pregunta: f"[ERROR] Librería langchain_openai no disponible: {e}"
        return agente_executor

    # --- Crear LLM real con OpenAI ---
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        print("✅ Modelo OpenAI cargado correctamente.")

        def agente_executor_func(pregunta: str):
            """
            Ejecuta el LLM con una pregunta y devuelve la respuesta.
            """
            try:
                respuesta = llm.invoke(pregunta)
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
