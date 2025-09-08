#!/usr/bin/env python3
# fix_encoding.py - Script para verificar y corregir encoding de archivos

import os
import chardet
from pathlib import Path

def detect_and_convert_encoding(file_path):
    """Detecta el encoding de un archivo y lo convierte a UTF-8 si es necesario."""
    
    try:
        # Leer el archivo en modo binario para detectar encoding
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            
        # Detectar encoding
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']
        
        print(f"📄 {file_path.name}")
        print(f"   Encoding detectado: {encoding} (confianza: {confidence:.2f})")
        
        if encoding and encoding.lower() != 'utf-8':
            # Leer con el encoding detectado
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                
                # Escribir de nuevo en UTF-8
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                print(f"   ✅ Convertido de {encoding} a UTF-8")
                
            except Exception as e:
                print(f"   ❌ Error al convertir: {e}")
                
        elif encoding and encoding.lower() == 'utf-8':
            print(f"   ✅ Ya está en UTF-8")
        else:
            print(f"   ⚠️ No se pudo detectar el encoding")
            
    except Exception as e:
        print(f"   ❌ Error procesando archivo: {e}")

def main():
    """Función principal para procesar todos los archivos."""
    
    print("🔧 REPARADOR DE ENCODING DE ARCHIVOS")
    print("=" * 50)
    
    conocimiento_path = Path("conocimiento")
    
    if not conocimiento_path.exists():
        print("❌ La carpeta 'conocimiento' no existe.")
        return
    
    # Buscar todos los archivos de texto
    txt_files = list(conocimiento_path.glob("*.txt"))
    
    if not txt_files:
        print("⚠️ No se encontraron archivos .txt en la carpeta conocimiento")
        return
    
    print(f"📚 Encontrados {len(txt_files)} archivos .txt")
    print("-" * 50)
    
    for txt_file in txt_files:
        detect_and_convert_encoding(txt_file)
        print()
    
    print("=" * 50)
    print("🏁 Proceso completado")
    
    # Ahora intentar cargar con langchain para verificar
    print("\n🧪 Verificando carga con LangChain...")
    
    try:
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        
        loader = DirectoryLoader("conocimiento", glob="*.txt", loader_cls=TextLoader)
        docs = loader.load()
        
        print(f"✅ LangChain cargó {len(docs)} documentos correctamente")
        
        for i, doc in enumerate(docs):
            filename = os.path.basename(doc.metadata.get('source', 'Desconocido'))
            content_length = len(doc.page_content)
            print(f"   📄 {filename}: {content_length} caracteres")
            
    except Exception as e:
        print(f"❌ Error verificando con LangChain: {e}")

if __name__ == "__main__":
    main()