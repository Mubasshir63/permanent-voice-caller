import os
import asyncio
import aiohttp
import requests
import uvicorn
from fastapi import FastAPI
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.groq import GroqLLMService, GroqSTTService
from pipecat.services.google import GoogleTTSService
from pipecat.transports.network.sip_transport import SIPTransport

# 1. Initialize FastAPI to keep Hugging Face Space active
app = FastAPI()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

@app.get("/")
def read_root():
    return {"status": "AI Voice Caller is Live & Listening"}

# 2. Main Pipecat Voice Pipeline Engine
async def run_voice_bot():
    async with aiohttp.ClientSession():
        # Setup the permanent Free SIP digital phone line
        transport = SIPTransport(
            sip_username=os.getenv("SIP_USERNAME"),
            sip_password=os.getenv("SIP_PASSWORD"),
            sip_server="sip.linphone.org",
            port=5060
        )
        
        # Free Tier AI Processing via Groq & Google
        stt = GroqSTTService(api_key=os.getenv("GROQ_API_KEY"), model="whisper-large-v3-turbo")
        llm = GroqLLMService(api_key=os.getenv("GROQ_API_KEY"), model="llama3-8b-8192")
        tts = GoogleTTSService(api_key=os.getenv("GOOGLE_API_KEY"))

        sys_context = OpenAILLMContext(
            messages=[{"role": "system", "content": "You are a professional phone assistant. Speak in short, concise sentences."}],
            tools=[]
        )
        
        pipeline = Pipeline([
            transport.input(),
            stt,
            llm,
            tts,
            transport.output()
        ])

        runner = PipelineRunner()
        print("Starting voice bot engine loop...")
        await runner.run(pipeline)

        # Automatically fire conversation logs to n8n when caller hangs up
        if N8N_WEBHOOK_URL:
            transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in sys_context.messages])
            payload = {
                "event": "call_ended",
                "transcript": transcript,
                "status": "completed"
            }
            try:
                requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                print("Transcript successfully sent to n8n!")
            except Exception as e:
                print(f"n8n webhook failed: {e}")

# Function to run the voice loop in the background of the web server
def start_voice_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_voice_bot())

if __name__ == "__main__":
    # Start the background voice pipeline thread
    import threading
    threading.Thread(target=start_voice_loop, daemon=True).start()
    
    # Run the web server on port 7860 for Hugging Face compatibility
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
