# whatsapp_server.py
import os
import logging
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.rest import Client
from dotenv import load_dotenv
from datetime import datetime
from cerebro import ejecutar_agente, inicializar_agente

load_dotenv()

# Configuración logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("ACccc1d7045cc94f60b4889b45c0d39432")
TWILIO_AUTH_TOKEN = os.getenv("7c3efb74a5c712a71db9aacafecac63f")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# FastAPI app
app = FastAPI(
    title="WhatsApp Bridge",
    version="1.0.0"
)

@app.get("/")
async def health():
    return {"status": "🟢 WhatsApp activo", "twilio": bool(twilio_client)}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None)
):
    logger.info(f"📨 {From}: {Body}")
    try:
        respuesta = ejecutar_agente(Body)
        if not respuesta:
            respuesta = "⚠️ Lo siento, no pude procesar tu mensaje."
        
        if twilio_client:
            twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=respuesta,
                to=From
            )
        return Response(content="", media_type="text/xml")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return Response(content="", media_type="text/xml", status_code=500)

@app.on_event("startup")
async def startup_event():
    inicializar_agente()
    logger.info("✅ Agente inicializado en WhatsApp Bridge")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("whatsapp_server:app", host="0.0.0.0", port=8001, reload=True)
