
import os

def speak(text):
    if not text or not isinstance(text, str):
        return

    os.system(f'say "{text}"')