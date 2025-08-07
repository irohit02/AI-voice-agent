// === Text-to-Speech ===
async function generateAudio() {
  const text = document.getElementById("textInput").value.trim();
  if (!text) {
    alert("Please enter some text.");
    return;
  }

  try {
    const response = await fetch("http://localhost:8000/generate-audio", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ text })
    });

    if (!response.ok) throw new Error("Failed to fetch audio");

    const data = await response.json();
    const audioUrl = data.audio_url;

    const audioPlayer = document.getElementById("audioPlayer");
    audioPlayer.src = audioUrl;
    audioPlayer.play();
  } catch (error) {
    console.error("TTS Error:", error);
    alert("An error occurred while generating audio.");
  }
}

// === Voice Recording, Upload & Transcription ===
let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const audioPlayback = document.getElementById("audioPlayback");
const listeningStatus = document.getElementById("listeningStatus");
const uploadStatus = document.getElementById("uploadStatus");
const transcriptResult = document.getElementById("transcriptResult");

startBtn.onclick = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      const audioUrl = URL.createObjectURL(audioBlob);
      audioPlayback.src = audioUrl;

      listeningStatus.style.display = "none";
      uploadStatus.textContent = "Uploading...";

      const formData = new FormData();
      formData.append("file", audioBlob, "recorded_audio.wav");

      try {
        // Upload to /upload-audio
        const uploadResponse = await fetch("http://localhost:8000/upload-audio", {
          method: "POST",
          body: formData
        });

        if (!uploadResponse.ok) throw new Error("Upload failed");

        const uploadResult = await uploadResponse.json();
        uploadStatus.textContent = `✅ Uploaded: ${uploadResult.filename} (${uploadResult.content_type}, ${uploadResult.size_kb} KB)`;
      } catch (uploadErr) {
        console.error("Upload Error:", uploadErr);
        uploadStatus.textContent = "❌ Upload failed.";
      }

      try {
        // Transcribe via /transcribe/file
        uploadStatus.textContent = "📝 Transcribing...";
        const transcribeForm = new FormData();
        transcribeForm.append("file", audioBlob, "recorded_audio.wav");

        const transcribeResponse = await fetch("http://localhost:8000/transcribe/file", {
          method: "POST",
          body: transcribeForm
        });

        if (!transcribeResponse.ok) throw new Error("Transcription failed");

        const transcribeResult = await transcribeResponse.json();
        transcriptResult.textContent = "🗣️ " + transcribeResult.transcript;
        uploadStatus.textContent = "✅ Transcription complete.";
      } catch (err) {
        console.error("Transcription error:", err);
        transcriptResult.textContent = "❌ Transcription failed.";
        uploadStatus.textContent = "❌ Transcription failed.";
      }
    };

    mediaRecorder.start();
    startBtn.disabled = true;
    stopBtn.disabled = false;
    listeningStatus.style.display = "block";
    transcriptResult.textContent = "";
  } catch (err) {
    console.error("Recording Error:", err);
    alert("Failed to start recording.");
  }
};

stopBtn.onclick = () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }
  listeningStatus.style.display = "none";
};
