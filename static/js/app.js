/* =====================================================================
   AI Dubstep Generator – app.js
   ===================================================================== */

"use strict";

// ── DOM references ──────────────────────────────────────────────────────────

const bpmSlider     = document.getElementById("bpm");
const bpmDisplay    = document.getElementById("bpm-display");
const barsSlider    = document.getElementById("bars");
const barsDisplay   = document.getElementById("bars-display");
const keySelect     = document.getElementById("key");
const scaleSelect   = document.getElementById("scale");
const styleSelect   = document.getElementById("style");
const btnGenerate   = document.getElementById("btn-generate");
const btnPlay       = document.getElementById("btn-play");
const btnStop       = document.getElementById("btn-stop");
const btnDownload   = document.getElementById("btn-download");
const statusBar     = document.getElementById("status-bar");
const patternGrid   = document.getElementById("pattern-grid");
const patternJson   = document.getElementById("pattern-json");
const waveCanvas    = document.getElementById("waveform-canvas");
const waveCtx       = waveCanvas.getContext("2d");

const djVolume      = document.getElementById("dj-volume");
const djVolumeDisp  = document.getElementById("dj-volume-display");
const djFilter      = document.getElementById("dj-filter");
const djFilterDisp  = document.getElementById("dj-filter-display");
const djHighpass    = document.getElementById("dj-highpass");
const djHighDisp    = document.getElementById("dj-highpass-display");
const djTempo       = document.getElementById("dj-tempo");
const djTempoDisp   = document.getElementById("dj-tempo-display");

// Keep the prefixed fallback for older WebView/Safari engines used in some desktops.
const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
const DJ_LOW_PASS_Q  = 0.9; // Slight resonance for musical sweep
const DJ_HIGH_PASS_Q = 0.7; // Gentle slope to avoid harshness

// ── State ───────────────────────────────────────────────────────────────────

let currentPattern  = null;
let audioContext    = null;
let audioSource     = null;
let audioBuffer     = null;
let isPlaying       = false;
let masterGain      = null;
let lowpassFilter   = null;
let highpassFilter  = null;
let audioGraphReady = false;

// ── Slider sync ─────────────────────────────────────────────────────────────

bpmSlider.addEventListener("input", () => {
  bpmDisplay.textContent = bpmSlider.value;
});

barsSlider.addEventListener("input", () => {
  barsDisplay.textContent = barsSlider.value;
});

djVolume.addEventListener("input", () => {
  const gain = parseFloat(djVolume.value);
  djVolumeDisp.textContent = `${Math.round(gain * 100)}%`;
  if (masterGain) masterGain.gain.value = gain;
});

djFilter.addEventListener("input", () => {
  const freq = parseFloat(djFilter.value);
  djFilterDisp.textContent = `${Math.round(freq).toLocaleString()} Hz`;
  if (lowpassFilter) lowpassFilter.frequency.value = freq;
});

djHighpass.addEventListener("input", () => {
  const freq = parseFloat(djHighpass.value);
  djHighDisp.textContent = `${Math.round(freq)} Hz`;
  if (highpassFilter) highpassFilter.frequency.value = freq;
});

djTempo.addEventListener("input", () => {
  const tempo = parseFloat(djTempo.value);
  djTempoDisp.textContent = `${Math.round(tempo * 100)}%`;
  if (audioSource) audioSource.playbackRate.value = tempo;
});

// ── Generate ────────────────────────────────────────────────────────────────

btnGenerate.addEventListener("click", async () => {
  setStatus("Generating pattern…", "busy");
  btnGenerate.disabled = true;

  try {
    const response = await fetch("/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bpm:   parseInt(bpmSlider.value, 10),
        key:   keySelect.value,
        scale: scaleSelect.value,
        style: styleSelect.value,
        bars:  parseInt(barsSlider.value, 10),
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || `HTTP ${response.status}`);
    }

    currentPattern = await response.json();
    audioBuffer    = null;   // invalidate old render

    renderPatternGrid(currentPattern);
    patternJson.textContent = JSON.stringify(currentPattern, null, 2);
    clearWaveform();

    btnPlay.disabled     = false;
    btnDownload.disabled = false;
    setStatus(`Pattern generated — ${currentPattern.style} in ${currentPattern.key} ${currentPattern.scale} at ${currentPattern.bpm} BPM`, "success");

  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  } finally {
    btnGenerate.disabled = false;
  }
});

