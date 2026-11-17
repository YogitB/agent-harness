import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads your key from .env

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",  # point the OpenAI library at Groq
)

reply = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Say hi and tell me one fun fact."}],
)

print(reply.choices[0].message.content)