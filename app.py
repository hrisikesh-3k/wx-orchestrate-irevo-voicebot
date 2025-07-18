from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import speech_recognition as sr
import pyttsx3
import asyncio
from src.agents import RealEstateAgent
import threading
import queue
import logging
import time
from src.utils import remove_md_asterisks

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize components
agent_builder = RealEstateAgent()
agent = agent_builder.build_agent()
recognizer = sr.Recognizer()

# Initialize TTS engine
engine = pyttsx3.init()

# Create locks and events for synchronization
tts_lock = threading.Lock()
mic_lock = threading.Lock()
is_speaking = threading.Event() #playing the output as audio
should_stop = threading.Event()

# Queues for thread synchronization
audio_queue = queue.Queue()


class MicrophoneManager:
    def __init__(self):
        self.mic = None
        self.source = None

    def __enter__(self):
        if is_speaking.is_set():
            return None
        self.mic = sr.Microphone()
        self.source = self.mic.__enter__()
        return self.source

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mic:
            self.mic.__exit__(exc_type, exc_val, exc_tb)


def listen():
    """Capture audio from the microphone and transcribe it."""
    if is_speaking.is_set():
        return None

    try:
        with mic_lock:  # Ensure exclusive mic access
            with MicrophoneManager() as source:
                if source is None or is_speaking.is_set():
                    return None

                logging.info("Listening for audio...")
                # recognizer.adjust_for_ambient_noise(source) 
                # recognizer.dynamic_energy_threshold
                audio = recognizer.listen(source)

                # Double check we're not speaking before processing
                if is_speaking.is_set():
                    return None

                return recognizer.recognize_google(audio, language="en-IN")
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        logging.error(f"Speech recognition error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in listen: {e}")
        return None


def speak_text(text):
    """Convert text to speech using TTS engine."""
    try:
        is_speaking.set()  # Signal that speech is starting
        time.sleep(0.1)  # Small delay to ensure mic is fully stopped

        with tts_lock:
            text = remove_md_asterisks(text) # Remove markdown asterisks
            engine.say(text)
            engine.runAndWait()

    except Exception as e:
        logging.error(f"TTS Error: {e}")
    finally:
        time.sleep(0.2)  # Small delay before allowing mic to start again
        is_speaking.clear()


async def process_audio(websocket: WebSocket):
    """Process audio queries from the queue."""
    while not should_stop.is_set():
        try:
            query = audio_queue.get_nowait()

            if not query:  # Skip if no valid input
                continue

            if query.lower() in ["exit", "bye", "stop"]:
                await websocket.send_json({"role": "user", "content": query, "status": "Stopping..."})
                should_stop.set()
                break

            await websocket.send_json({"role": "user", "content": query, "status": "Processing..."})

            output = agent.invoke({"input": query})
            response = output['output']

            # First send the response to UI
            await websocket.send_json({"role": "assistant", "content": response, "status": "Received..."})

            # Small delay to ensure UI updates before audio starts
            await asyncio.sleep(0.2)

            # Then play the audio
            await websocket.send_json({"status": "Speaking..."})
            speak_text(response)

        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in process_audio: {e}")
            is_speaking.clear()


def audio_listener():
    """Listen for audio input and add it to the queue."""
    while not should_stop.is_set():
        try:
            if is_speaking.is_set():
                time.sleep(0.1)  # Short sleep to prevent busy waiting
                continue

            query = listen()
            if query:  # Only process valid input
                audio_queue.put(query)
                logging.info(f"Received audio input: {query}")

                if query.lower() in ["exit", "bye", "stop"]:
                    should_stop.set()
                    break

        except Exception as e:
            logging.error(f"Error in audio_listener: {e}")
            break


@app.get("/")
async def get(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling audio input and responses."""
    await websocket.accept()
    audio_thread = None

    try:
        while True:
            data = await websocket.receive_json()

            if data['action'] == 'start' and audio_thread is None:
                # Reset all control flags
                should_stop.clear()
                is_speaking.clear()

                audio_thread = threading.Thread(target=audio_listener)
                audio_thread.daemon = True 
                audio_thread.start()

                await websocket.send_json({"status": "Listening..."})
                await process_audio(websocket)

            elif data['action'] == 'stop' and audio_thread is not None:
                should_stop.set()
                is_speaking.clear()
                audio_queue.put("stop")
                audio_thread = None

                await websocket.send_json({"status": "Stopped"})

    except Exception as e:
        logging.error(f"Error in websocket_endpoint: {e}")
    finally:
        should_stop.set()
        is_speaking.clear()
        if audio_thread is not None:
            audio_queue.put("stop")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)