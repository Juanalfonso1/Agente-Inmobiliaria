import os
from langchain.tools import tool

@tool
def listar_propiedades_disponibles():
    """
    Devuelve una lista con los nombres de archivo de todas las propiedades disponibles.
    Esta herramienta es útil para responder preguntas generales sobre la cartera,
    como "¿qué propiedades tienes?" o "¿tienes villas en venta?".
    """
    ruta_conocimiento = "./conocimiento"
    try:
        # Lista todos los archivos en la carpeta que terminan en .txt
        archivos = [f for f in os.listdir(ruta_conocimiento) if f.endswith('.txt')]
        if not archivos:
            return "No se encontraron propiedades en la base de datos."
        
        # Formatea la lista para que sea más legible
        lista_formateada = "\n- ".join(archivos)
        return f"Actualmente, estas son las propiedades en cartera:\n- {lista_formateada}"
        
    except FileNotFoundError:
        return "Error: La carpeta de conocimiento no fue encontrada."
    except Exception as e:
        return f"Ha ocurrido un error inesperado al listar las propiedades: {e}"