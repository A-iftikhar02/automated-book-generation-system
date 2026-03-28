import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

for model in models_to_try:
    try:
        print(f"Testing model: {model}...")
        response = client.models.generate_content(
            model=model,
            contents="Say hello"
        )
        print(f"Successfully used: {model}")
        print(f"Response: {response.text}")
        break # stop at first success
    except Exception as e:
        print(f"Failed to use {model}: {e}")
