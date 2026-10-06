# Reflection: STT + LLM Mini Pipeline

**1. Where does this map to in the SCAI voice pipeline?**
This mini-pipeline maps to the core STT (Speech-to-Text) and LLM (Large Language Model) integration steps within the `pipeline.py` or equivalent module in the SCAI voice pipeline. In SCAI, incoming audio from a telephony provider (like Twilio) would be streamed to a transcriber (like Whisper or Deepgram), and the resulting text is fed into the LLM to generate a conversational response.

**2. What is missing from this mini-pipeline compared to the real SCAI system?**
- **Streaming audio:** The real system likely handles streaming audio chunks (WebSocket) rather than static files to ensure low latency, allowing real-time bidirectional conversation.
- **TTS (Text-to-Speech):** The mini-pipeline only prints the text response. A real system must synthesize the LLM's text back into speech using a service like ElevenLabs, OpenAI TTS, or similar.
- **VAD (Voice Activity Detection):** Real systems need to know when the user starts and stops speaking to properly interrupt (barge-in) and trigger the LLM at the right time.
- **State and Context Management:** The SCAI pipeline manages the entire conversation history, call context (tenant context, user data), and system state across multiple turns.
- **Error Handling and Latency Optimizations:** The real system includes retries, fallback models, and optimizations like chunked LLM generation to reduce Time-to-First-Byte (TTFB).
