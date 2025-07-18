// WebSocket connection
let ws = new WebSocket("ws://localhost:8000/ws");

let isListening = false;
let isMuted = false;
let mediaStream;

const equalizerButton = document.getElementById('equalizer');
const muteButton = document.getElementById('mute');
const closeButton = document.getElementById('cancel');
const chatContainer = document.getElementById('chatContainer');

$('#chatContainer').hide();
$('#loader-gif').hide();

console.log("Marked loaded:", typeof marked); // Should output "function"

function formatAssistantMessage(content) {
    // Check if the content is a valid string
    if (typeof content !== 'string') {
        console.warn("Invalid content type. Expected a string.");
        return content;  // If it's not a string, return the content as is
    }

    // Convert markdown to HTML using the 'marked' function
    try {
        return marked(content);  // Use marked to convert markdown to HTML
    } catch (error) {
        console.error("Error converting markdown:", error);
        return content;  // Fallback to raw content if conversion fails
    }
}

ws.onmessage = function (event) {
    const data = JSON.parse(event.data);

    // Add assistant or user message to the chat container
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${data.role}-message`;

    // Format the content if it's from the assistant
    if (data.role === 'assistant') {
        messageDiv.innerHTML = `${data.role === 'user' ? 'You' : 'Assistant'}: ${formatAssistantMessage(data.content)}`;
    } else {
        messageDiv.textContent = `${data.role === 'user' ? 'You' : 'Assistant'}: ${data.content}`;
    }

    if (data.content) {
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Handle status messages
    if (data.status) {
        $('#loader-gif').toggle(data.status === 'Listening...' || data.status === 'Processing...');
    }
};


equalizerButton.onclick = function () {
    $('#no-chat').hide();
    $('#chatContainer').show();

    isListening = true;

    // Start recording audio
    startAudioRecording();

    // Update UI
    equalizerButton.style.display = "none";
    muteButton.style.display = "inline-block";
    muteButton.src = "/static/icons/unmute.png";

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'start',
            message: 'start'
        }));
    }
};

muteButton.onclick = function () {
    isMuted = !isMuted;

    // Send mute/unmute action to WebSocket
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: isMuted ? 'mute' : 'unmute',
            message: isMuted ? 'Microphone is muted.' : 'Microphone is unmuted.'
        }));
    }

    // Stop microphone stream when muting
    if (isMuted) {
        stopAudioRecording();  // Stop the audio recording when muted
    } else {
        startAudioRecording();  // Start the audio recording again when unmuted
    }

    // Update the UI (mute/unmute icon)
    muteButton.src = isMuted ? "/static/icons/mute.png" : "/static/icons/unmute.png";
};

closeButton.onclick = function () {
    stopAudioRecording();

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'stop',
            message: 'stop'
        }));
    }

    ws.close();

    // Reset UI
    equalizerButton.style.display = "inline-block";
    muteButton.style.display = "none";
};

function startAudioRecording() {
    if (isMuted) return;  // Prevent starting the stream if muted

    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function (stream) {
            mediaStream = stream;

            const audioContext = new AudioContext();
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(1024, 1, 1);

            source.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = function (e) {
                // Check mute status here before processing audio
                if (!isMuted) {
                    const audioData = e.inputBuffer.getChannelData(0);
                    const audioBlob = new Blob([new Float32Array(audioData).buffer], {
                        type: 'audio/wav'
                    });

                    const reader = new FileReader();
                    reader.onloadend = function () {
                        const base64Audio = reader.result.split(',')[1];

                        if (ws.readyState === WebSocket.OPEN && !isMuted) {  // Recheck mute before sending
                            ws.send(JSON.stringify({ action: 'audio', audio: base64Audio }));
                        }
                    };
                    reader.readAsDataURL(audioBlob);
                }
            };
        })
        .catch(err => console.error('Microphone error:', err));
}

function stopAudioRecording() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop()); // Stop all tracks
        mediaStream = null; // Nullify the mediaStream reference to indicate the microphone is stopped
    }
}