// ── Play ────────────────────────────────────────────────────────────────────

btnPlay.addEventListener("click", async () => {
  if (!currentPattern) return;
  if (isPlaying) return;

  setStatus("Rendering audio…", "busy");
  btnPlay.disabled = true;

  try {
    if (!audioBuffer) {
      audioBuffer = await fetchAudioBuffer(currentPattern);
      drawWaveform(audioBuffer);
    }

    ensureAudioGraph();
    if (audioContext && audioContext.state === "suspended") await audioContext.resume();

    audioSource = audioContext.createBufferSource();
    audioSource.buffer = audioBuffer;
    audioSource.loop   = true;
    // Initialize playback speed from the current DJ tempo slider value.
    audioSource.playbackRate.value = parseFloat(djTempo.value);
    audioSource.connect(highpassFilter);
    audioSource.start();
    isPlaying = true;

    btnPlay.disabled = true;
    btnStop.disabled = false;
    setStatus("Playing… (looping)", "success");

    audioSource.onended = () => {
      if (!isPlaying) return;
      isPlaying = false;
      btnPlay.disabled = false;
      btnStop.disabled = true;
      setStatus("Playback finished.", "");
    };

  } catch (err) {
    setStatus(`Render error: ${err.message}`, "error");
    btnPlay.disabled = false;
  }
});

// ── Stop ────────────────────────────────────────────────────────────────────

btnStop.addEventListener("click", () => {
  if (audioSource) {
    audioSource.loop = false;
    audioSource.stop();
    try {
      audioSource.disconnect();
    } catch (err) {
      console.warn("Audio source already disconnected", err);
    }
    audioSource = null;
  }
  isPlaying = false;
  btnPlay.disabled = false;
  btnStop.disabled = true;
  setStatus("Stopped.", "");
});

// ── Download ────────────────────────────────────────────────────────────────

