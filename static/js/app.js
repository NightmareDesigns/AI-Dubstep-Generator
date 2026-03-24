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

// ── State ───────────────────────────────────────────────────────────────────

let currentPattern  = null;
let audioContext    = null;
let audioSource     = null;
let audioBuffer     = null;
let isPlaying       = false;

// ── Slider sync ─────────────────────────────────────────────────────────────

bpmSlider.addEventListener("input", () => {
  bpmDisplay.textContent = bpmSlider.value;
});

barsSlider.addEventListener("input", () => {
  barsDisplay.textContent = barsSlider.value;
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

    audioContext = audioContext || new AudioContext();
    if (audioContext.state === "suspended") await audioContext.resume();

    audioSource = audioContext.createBufferSource();
    audioSource.buffer = audioBuffer;
    audioSource.loop   = true;
    audioSource.connect(audioContext.destination);
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
  audioContext   = audioContext || new AudioContext();
  return await audioContext.decodeAudioData(arrayBuf);
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
