import os
import openai

def process_audio(audio_file_path):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print(f"Transcribing {audio_file_path}...")
    # Step 1: STT
    with open(audio_file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    
    user_text = transcript.text
    print(f"User said: {user_text}")

    # Step 2: LLM
    print("Generating response...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful receptionist. Answer the user's question."},
            {"role": "user", "content": user_text}
        ]
    )

    llm_reply = response.choices[0].message.content
    print(f"LLM Reply: {llm_reply}")

if __name__ == "__main__":
    audio_path = "sample.mp3"
    if not os.path.exists(audio_path):
        print(f"Please provide an audio file named '{audio_path}' in the same directory to run the pipeline.")
    else:
        process_audio(audio_path)
