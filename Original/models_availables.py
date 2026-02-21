from dotenv import load_dotenv
import os
load_dotenv()
from google import genai
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
for m in client.models.list():
    if 'imagen' in m.name.lower() or 'image' in m.name.lower():
        print(f'{m.name:50s}  supported: {m.supported_actions}')