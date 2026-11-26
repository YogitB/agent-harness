import os, json, subprocess
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import time


load_dotenv()
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
MODEL = "openai/gpt-oss-120b"

# 1. The tools the AI is allowed to use
def list_files(path="."):
    return "\n".join(os.listdir(path))

def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()[:4000]
def fetch_url(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "agent-harness"})
        r.raise_for_status()
    except Exception as e:
        return f"Error fetching {url}: {e}"
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return text[:4000]
def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {path}"

def run_command(command):
    ok = input(f"  Agent wants to run: {command}\n  Allow? (y/n) ")
    if ok.lower() != "y":
        return "User denied the command."
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr)[:4000] or "(no output)"

def edit_file(path, old, new):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if old not in text:
        return "Error: text to replace not found."
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new, 1))
    return f"Edited {path}"

TOOLS = {"list_files": list_files, "read_file": read_file, "write_file": write_file,
         "run_command": run_command, "edit_file": edit_file, "fetch_url": fetch_url}

# 2. Describe the tools so the AI knows they exist
TOOL_SPECS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files in a folder",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a text file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command on Windows and get its output",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace one exact piece of text in a file with new text",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
        "required": ["path", "old", "new"]}}},
    {"type": "function", "function": {"name": "fetch_url", "description": "Download a web page and return its readable text",
        "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "Full URL starting with http"}},
        "required": ["url"]}}},
]


SYSTEM = {"role": "system", "content": f"""You are a coding agent on Windows.
Working folder: {os.getcwd()}
Rules:
- Look at files before changing them.
- Use edit_file for small changes and write_file only for new files.
- After writing code, run it to check that it works, and fix any errors.
- Keep answers short.
- When the user mentions a website or URL, use fetch_url to read it instead of guessing.
- Run Python files with: python filename.py"""}
HISTORY_FILE = "history.json"
MAX_MESSAGES = 40 #Number of how many recent messagse that the agent remembers


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            old = json.load(f)
        print(f"(Loaded {len(old)} old messages)")
        return [SYSTEM] + old
    return [SYSTEM]

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages[1:], f, indent=2)   # skip the system prompt
def trim_history():
    global messages
    if len(messages) - 1 <= MAX_MESSAGES:
        return
    recent = messages[-MAX_MESSAGES:]
    # don't start on a tool result whose tool call got cut off
    while recent and recent[0].get("role") == "tool":
        recent.pop(0)
    messages = [SYSTEM] + recent
messages = load_history()

# 3. The loop
while True:
    user = input("\nYou: ")
    if user.lower() in ("quit", "exit"):
        break
    if user.lower() == "reset":
        messages = [SYSTEM]
        save_history()
        print("(Memory wiped)")
        continue
    messages.append({"role": "user", "content": user})
    trim_history()

    while True:
        try:
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SPECS)
        except Exception as e:
            if "429" in str(e):
                print("  (rate limited, waiting 5s...)")
                time.sleep(5)
                continue
            if "tool call validation failed" in str(e):
                messages.append({"role": "user", "content": "That tool doesn't exist. Only use: " + ", ".join(TOOLS)})
                continue
            print("\nError:", e)
            break

        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            print("\nAgent:", msg.content)
            save_history()
            break

        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            print(f"  [tool] {call.function.name}({args})")
            try:
                result = TOOLS[call.function.name](**args)
            except Exception as e:
                result = f"Error: {e}"
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})