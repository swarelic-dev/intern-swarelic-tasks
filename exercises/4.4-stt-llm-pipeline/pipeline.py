"""
pipeline.py — Exercise 4.4: STT + LLM Mini Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrates the core STT → LLM loop at the heart of SCAI's voice pipeline.

Step 1  Audio file  →  OpenAI Whisper API  →  transcript text
Step 2  Transcript  →  OpenAI Chat API      →  receptionist reply

Requirements
------------
    pip install openai
    export OPENAI_API_KEY="sk-..."

Usage
-----
    # Transcribe and respond to a specific audio file
    python pipeline.py sample.mp3

    # Or use the default filename "sample.mp3" in the same directory
    python pipeline.py
"""

from __future__ import annotations

import os
import sys


def transcribe(client, audio_file_path: str) -> str:
    """
    Step 1 — Speech-to-Text
    Use OpenAI Whisper to transcribe an audio file to text.

    Maps to: the STT stage in SCAI's pipeline.py, where audio chunks
    streamed over WebSocket are forwarded to Deepgram / Whisper.
    """
    print(f"[STT] Transcribing '{audio_file_path}' with Whisper …")
    with open(audio_file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
        )
    transcript = response.strip()
    print(f"[STT] Transcript: \"{transcript}\"")
    return transcript


def generate_reply(client, transcript: str) -> str:
    """
    Step 2 — LLM Response
    Pass the transcript to GPT with a receptionist system prompt.

    Maps to: the LLM stage in SCAI's pipeline.py, where the transcript
    is combined with call context and sent to the configured LLM.
    """
    print("[LLM] Sending transcript to GPT-4o …")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful receptionist. Answer the user's question.",
            },
            {
                "role": "user",
                "content": transcript,
            },
        ],
        temperature=0.7,
    )
    reply = response.choices[0].message.content.strip()
    print(f"[LLM] Reply: \"{reply}\"")
    return reply


def run_pipeline(audio_file_path: str) -> None:
    """
    Execute the full STT → LLM mini-pipeline.

    Parameters
    ----------
    audio_file_path : str
        Path to a .mp3, .wav, .m4a, or .webm audio file.
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY environment variable is not set.")
        print("        Export it with: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    if not os.path.exists(audio_file_path):
        print(f"[ERROR] Audio file not found: '{audio_file_path}'")
        print("        Provide a valid audio file path as an argument.")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    print("=" * 55)
    print("  SCAI Mini Voice Pipeline — STT + LLM")
    print("=" * 55)

    # Step 1: Speech-to-Text
    transcript = transcribe(client, audio_file_path)

    print()

    # Step 2: LLM Reply
    reply = generate_reply(client, transcript)

    print()
    print("=" * 55)
    print("  Pipeline complete.")
    print(f"  Transcript : {transcript}")
    print(f"  LLM Reply  : {reply}")
    print("=" * 55)


if __name__ == "__main__":
    # Accept an optional CLI argument for the audio file path
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "sample.mp3"
    run_pipeline(audio_path)
