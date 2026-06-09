from dotenv import load_dotenv
import os

load_dotenv('.env')
api_key = os.getenv('GROQ_API_KEY')
print('GROQ_API_KEY found' if api_key else 'GROQ_API_KEY not found')

try:
    from groq import Groq
except Exception as e:
    print('Failed to import groq:', e)
    raise

try:
    client = Groq(api_key=api_key)
    print('Groq client initialized (no model arg)')
except Exception as e:
    print('Groq init failed:', e)
    raise
