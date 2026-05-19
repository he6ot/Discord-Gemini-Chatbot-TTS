"""
TTS service using Google Gemini Generative AI API.
Synthesizes text to audio using multimodal output and plays in Discord voice channels.
"""
import os
import asyncio
import tempfile
import traceback
from typing import Optional, Tuple
import google.generativeai as genai
import discord
from settings import (
    GOOGLE_AI_KEY,
    TTS_ENABLED,
    TTS_MAX_LENGTH,
    TTS_MODEL,
    TTS_VOICE_NAME,
)
from storage import log_error


class TTSService:
    """Manages text-to-speech synthesis using Gemini API and voice channel playback."""

    def __init__(self):
        """Initialize TTS client using API Key."""
        if not TTS_ENABLED:
            self.client = None
            return

        genai.configure(api_key=GOOGLE_AI_KEY)
        self.model = genai.GenerativeModel(model_name=TTS_MODEL)

    async def synthesize_speech(self, text: str) -> Optional[Tuple[bytes, str]]:
        """
        Synthesize speech from text using Gemini multimodal capabilities.

        Returns:
            Tuple of (audio_bytes, mime_type) or None if failed.
        """
        if not TTS_ENABLED:
            return None

        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8')

            text = text[:TTS_MAX_LENGTH]
            prompt = f"Read this: {text}"

            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": TTS_VOICE_NAME
                            }
                        }
                    }
                }
            )

            audio_data = None
            mime_type = None

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_data = part.inline_data.data
                        mime_type = getattr(part.inline_data, 'mime_type', 'audio/mpeg')
                        break
                    elif hasattr(part, 'data') and part.data:
                        audio_data = part.data
                        mime_type = 'audio/mpeg'

            if audio_data:
                print(f"TTS Success: Received {len(audio_data)} bytes (mime: {mime_type})")
                if len(audio_data) > 10:
                    print(f"TTS Debug: First bytes: {audio_data[:10].hex()}")
                return audio_data, mime_type
            else:
                print("TTS Error: No audio data found in response parts")
                return None

        except Exception as e:
            print(f"TTS Error detail: {str(e)}")
            log_error(
                text=text,
                error_traceback=traceback.format_exc(),
                history="Gemini TTS synthesis failed",
                candidates="N/A",
                parts="N/A",
                prompt_feedbacks="N/A"
            )
            return None

    async def get_largest_voice_channel(self, guild: discord.Guild) -> Optional[discord.VoiceChannel]:
        voice_channels = [c for c in guild.voice_channels if c.members]
        if not voice_channels:
            return None
        return max(voice_channels, key=lambda c: len(c.members))

    async def play_in_voice_channel(
        self,
        voice_channel: discord.VoiceChannel,
        text: str,
        bot: discord.Client,
    ) -> bool:
        if not TTS_ENABLED:
            return False

        result = await self.synthesize_speech(text)
        if not result:
            return False

        audio_content, mime_type = result

        # Определяем расширение по MIME-типу от Gemini
        ext = '.mp3'
        is_pcm = False
        if mime_type:
            mime_type = mime_type.lower()
            if 'wav' in mime_type:
                ext = '.wav'
            elif 'ogg' in mime_type:
                ext = '.ogg'
            elif 'webm' in mime_type:
                ext = '.webm'
            elif 'mpeg' in mime_type or 'mp3' in mime_type:
                ext = '.mp3'
            elif 'pcm' in mime_type or 'l16' in mime_type:
                ext = '.pcm'
                is_pcm = True
        
        # Если заголовок MP3 отсутствует (первые байты не FF FB или ID3), 
        # но размер данных большой — вероятно это сырой PCM
        if ext == '.mp3' and len(audio_content) > 4:
            if not (audio_content.startswith(b'\xff\xfb') or audio_content.startswith(b'ID3')):
                print("TTS Debug: MP3 header not found, treating as raw PCM")
                is_pcm = True
                ext = '.pcm'

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
            f.write(audio_content)
            temp_path = f.name

        print(f"TTS Debug: Saved audio to {temp_path}, size: {os.path.getsize(temp_path)} bytes")

        voice_client = None
        guild = voice_channel.guild

        try:
            # Если бот уже в голосовом канале на этом сервере — перемещаемся
            if guild.voice_client is not None:
                voice_client = guild.voice_client
                print(f"TTS Debug: Moving to {voice_channel.name}")
                await voice_client.move_to(voice_channel)
            else:
                print(f"TTS Debug: Connecting to {voice_channel.name}")
                voice_client = await voice_channel.connect(timeout=60.0, self_deaf=True)

            def after_callback(error):
                if error:
                    print(f"TTS Voice playback error: {error}")
                else:
                    print("TTS Voice playback finished (callback)")

            # Улучшенные параметры FFmpeg для предотвращения ошибок заголовка
            ffmpeg_before_options = '-analyzeduration 20M -probesize 20M'
            
            # Если это сырой PCM, нужно подсказать FFmpeg формат (обычно 24kHz s16le mono для Gemini)
            if is_pcm:
                ffmpeg_before_options += ' -f s16le -ar 24000 -ac 1'
            
            ffmpeg_options = '-loglevel error'

            voice_client.play(
                discord.FFmpegPCMAudio(
                    temp_path, 
                    before_options=ffmpeg_before_options,
                    options=ffmpeg_options
                ),
                after=after_callback
            )

            print(f"Playing audio in {voice_channel.name}...")

            await asyncio.sleep(1)

            while voice_client.is_playing():
                await asyncio.sleep(0.5)

            print("Finished playing audio.")

        except Exception as e:
            print(f"Voice playback/connection error: {e}")
            log_error(
                text=text,
                error_traceback=traceback.format_exc(),
                history="Voice playback failed",
                candidates="N/A",
                parts="N/A",
                prompt_feedbacks="N/A"
            )
            return False

        finally:
            if voice_client is not None:
                try:
                    await voice_client.disconnect()
                except Exception as e:
                    print(f"Error disconnecting voice client: {e}")
            try:
                os.remove(temp_path)
            except Exception:
                pass

        return True


async def speak_response(guild: discord.Guild, text: str, bot: discord.Client, tts_service: TTSService) -> bool:
    if not TTS_ENABLED:
        return False

    voice_channel = await tts_service.get_largest_voice_channel(guild)
    if not voice_channel:
        return False

    return await tts_service.play_in_voice_channel(voice_channel, text, bot)