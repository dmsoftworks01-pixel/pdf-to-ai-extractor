import fitz  # PyMuPDF: El motor de extracción ultrarrápido
from fastapi import FastAPI, UploadFile, File, HTTPException
import time

app = FastAPI(
    title="PDF to AI Extractor API",
    description="Convierte facturas, contratos y documentos PDF complejos en texto limpio optimizado para el consumo de LLMs (Agentes de IA).",
    version="1.0.0"
)

@app.get("/")
def home():
    return {"status": "online", "message": "PDF Extractor API activa. Visita /docs para probar el endpoint."}

# Usamos POST porque el cliente "enviará" un archivo pesado a nuestro servidor
@app.post("/api/v1/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    start_time = time.time()
    
    # 1. Validación estricta: Rechazamos automáticamente imágenes o excels para no colgar el servidor
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Error de formato: El archivo subido debe ser estrictamente un documento PDF (.pdf).")
    
    try:
        # 2. Lectura en memoria RAM (Zero-Disk-Write)
        # Leemos el archivo directamente en la memoria sin guardarlo en el disco duro de Render.
        # Esto hace que la API sea 10 veces más rápida y ahorra espacio de almacenamiento.
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        full_text = ""
        total_pages = len(doc)
        
        # 3. Extracción secuencial con marcadores de página
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            # Agregamos separadores de página visuales para que la IA entienda el contexto estructural
            full_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
        doc.close()
        
        # 4. Limpieza intensiva para ahorrar Tokens de IA
        # Eliminamos saltos de línea excesivos y tabulaciones raras que consumen tokens innecesarios en ChatGPT/Claude.
        clean_text = " ".join(full_text.split())
        
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # 5. Respuesta JSON estructurada
        return {
            "success": True,
            "file_name": file.filename,
            "metadata": {
                "total_pages": total_pages,
                "file_size_bytes": len(pdf_bytes),
                "processing_time_ms": process_time_ms
            },
            "ai_ready_text": clean_text
        }
        
    except Exception as e:
        # Captura de errores para evitar que el bot se caiga y devuelva un 500 feo
        raise HTTPException(status_code=500, detail=f"Error interno procesando la estructura del PDF: {str(e)}")