"""
start_debug.py
---------------
Script de arranque de diagnóstico para Render.
Verifica variables de entorno críticas, intenta importar la app
y muestra errores detallados en los logs.
"""

import os
import sys
import traceback
import time

# --- Variables de entorno críticas ---
REQUIRED_ENV_VARS = ["OPENAI_API_KEY"]

def check_env_vars():
    print("🔍 Verificando variables de entorno críticas...")
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
            print(f"⚠️  Falta la variable de entorno: {var}")
        else:
            print(f"✅ {var} configurada correctamente")
    if missing:
        print("❌ ERROR: Variables de entorno faltantes. "
              "Configúralas en el dashboard de Render (Environment).")
        # No salimos aún para permitir seguir con debug
    print("")

def try_import_app():
    print("🔍 Intentando importar main.app ...")
    try:
        from main import app
        print("✅ Importación exitosa: main.app encontrado.")
        return True
    except Exception:
        print("❌ ERROR al importar main.app")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando start_debug.py (modo diagnóstico Render)\n")

    check_env_vars()
    success = try_import_app()

    if success:
        print("\nManteniendo el proceso vivo para inspección de logs...")
        # Mantiene el contenedor activo, Render mostrará los logs
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("⏹️ Proceso detenido manualmente")
    else:
        print("\n⏹️ Finalizando con código de error 1.")
        sys.exit(1)