btnDownload.addEventListener("click", async () => {
  if (!currentPattern) return;
  setStatus("Preparing download…", "busy");

  try {
    const response = await fetch("/render", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pattern: currentPattern }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `dubstep_${currentPattern.key}_${currentPattern.bpm}bpm.wav`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setStatus("WAV downloaded!", "success");
  } catch (err) {
    setStatus(`Download error: ${err.message}`, "error");
  }
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function requireAudioContext() {
  if (!AudioCtxClass) {
    throw new Error("Web Audio API is not available in this browser. Please switch to a modern browser (Edge, Chrome, Firefox) with Web Audio support.");
  }
  audioContext = audioContext || new AudioCtxClass();
  return audioContext;
}

function ensureAudioGraph() {
  requireAudioContext();

  if (!masterGain) {
    masterGain = audioContext.createGain();
    masterGain.gain.value = parseFloat(djVolume.value);
  }
  if (!lowpassFilter) {
    lowpassFilter = audioContext.createBiquadFilter();
    lowpassFilter.type = "lowpass";
    lowpassFilter.frequency.value = parseFloat(djFilter.value);
    lowpassFilter.Q.value = DJ_LOW_PASS_Q;
  }
  if (!highpassFilter) {
    highpassFilter = audioContext.createBiquadFilter();
    highpassFilter.type = "highpass";
    highpassFilter.frequency.value = parseFloat(djHighpass.value);
    highpassFilter.Q.value = DJ_HIGH_PASS_Q;
  }
  if (!audioGraphReady) {
    highpassFilter.connect(lowpassFilter);
    lowpassFilter.connect(masterGain);
    masterGain.connect(audioContext.destination);
    audioGraphReady = true;
  }
}

async function fetchAudioBuffer(pattern) {
  const response = await fetch("/render", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pattern }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${response.status}`);
  }
  const arrayBuf = await response.arrayBuffer();
  const ctx = requireAudioContext();
  return await ctx.decodeAudioData(arrayBuf);
}

function setStatus(msg, type = "") {
  statusBar.textContent = "";
  statusBar.innerHTML   = msg;
  statusBar.className   = "status-bar" + (type ? " " + type : "");
}

// ── Pattern grid renderer ───────────────────────────────────────────────────

function renderPatternGrid(pattern) {
  patternGrid.innerHTML = "";

  const tracks = [
    { label: "Kick",  data: pattern.drums.kick,  cls: "active-kick"  },
    { label: "Snare", data: pattern.drums.snare, cls: "active-snare" },
    { label: "Hi-Hat", data: pattern.drums.hihat, cls: "active-hihat" },
    { label: "Bass",  data: buildBassStepMap(pattern), cls: "active-bass" },
  ];

  for (const track of tracks) {
    const row  = document.createElement("div");
    row.className = "pattern-row";

    const lbl = document.createElement("span");
    lbl.className   = "row-label";
    lbl.textContent = track.label;
    row.appendChild(lbl);

    const cells = document.createElement("div");
    cells.className = "step-cells";

    // Show only the first bar for clarity; cycle through bars visually
    const bars   = track.data;
    const STEPS  = pattern.steps_per_bar;

    for (let b = 0; b < bars.length; b++) {
      for (let s = 0; s < STEPS; s++) {
        const cell = document.createElement("div");
        cell.className = "step-cell";
        if ((s % 4) === 0) cell.classList.add("beat-marker");
        if (bars[b][s]) cell.classList.add(track.cls);
        cells.appendChild(cell);
      }
    }
    row.appendChild(cells);
    patternGrid.appendChild(row);
  }
}

function buildBassStepMap(pattern) {
  // Convert bass notes list to a per-bar step array (1/0) for the grid
  return pattern.bass.notes.map(barNotes => {
    const steps = new Array(pattern.steps_per_bar).fill(0);
    for (const note of barNotes) {
      if (note.step < steps.length) steps[note.step] = 1;
    }
    return steps;
  });
}

// ── Waveform visualizer ──────────────────────────────────────────────────────

function drawWaveform(buffer) {
  const data   = buffer.getChannelData(0);
  const w      = waveCanvas.width;
  const h      = waveCanvas.height;
  const step   = Math.ceil(data.length / w);

  waveCtx.clearRect(0, 0, w, h);
  waveCtx.fillStyle   = "#1a1a2e";
  waveCtx.fillRect(0, 0, w, h);

  waveCtx.beginPath();
  waveCtx.strokeStyle = "#a78bfa";
  waveCtx.lineWidth   = 1.5;

  for (let x = 0; x < w; x++) {
    let min = 1, max = -1;
    for (let i = 0; i < step; i++) {
      const d = data[x * step + i] || 0;
      if (d < min) min = d;
      if (d > max) max = d;
    }
    const yMin = ((1 + min) / 2) * h;
    const yMax = ((1 + max) / 2) * h;
    if (x === 0) {
      waveCtx.moveTo(x, yMin);
    } else {
      waveCtx.lineTo(x, yMin);
      waveCtx.lineTo(x, yMax);
    }
  }
  waveCtx.stroke();
}

function clearWaveform() {
  waveCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);
  waveCtx.fillStyle = "#1a1a2e";
  waveCtx.fillRect(0, 0, waveCanvas.width, waveCanvas.height);
}

// Initialize canvas background
clearWaveform();

// Prime DJ control displays with their default values
djVolume.dispatchEvent(new Event("input"));
djFilter.dispatchEvent(new Event("input"));
djHighpass.dispatchEvent(new Event("input"));
djTempo.dispatchEvent(new Event("input"));
