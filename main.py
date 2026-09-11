import os
import asyncio
import aiohttp
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

chat_history = [
    {"role": "system", "content": "You are a professional, polite business receptionist. Speak in maximum 1-2 short sentences."}
]

# 1. Free Interactive Browser Testing Interface (Fixed JS Syntax)
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Tester Console</title>
        <style>
            body { font-family: sans-serif; background: #121212; color: #fff; max-width: 600px; margin: 40px auto; padding: 20px; }
            #chatbox { height: 300px; border: 1px solid #333; padding: 10px; overflow-y: scroll; background: #1e1e1e; border-radius: 8px; margin-bottom: 10px; }
            .user { color: #4af; font-weight: bold; }
            .ai { color: #af4; font-weight: bold; }
            input, button { padding: 10px; background: #333; color: #fff; border: 1px solid #555; border-radius: 4px; }
            input { width: 70%; }
            #hangup { background: #d32f2f; cursor: pointer; float: right; }
        </style>
    </head>
    <body>
        <h2>🤖 Free AI Voice Agent Test Console</h2>
        <div id="chatbox"></div>
        <input type="text" id="userInput" placeholder="Type what you would say on the phone...">
        <button id="sendBtn">Send Speech</button>
        <button id="hangup">End Session</button>

        <script>
            // Bulletproof standard Event Listeners to ensure buttons never freeze
            document.getElementById('sendBtn').addEventListener('click', function() {
                var input = document.getElementById('userInput');
                var box = document.getElementById('chatbox');
                if(!input.value) return;
                
                box.innerHTML += "<p><span class='user'>YOU:</span> " + input.value + "</p>";
                
                fetch('/sip-incoming', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({speech_text: input.value})
                })
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    box.innerHTML += "<p><span class='ai'>AI:</span> " + data.response + "</p>";
                    input.value = '';
                    box.scrollTop = box.scrollHeight;
                })
                .catch(function(err) {
                    box.innerHTML += "<p style='color:red;'>Error connecting to server</p>";
                });
            });

            document.getElementById('hangup').addEventListener('click', function() {
                fetch('/sip-hangup', { method: 'POST' })
                .then(function() {
                    alert('Call ended! Data sent to n8n. Console reset.');
                    document.getElementById('chatbox').innerHTML = '';
                });
            });
        </script>
    </body>
    </html>
    """

@app.post("/sip-incoming")
async def handle_sip_audio(payload: dict):
    global chat_history
    caller_speech = payload.get("speech_text", "")
    if not caller_speech:
        return {"response": ""}
    chat_history.append({"role": "user", "content": caller_speech})
    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=chat_history,
            max_tokens=60
        )
        ai_response = completion.choices.message.content
        chat_history.append({"role": "assistant", "content": ai_response})
        return {"response": ai_response}
    except Exception as e:
        return {"response": "Sorry, let me try processing that again."}

@app.post("/sip-hangup")
async def end_sip_call():
    global chat_history
    if N8N_WEBHOOK_URL:
        formatted_transcript = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        n8n_payload = {"event": "call_completed", "transcript": formatted_transcript, "status": "completed"}
        try: requests.post(N8N_WEBHOOK_URL, json=n8n_payload, timeout=5)
        except Exception: pass
    chat_history = [{"role": "system", "content": "You are a professional, polite business receptionist. Speak in maximum 1-2 short sentences."}]
    return {"status": "session_reset"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
