from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Dict, Callable
from deepgram import Deepgram
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']
        
            if transcript:
                await fast_socket.send_text(transcript) 

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket

async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)
        
        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')
 
@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# @app.websocket("/listen")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()

#     try:
#         deepgram_socket = await process_audio(websocket) 

#         while True:
#             data = await websocket.receive_bytes()
#             deepgram_socket.send(data)
#     except Exception as e:
#         raise Exception(f'Could not process audio: {e}')
#     finally:
#         await websocket.close()

import base64

def save_base64_audio(base64_string, file_path="output_audio.wav"):
    """
    Decodes a base64 audio string and saves it as a .wav file.

    :param base64_string: The base64-encoded audio data.
    :param file_path: The file path where the audio file will be saved.
    """
    try:
        audio_data = base64.b64decode(base64_string)
        with open(file_path, "wb") as audio_file:
            audio_file.write(audio_data)
        print(f"Audio file saved successfully at {file_path}")
    except Exception as e:
        print(f"Error saving audio file: {e}")
        
        
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    data = await websocket.accept()

    try:
        data = await websocket.receive_json()
        print(f"Data received: {data}")
        if data['action'] == 'start':
            print("Listening...")
            
            await websocket.send_json({"status": "Listening..."})
            
            # await process_audio(websocket)
        if data['action'] == 'audio':
            audio = data['audio'] 
            save_base64_audio(audio)
            print("Audio received")
            # break
                

    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()