"""
Environment and configuration settings for the Gemini Discord Bot.
Loads all configuration from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')
load_dotenv('.env.development')

# API Keys
GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Tracked channels where the bot responds to all messages
TRACKED_CHANNELS = [
    # channel_id_1,
    # thread_id_2,
]

# AI Model Configuration
TEXT_GENERATION_CONFIG = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    # "max_output_tokens": 1024,
}

IMAGE_GENERATION_CONFIG = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    # "max_output_tokens": 1024,
}

# Safety settings for content filtering
SAFETY_SETTINGS = [
    # {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    # {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    # {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    # {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# Bot personality/system prompt template
BOT_TEMPLATE = [
    # {'role':'user','parts': ["Hi!"]},
    # {'role':'model','parts': ["Hello! I am a Discord bot!"]},
    # {'role':'user','parts': ["Please give short and concise answers!"]},
    # {'role':'model','parts': ["I will try my best!"]},
]

# Message splitting configuration
MAX_MESSAGE_LENGTH = 1700

# Discord bot configuration
BOT_PREFIX = []
BOT_ACTIVITY = "with your feelings"

# TTS Configuration
TTS_ENABLED = os.getenv('TTS_ENABLED', 'false').lower() == 'true'
TTS_VOICE_NAME = os.getenv('TTS_VOICE_NAME', 'Kore')
TTS_LANGUAGE_CODE = os.getenv('TTS_LANGUAGE_CODE', 'ru-RU')
TTS_MODEL = os.getenv('TTS_MODEL', 'gemini-3.1-flash-tts-preview')
TTS_PROMPT = os.getenv('TTS_PROMPT', 'Speak in a clear, natural voice.')
TTS_MAX_LENGTH = 10000  # Max text length for TTS
