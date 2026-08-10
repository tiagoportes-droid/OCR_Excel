"""Script temporario para verificar APIs do SDK."""
import inspect
import sys

# --- Google GenAI ---
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai NAO instalado")
else:
    print("google-genai OK")
    # Verificar métodos disponíveis no client
    print("Client attrs:", [m for m in dir(genai.Client) if not m.startswith('_')])
    # Verificar signature de generate_content no models
    try:
        sig = inspect.signature(genai.Client.models.generate_content)
        print("generate_content signature:", sig)
    except Exception as e:
        print("generate_content error:", e)
    # Verificar types.Part
    print("Part methods:", [m for m in dir(types.Part) if not m.startswith('_')])
    try:
        print("Part.from_bytes sig:", inspect.signature(types.Part.from_bytes))
    except Exception as e:
        print("Part.from_bytes error:", e)
    try:
        print("Part.from_text sig:", inspect.signature(types.Part.from_text))
    except Exception as e:
        print("Part.from_text error:", e)
    print("Content sig:", inspect.signature(types.Content))

# --- Ollama ---
import shutil
which_ollama = shutil.which("ollama")
print("Ollama disponivel:", which_ollama)