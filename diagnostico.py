# diagnostico.py - Script para identificar problemas

import os
import sys
from pathlib import Path

def verificar_estructura():
    """Verifica la estructura del proyecto."""
    print("🔍 DIAGNÓSTICO DEL PROYECTO")
    print("=" * 50)
    
    # Verificar archivos principales
    archivos_requeridos = ['cerebro.py', 'main.py', 'requirements.txt', '.env']
    
    print("📁 Estructura de archivos:")
    for archivo in archivos_requeridos:
        existe = os.path.exists(archivo)
        estado = "✅" if existe else "❌"
        print(f"   {estado} {archivo}")
    
    # Verificar directorio conocimiento
    directorio_conocimiento = "conocimiento"
    existe_dir = os.path.exists(directorio_conocimiento)
    print(f"   {'✅' if existe_dir else '❌'} {directorio_conocimiento}/")
    
    if existe_dir:
        archivos_conocimiento = list(Path(directorio_conocimiento).glob("*.*"))
        print(f"       📄 Archivos encontrados: {len(archivos_conocimiento)}")
        for archivo in archivos_conocimiento:
            print(f"          - {archivo.name}")
    
    return all(os.path.exists(archivo) for archivo in archivos_requeridos)

def verificar_variables_entorno():
    """Verifica las variables de entorno."""
    print("\n🔑 Variables de entorno:")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            print(f"   ✅ OPENAI_API_KEY configurada (longitud: {len(openai_key)})")
            return True
        else:
            print("   ❌ OPENAI_API_KEY no encontrada")
            return False
            
    except ImportError:
        print("   ❌ python-dotenv no está instalado")
        return False

def verificar_dependencias():
    """Verifica que las librerías estén instaladas."""
    print("\n📦 Dependencias:")
    
    dependencias = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('python-dotenv', 'dotenv'),
        ('langchain-core', 'langchain_core'),
        ('langchain-community', 'langchain_community'), 
        ('langchain-openai', 'langchain_openai'),
        ('faiss-cpu', 'faiss')
    ]
    
    todas_instaladas = True
    
    for paquete, modulo in dependencias:
        try:
            __import__(modulo.replace('-', '_'))
            print(f"   ✅ {paquete}")
        except ImportError:
            print(f"   ❌ {paquete} - NO INSTALADO")
            todas_instaladas = False
    
    return todas_instaladas

def probar_cerebro():
    """Prueba el módulo cerebro directamente."""
    print("\n🧠 Probando cerebro.py:")
    
    try:
        import cerebro
        print("   ✅ cerebro.py importado correctamente")
        
        # Intentar inicializar
        resultado = cerebro.inicializar_agente()
        if resultado:
            print("   ✅ Agente inicializado correctamente")
            
            # Hacer una pregunta de prueba
            respuesta = cerebro.ejecutar_agente("Hola, ¿funcionas?")
            print(f"   ✅ Respuesta de prueba: {respuesta[:100]}...")
            return True
        else:
            print("   ❌ El agente no se inicializó")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en cerebro.py: {str(e)}")
        return False

def probar_main():
    """Prueba el módulo main."""
    print("\n🚀 Probando main.py:")
    
    try:
        # Cambiar al directorio del script
        sys.path.insert(0, os.getcwd())
        
        import main
        print("   ✅ main.py importado correctamente")
        
        # Verificar que FastAPI se creó
        if hasattr(main, 'app'):
            print("   ✅ Aplicación FastAPI creada")
            return True
        else:
            print("   ❌ No se encontró la aplicación FastAPI")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en main.py: {str(e)}")
        return False

def mostrar_solucion(estructura_ok, env_ok, deps_ok, cerebro_ok, main_ok):
    """Muestra los pasos de solución basados en los problemas encontrados."""
    print("\n" + "=" * 50)
    print("🔧 PLAN DE SOLUCIÓN")
    print("=" * 50)
    
    if not estructura_ok:
        print("1. ❌ Estructura de archivos incompleta:")
        print("   - Asegúrate de que todos los archivos estén presentes")
        print("   - Crea la carpeta 'conocimiento' si no existe")
        print("   - Verifica que los nombres de archivo sean correctos")
    
    if not env_ok:
        print("2. ❌ Variables de entorno:")
        print("   - Crea o verifica el archivo .env")
        print("   - Agrega: OPENAI_API_KEY=tu_clave_aqui")
        print("   - Instala: pip install python-dotenv")
    
    if not deps_ok:
        print("3. ❌ Dependencias faltantes:")
        print("   - Ejecuta: pip install -r requirements.txt")
        print("   - O instala manualmente las librerías faltantes")
    
    if not cerebro_ok:
        print("4. ❌ Problema en cerebro.py:")
        print("   - Reemplaza cerebro.py con la versión corregida")
        print("   - Verifica la configuración de OpenAI")
    
    if not main_ok:
        print("5. ❌ Problema en main.py:")
        print("   - Reemplaza main.py con la versión corregida")
        print("   - Verifica imports y configuración")
    
    if all([estructura_ok, env_ok, deps_ok, cerebro_ok, main_ok]):
        print("✅ DIAGNÓSTICO: Todo parece estar correcto!")
        print("\nPara iniciar el servidor:")
        print("   python main.py")
        print("\nO alternativamente:")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

def main():
    """Función principal de diagnóstico."""
    estructura_ok = verificar_estructura()
    env_ok = verificar_variables_entorno()
    deps_ok = verificar_dependencias() 
    cerebro_ok = probar_cerebro()
    main_ok = probar_main()
    
    mostrar_solucion(estructura_ok, env_ok, deps_ok, cerebro_ok, main_ok)

if __name__ == "__main__":
    main()