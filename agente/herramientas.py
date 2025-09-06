# agente/herramientas.py - Aquí definimos las habilidades especiales del agente.

import os
from langchain.tools import tool

@tool
def listar_propiedades_disponibles():
    """
    Útil para obtener una lista de todas las propiedades disponibles en cartera.
    No recibe ningún argumento.
    Devuelve un resumen de los inmuebles disponibles.
    """
    print(">>> USANDO HERRAMIENTA: listar_propiedades_disponibles")
    
    ruta_conocimiento = './conocimiento'
    try:
        archivos = os.listdir(ruta_conocimiento)
        # Filtramos para asegurarnos de que solo cogemos los archivos .txt
        propiedades_txt = [archivo for archivo in archivos if archivo.endswith('.txt')]
        
        if not propiedades_txt:
            return "Actualmente no hay ninguna propiedad en la base de datos."
            
        # Limpiamos los nombres de los archivos para que sean más legibles
        nombres_limpios = [nombre.replace('.txt', '').replace('_', ' ') for nombre in propiedades_txt]
        
        return f"Claro, aquí tienes un resumen de las propiedades en cartera:\n- " + "\n- ".join(nombres_limpios)

    except FileNotFoundError:
        return "No se ha encontrado la carpeta de conocimiento. No puedo listar las propiedades."
    except Exception as e:
        return f"Ha ocurrido un error al intentar listar las propiedades: {e}"
