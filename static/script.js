// ---------------- TAB SWITCHING ----------------
const tabs = { assistant: document.getElementById("assistantSection") };
const tabButtons = { assistant: document.getElementById("tabAssistant") };
function showTab(tabName) { for(const key in tabs) { if(key===tabName){tabs[key].classList.add("active");tabButtons[key].classList.add("active");}else{tabs[key].classList.remove("active");tabButtons[key].classList.remove("active");}} }
tabButtons.assistant.onclick = () => showTab("assistant");

// ---------------- UTILITIES ----------------
function speakFallback(message = "I'm having trouble connecting right now.") {
  try { const synth = window.speechSynthesis; if(!synth) return; const utter = new SpeechSynthesisUtterance(message); utter.lang="en-US"; utter.rate=1; synth.cancel(); synth.speak(utter); } catch(_) {}
}

async function fetchJsonWithTimeout(url, { timeout = 20000, ...options } = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    const ct = res.headers.get("content-type") || "";
    let data = null;
    if(ct.includes("application/json")) data = await res.json();
    else { const text = await res.text(); try{data=JSON.parse(text);}catch{data={message:text}}}
    if(!res.ok){throw (data?.error||data||{message:"Request failed"});}
    return data;
  } catch(e){ if(e?.name==='AbortError') throw {message:"Request timed out"}; throw e; }
  finally{ clearTimeout(id); }
}

// ---------------- AI ASSISTANT ----------------
const recordButton = document.getElementById("recordButton");
const recordStatus = document.getElementById("recordStatus");
const chatContainer = document.getElementById("chatContainer");
const assistantAudioPlayback = document.getElementById("assistantAudioPlayback");

let recording = false, mediaRecorderAssistant, audioChunksAssistant=[], lastBotAudioUrl=null;

// ---------------- STATUS ----------------
function setStatus(state){
  recordStatus.className = state;
  if(state==="recording") recordStatus.textContent="🔴 Recording...";
  else if(state==="playing") recordStatus.textContent="🟢 Playing Bot Audio";
  else recordStatus.textContent="⚪ Idle";
}

// ---------------- CHAT ----------------
function addMessageToChat(sender, message, isTyping=false){
  if(!chatContainer) return;
  const wrap=document.createElement("div"); wrap.className=`message ${sender==="You"?"user":"bot"}`;
  const avatar=document.createElement("div"); avatar.className="avatar"; avatar.textContent=sender==="You"?"Y":"A";
  const bubble=document.createElement("div"); bubble.className="bubble"; if(isTyping) bubble.classList.add("typing"); bubble.textContent=isTyping?"":message;
  wrap.appendChild(avatar); wrap.appendChild(bubble); chatContainer.appendChild(wrap); chatContainer.scrollTop = chatContainer.scrollHeight;
  return bubble;
}

// ---------------- RECORD ----------------
function startRecording(){
  navigator.mediaDevices.getUserMedia({audio:true}).then(stream=>{
    mediaRecorderAssistant=new MediaRecorder(stream); audioChunksAssistant=[]; mediaRecorderAssistant.start();
    recording=true; setStatus("recording"); recordButton.textContent="⏹ Stop Recording";

    mediaRecorderAssistant.ondataavailable=e=>audioChunksAssistant.push(e.data);
    mediaRecorderAssistant.onstop=()=>{ const audioBlob=new Blob(audioChunksAssistant,{type:"audio/wav"}); sendAssistantAudio(audioBlob); recording=false; setStatus("idle"); recordButton.textContent="🎙 Start Recording"; };
  }).catch(err=>{ console.error(err); alert("Please allow microphone access."); setStatus("idle"); });
}

function stopRecording(){ if(mediaRecorderAssistant && mediaRecorderAssistant.state!=="inactive") mediaRecorderAssistant.stop(); }

// ---------------- BUTTON CLICK ----------------
recordButton.onclick=()=>{
  if(recording) stopRecording();
  else if(assistantAudioPlayback && !assistantAudioPlayback.paused){ assistantAudioPlayback.pause(); assistantAudioPlayback.currentTime=0; setStatus("idle"); recordButton.textContent="🎙 Start Recording"; }
  else startRecording();
};

// ---------------- AUDIO PLAYBACK ----------------
assistantAudioPlayback.onplay=()=>setStatus("playing");
assistantAudioPlayback.onended=()=>setStatus("idle");
assistantAudioPlayback.onpause=()=>setStatus("idle");

// ---------------- SESSION ID ----------------
const urlParams = new URLSearchParams(window.location.search);
let sessionId = urlParams.get("session_id") || crypto.randomUUID();
if(!urlParams.get("session_id")) { urlParams.set("session_id", sessionId); window.history.replaceState(null,"","?"+urlParams.toString()); }

// ---------------- SEND TO SERVER ----------------
function sendAssistantAudio(blob){
  const formData=new FormData();
  formData.append("file",blob,"input.wav");
  addMessageToChat("You","",true); // typing placeholder

  fetchJsonWithTimeout(`http://127.0.0.1:8000/agent/chat/${sessionId}`,{method:"POST",body:formData})
    .then(data=>{
      const lastBubble = chatContainer.querySelector(".bubble.typing"); if(lastBubble) lastBubble.remove();
      if(data?.transcript) addMessageToChat("You", data.transcript);
      if(data?.llm_response) addMessageToChat("Bot", data.llm_response);
      if(data?.audio_url){ lastBotAudioUrl=data.audio_url; assistantAudioPlayback.src=data.audio_url; assistantAudioPlayback.play(); }
      else speakFallback();
    }).catch(err=>{ console.error(err); speakFallback(); addMessageToChat("Bot","Sorry, I encountered an error. Please try again."); });
}

// ---------------- INITIAL BOT MESSAGE ----------------
window.addEventListener("load",()=>{ if(chatContainer.children.length===0) addMessageToChat("Bot","Hello! I'm your AI voice assistant. Click the microphone button and start talking to begin our conversation."); });

// ---------------- GLOBAL ERROR HANDLING ----------------
window.addEventListener("error",(event)=>{ console.error(event.error||event.message); speakFallback(); });
window.addEventListener("unhandledrejection",(event)=>{ console.error(event.reason); speakFallback(); });
