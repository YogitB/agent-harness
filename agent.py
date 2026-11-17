import os, json, subprocess
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
MODEL = "openai/gpt-oss-120b"

# 1. The tools the AI is allowed to use
def list_files(path="."):
    return "\n".join(os.listdir(path))

def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()[:4000]

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {path}"

TOOLS = {"list_files": list_files, "read_file": read_file, "write_file": write_file}

# 2. Describe the tools so the AI knows they exist
TOOL_SPECS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files in a folder",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a text file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"]}}},
]

messages = [{"role": "system", "content": "You are a helpful coding agent. Use tools when you need them."}]

# 3. The loop
while True:
    user = input("\nYou: ")
    if user.lower() in ("quit", "exit"):
        break
    messages.append({"role": "user", "content": user})

    while True:
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SPECS)
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:          # no tools needed, so it's answering
            print("\nAgent:", msg.content)
            break

        for call in msg.tool_calls:     # run each tool it asked for
            args = json.loads(call.function.arguments or "{}")
            print(f"  [tool] {call.function.name}({args})")
            try:
                result = TOOLS[call.function.name](**args)
            except Exception as e:
                result = f"Error: {e}"
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})