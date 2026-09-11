import os
import asyncio
import aiohttp
import requests
import uvicorn
from fastapi import FastAPI
from groq import Groq

# 1. Initialize API configurations safely from environment keys
app = FastAPI()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# Keep track of active session conversations natively
chat_history = [
    {"role": "system", "content": "You are a professional, polite phone receptionist. Speak in maximum 1-2 short sentences."}
]

@app.get("/")
def read_root():
    return {"status": "AI Voice Receptor Endpoint Live & Ready"}

# 2. Handles Incoming Text Stream via SIP Webhook Routing
@app.post("/sip-incoming")
async def handle_sip_audio(payload: dict):
    global chat_history
    
    # Extract caller's speech string passed by your SIP layer
    caller_speech = payload.get("speech_text", "")
    if not caller_speech:
        return {"response": ""}
        
    # Append input speech onto conversation log
    chat_history.append({"role": "user", "content": caller_speech})
    
    try:
        # Core Free-Tier Processing Layer via Groq Direct Client SDK
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=chat_history,
            max_tokens=60
        )
        
        ai_response = completion.choices[0].message.content
        chat_history.append({"role": "assistant", "content": ai_response})
        return {"response": ai_response}
        
    except Exception as e:
        print(f"Groq runtime process failed: {e}")
        return {"response": "Sorry, let me try processing that again."}

# 3. Dispatches Clean Log to n8n Once the Call Finishes
@app.post("/sip-hangup")
async def end_sip_call():
    global chat_history
    if N8N_WEBHOOK_URL:
        # Build a highly readable transcription string block
        formatted_transcript = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        
        n8n_payload = {
            "event": "call_completed",
            "transcript": formatted_transcript,
            "status": "completed"
        }
        try:
            requests.post(N8N_WEBHOOK_URL, json=n8n_payload, timeout=5)
            print("Transcript packet successfully pushed to n8n!")
        except Exception as e:
            print(f"Failed pushing payload to n8n: {e}")
            
    # Reset tracking state for next incoming caller connection
    chat_history = [chat_history[0]]
    return {"status": "session_reset"}

if __name__ == "__main__":
    # Launch uvicorn web server natively mapped on Render container ports
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
