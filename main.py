import os
import asyncio
import aiohttp
import requests
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.groq import GroqLLMService, GroqSTTService
from pipecat.services.google import GoogleTTSService
from pipecat.transports.network.sip_transport import SIPTransport

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

async def main():
    async with aiohttp.ClientSession():
        # Set up the Free SIP digital line
        transport = SIPTransport(
            sip_username=os.getenv("SIP_USERNAME"),
            sip_password=os.getenv("SIP_PASSWORD"),
            sip_server="sip.linphone.org",
            port=5060
        )
        
        # Free AI Processing Pipeline via Groq & Google
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
                print("Transcript successfully dispatched to n8n!")
            except Exception as e:
                print(f"n8n webhook dispatch failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
