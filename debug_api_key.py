#!/usr/bin/env python3
"""Debug script to check if API key is being loaded correctly"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import get_settings

settings = get_settings()

print(f"AI_ENABLED: {settings.ai_enabled}")
print(f"API_PROVIDER: {settings.ai_provider}")
print(f"GEMINI_MODEL_ID: {settings.gemini_model_id}")

if settings.gemini_api_key:
    print(f"✅ GEMINI_API_KEY found: {settings.gemini_api_key[:10]}...{settings.gemini_api_key[-5:]}")
    print(f"   Key length: {len(settings.gemini_api_key)}")
else:
    print(f"❌ GEMINI_API_KEY is None")

# Now try to initialize the client
print("\nTrying to initialize Gemini client...")
try:
    from app.infrastructure.ai_clients.gemini_client import GeminiClient
    client = GeminiClient(settings)
    print("✅ GeminiClient initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize GeminiClient: {e}")

# Try a simple API call
print("\nTrying to call Gemini API via new REST client...")
try:
    import asyncio
    import httpx
    
    async def test_api():
        api_key = settings.gemini_api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        # Use simple format like test_api_direct.py
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Say 'Simple test' only."}
                    ]
                }
            ]
        }
        
        print("Trying simple format...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and result["candidates"]:
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"✅ API call successful: {text}")
            else:
                print(f"❌ Error: {response.json()}")
    
    asyncio.run(test_api())
except Exception as e:
    print(f"❌ API call failed: {e}")
