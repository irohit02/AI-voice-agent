document.addEventListener("DOMContentLoaded", () => {
  const recordButton = document.getElementById("record-button");
  const statusIndicator = document.getElementById("status-indicator");
  const messageWindow = document.getElementById("message-window");
  const audioPlayback = document.getElementById("audio-playback");

  let recording = false;
  let mediaRecorder;
  let audioChunks = [];

  const urlParams = new URLSearchParams(window.location.search);
  let sessionId = urlParams.get("session_id") || crypto.randomUUID();
  if (!urlParams.has("session_id")) {
    urlParams.set("session_id", sessionId);
    window.history.replaceState({}, "", `?${urlParams.toString()}`);
  }

  const setStatus = (text) => {
    statusIndicator.textContent = text;
  };

  const addMessage = (sender, text, isTyping = false) => {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", sender);
    if (isTyping) {
      messageElement.classList.add("typing");
    }

    const bubble = document.createElement("div");
    bubble.classList.add("bubble");
    bubble.textContent = text;
    messageElement.appendChild(bubble);

    messageWindow.appendChild(messageElement);
    messageWindow.scrollTop = messageWindow.scrollHeight;
    return messageElement;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.addEventListener("dataavailable", (event) => {
        audioChunks.push(event.data);
      });

      mediaRecorder.addEventListener("stop", () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        sendAudioToServer(audioBlob);
      });

      mediaRecorder.start();
      recording = true;
      recordButton.classList.add("recording");
      setStatus("Recording... speak your mind!");
    } catch (error) {
      console.error("Error starting recording:", error);
      setStatus("Couldn't start recording. Please allow microphone access.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      recording = false;
      recordButton.classList.remove("recording");
      setStatus("Processing your audio...");
    }
  };

  const sendAudioToServer = async (audioBlob) => {
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.wav");

    const typingIndicator = addMessage("bot", "", true);

    try {
      const response = await fetch(`/agent/chat/${sessionId}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }

      const data = await response.json();

      messageWindow.removeChild(typingIndicator);

      addMessage("user", data.transcript);
      addMessage("bot", data.llm_response);

      if (data.audio_url) {
        audioPlayback.src = data.audio_url;
        audioPlayback.play();
        setStatus("Playing back response...");
      }
    } catch (error) {
      console.error("Error sending audio to server:", error);
      messageWindow.removeChild(typingIndicator);
      addMessage("bot", "Sorry, something went wrong. Please try again.");
      setStatus("An error occurred. Ready to try again.");
    }
  };

  recordButton.addEventListener("click", () => {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  audioPlayback.addEventListener("ended", () => {
    setStatus("Ready for your next message.");
  });

  addMessage("bot", "Hello! I'm your AI assistant. Click the mic to start talking.");
});
