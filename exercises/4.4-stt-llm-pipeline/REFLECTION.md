# Reflection: STT + LLM Mini Pipeline

## 1. Where does this map to in the SCAI voice pipeline?

```
[Caller] ─── audio stream ──► [Whisper STT] ──► transcript ──► [LLM] ──► reply text
                WebSocket          (Step 1)                    (Step 2)
```

| Mini-pipeline step | SCAI equivalent |
|---|---|
| Read audio file | Stream real-time audio chunks from Twilio/WebSocket inside `VoiceCallConsumer` |
| `whisper-1` transcription | Deepgram or Whisper STT module inside `pipeline.py` |
| GPT-4o with receptionist prompt | The configured LLM with full system prompt, call context, and tenant-specific instructions |
| Print reply text | TTS synthesis → audio stream sent back to caller over WebSocket |

The exact same **STT → LLM** sequence is the core inner loop of SCAI's voice pipeline. Every
time the caller finishes a sentence, this loop fires: audio bytes arrive, get transcribed,
and the transcript is passed to the LLM to generate the next conversational turn.

---

## 2. What is missing from this mini-pipeline compared to the real SCAI system?

### Real-time streaming audio (WebSocket)
Our pipeline reads a **static file**. SCAI streams audio in small chunks (typically 20 ms
frames) over a persistent WebSocket connection with Twilio. This requires handling partial
audio buffers and assembling them into complete utterances.

### Voice Activity Detection (VAD)
A real system needs to know **when the user has stopped speaking** before sending audio to
the STT engine. Without VAD, the system either waits too long (bad latency) or cuts the user
off mid-sentence. SCAI uses a VAD model or silence-detection threshold to trigger
transcription at the right moment.

### Text-to-Speech (TTS)
Our pipeline only **prints** the LLM reply. SCAI must synthesize the reply back into speech
(using ElevenLabs, OpenAI TTS, or a similar service) and stream the audio bytes back to the
caller in real time — before the full reply is even complete (chunked/streaming TTS).

### Conversation history and context management
Our pipeline is **stateless** — one audio clip, one reply. SCAI maintains the full
conversation history across many turns, injects tenant-specific context (patient name,
appointment details, business rules), and manages state machines (e.g., `greeting →
intent_detection → booking → confirmation`).

### Barge-in (interruption handling)
In a real phone conversation, the caller might start speaking while the AI is still talking.
SCAI detects this mid-stream and aborts the current TTS playback, re-runs the STT → LLM
loop on the new utterance. This is a complex async orchestration problem our mini-pipeline
does not address.

### Error handling, retries, and latency optimisation
SCAI includes timeout handling, model fallbacks, streaming LLM output (reducing
time-to-first-byte), and connection recovery logic. Our pipeline exits on any error.

### Multi-tenancy
Our pipeline uses a single hardcoded API key and system prompt. SCAI dynamically selects the
LLM configuration, system prompt, voice, and business rules per tenant, per call — all
resolved through the tenant's schema at runtime.
