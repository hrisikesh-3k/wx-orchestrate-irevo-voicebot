from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import logging
import os
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient, 
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
    SpeakWebSocketEvents,
    SpeakWSOptions
)
from src.agents import RealEstateAgent

# Load environment variables and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class MicrophoneManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.is_blocked = False

    async def block(self):
        async with self._lock:
            self.is_blocked = True
            await asyncio.sleep(0.2)  # Short delay to ensure mic stops

    async def unblock(self):
        await asyncio.sleep(1.0)  # Longer delay after TTS
        async with self._lock:
            self.is_blocked = False

class TranscriptCollector:
    def __init__(self):
        self.reset()
        self.mic_manager = MicrophoneManager()

    def reset(self):
        self.transcript_parts = []
        self.is_speaking = False

    async def block_mic(self):
        await self.mic_manager.block()

    async def resume_mic(self):
        await self.mic_manager.unblock()

    def add_part(self, part):
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        return ' '.join(self.transcript_parts)

    def should_process_audio(self):
        return not self.mic_manager.is_blocked

class TTSHandler:
    def __init__(self, api_key, loop=None):
        self.api_key = api_key
        self.loop = loop or asyncio.get_event_loop()
        self.message_queue = asyncio.Queue()
        self.speaking_event = asyncio.Event()
        self.config = DeepgramClientOptions(
            options={"speaker_playback": "true"}
        )

    async def process_tts_queue(self, transcript_collector):
        while True:
            message = await self.message_queue.get()
            if message is None:
                break

            try:
                self.speaking_event.set()
                await transcript_collector.block_mic()
                await self.speak(message)
            finally:
                await transcript_collector.resume_mic()
                self.speaking_event.clear()
                self.message_queue.task_done()

    async def speak(self, text: str):
        try:
            deepgram = DeepgramClient(self.api_key, self.config)
            dg_connection = deepgram.speak.websocket.v("1")
            
            options = SpeakWSOptions(
                model="aura-asteria-en",
                encoding="linear16",
                sample_rate=16000,
            )

            if not dg_connection.start(options):
                raise Exception("Failed to start TTS connection")

            await self.loop.run_in_executor(None, dg_connection.send_text, text)
            await self.loop.run_in_executor(None, dg_connection.flush)
            await self.loop.run_in_executor(None, dg_connection.wait_for_complete)
            await self.loop.run_in_executor(None, dg_connection.finish)

        except Exception as e:
            logging.error(f"TTS Error: {e}")
            raise

async def get_transcript(transcript_collector, websocket, agent):
    try:
        loop = asyncio.get_event_loop()
        tts_handler = TTSHandler(DEEPGRAM_API_KEY, loop)
        # Start TTS worker
        tts_task = asyncio.create_task(tts_handler.process_tts_queue(transcript_collector))
        
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.asyncwebsocket.v("1")
        print("Starting transcription...")

        async def on_message(self, result, **kwargs):
            if transcript_collector.mic_manager.is_blocked:
                return  # Skip processing when blocked

            try:
                sentence = result.channel.alternatives[0].transcript
                
                if not result.speech_final:
                    transcript_collector.add_part(sentence)
                else:
                    transcript_collector.add_part(sentence)
                    full_sentence = transcript_collector.get_full_transcript()
                    
                    if len(full_sentence.strip()) > 0:
                        full_sentence = full_sentence.strip()
                        print(f"Transcribed: {full_sentence}")
                        
                        await websocket.send_json({
                            "role": "user",
                            "content": full_sentence,
                            "status": "Processing..."
                        })

                        # Get LLM response
                        response = await loop.run_in_executor(
                            None, 
                            agent.invoke, 
                            {"input": full_sentence}
                        )
                        llm_response = response['output']
                        print(f"LLM Response: {llm_response}")

                        await websocket.send_json({
                            "role": "assistant",
                            "content": llm_response,
                            "status": "Speaking..."
                        })

                        # Queue TTS message instead of direct processing
                        await tts_handler.message_queue.put(llm_response)
                            
                    transcript_collector.reset()

            except Exception as e:
                logging.error(f"Error processing message: {e}")
                await transcript_collector.resume_mic()  # Ensure mic is resumed on error

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        options = LiveOptions(
            model="nova-2",
            punctuate=True,
            language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            endpointing=300,
            smart_format=True,
        )

        await dg_connection.start(options)
        
        # Create microphone with the same loop
        microphone = Microphone(dg_connection.send)
        await loop.run_in_executor(None, microphone.start)
        print("Microphone is now listening...")

        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            await loop.run_in_executor(None, microphone.stop)
            raise

    except Exception as e:
        logging.error(f"Error in transcription: {e}")
        raise
    finally:
        # Cleanup
        await tts_handler.message_queue.put(None)
        await tts_task

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")

    loop = asyncio.get_event_loop()
    transcript_collector = TranscriptCollector()
    agent = RealEstateAgent().build_agent()
    task = None

    try:
        while True:
            data = await websocket.receive_json()
            
            if data['action'] == 'start' and task is None:
                print("Starting audio capture...")
                await websocket.send_json({"status": "Listening..."})
                task = asyncio.create_task(
                    get_transcript(transcript_collector, websocket, agent)
                )
                
            elif data['action'] == 'stop' and task is not None:
                print("Stopping audio capture...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                task = None
                transcript_collector.reset()
                await websocket.send_json({"status": "Stopped"})

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)