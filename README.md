# Jarvis AI Assistant

A modular AI assistant built using Python inspired by Iron Man's Jarvis.

## Features

- Natural language command processing
- Intent parsing system
- Browser automation
- Persistent memory storage
- Voice output system
- Modular execution engine

## Architecture

```text
User Input
   ↓
main.py
   ↓
intent_parser.py
   ↓
executor.py
   ↓
browser.py / memory.py / speak.py
```

## Project Files

- main.py → main program loop
- intent_parser.py → detects user intent
- executor.py → executes commands
- browser.py → opens browser tasks
- memory.py → stores memory
- speak.py → text to speech
- config.py → configuration settings

## Future Improvements

- Wake word detection
- Local LLM integration
- Autonomous decision making
- Long term memory system

## Tech Stack

- Python
- JSON
- LLM APIs
- Speech Processing
