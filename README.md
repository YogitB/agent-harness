agent-harness

What it is: (a coding agent that runs in your terminal, built with Python).

What it can do
- list, read, write and edit files
- run commands (asks you first)
- read web pages with fetch_url
- remembers past chats in history.json

Setup
1. git clone https://github.com/yogitb/agent-harness.git
2. python -m venv .venv  then  .venv\Scripts\activate
3. pip install -r requirements.txt
4. Make a .env file with: GROQ_API_KEY=your_key_here
5. python agent.py

Commands
- type `reset` to wipe memory
- type `exit` to quit

What I learned:
- I learned how an AI agent works and what is required for it to function
- I engineered throught the mess of an AI agent's chat history. I used history.json and the .gitignore files to teach me about git and keeping private information out.
- I learned about the context limits and how the history keeps on growing
- I learned how the model has limits which is why it breaks whenever it makes up tools as per how I programmed it to
- Safety of the user. run_command asks the user before it runs anything symbolizing the importance of consent.

