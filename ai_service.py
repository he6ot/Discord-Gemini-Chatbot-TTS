"""
AI service layer for interacting with Google's Generative AI API.
Handles chat session management and response generation.
"""
import base64
import traceback
from enum import Enum
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types
from settings import (
    GOOGLE_AI_KEY,
    TEXT_GENERATION_CONFIG,
    SAFETY_SETTINGS,
    BOT_TEMPLATE,
    SYSTEM_PROMPT
)
from storage import log_error


def _sanitize_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert enum objects and old SDK types in history data to plain dicts/strings."""
    BASIC_TYPES = (str, int, float, bool, type(None), bytes)
    SEEN = set()
    KNOWN_ATTRS = ['text', 'inline_data', 'function_call', 'function_response',
                   'code_execution_result', 'executable_code', 'file_data',
                   'thought', 'thinking', 'role', 'outcome', 'language',
                   'name', 'args', 'response', 'mime_type', 'data', 'uri',
                   'file_uri', 'video_metadata']

    def _convert(obj: Any) -> Any:
        obj_id = id(obj)
        if obj_id in SEEN:
            return str(obj)
        SEEN.add(obj_id)

        try:
            if isinstance(obj, BASIC_TYPES):
                return obj
            if isinstance(obj, Enum):
                return obj.name
            if isinstance(obj, dict):
                return {str(k): _convert(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_convert(item) for item in obj]
            if hasattr(obj, 'model_dump'):
                return _convert(obj.model_dump())
            if hasattr(obj, 'dict'):
                return _convert(obj.dict())
            if hasattr(obj, 'to_dict'):
                return _convert(obj.to_dict())

            result = {}
            for attr in KNOWN_ATTRS:
                try:
                    val = getattr(obj, attr, None)
                    if val is not None:
                        result[attr] = _convert(val)
                except Exception:
                    pass

            if hasattr(obj, '__dict__'):
                try:
                    for k, v in vars(obj).items():
                        if not k.startswith('_') and k not in result:
                            result[k] = _convert(v)
                except TypeError:
                    pass

            if result:
                return result
            return str(obj)
        finally:
            SEEN.discard(obj_id)

    try:
        return _convert(history)
    except Exception:
        return []


def _build_parts_for_api(parts: List[Dict[str, Any]]) -> List[Any]:
    """Convert stored history parts into types.Part objects for the API."""
    result = []
    for part in parts:
        if isinstance(part, str):
            result.append(types.Part.from_text(text=part))
        elif isinstance(part, dict):
            if 'text' in part:
                result.append(types.Part.from_text(text=part['text']))
            elif 'inline_data' in part:
                inline = part['inline_data']
                data = inline.get('data', '')
                mime_type = inline.get('mime_type', 'application/octet-stream')
                if isinstance(data, str):
                    try:
                        data_bytes = base64.b64decode(data)
                    except Exception:
                        data_bytes = data.encode('utf-8', errors='ignore')
                else:
                    data_bytes = data
                result.append(types.Part.from_bytes(data=data_bytes, mime_type=mime_type))
            elif 'function_call' in part:
                fc = part['function_call']
                result.append(types.Part.from_function_call(
                    name=fc.get('name', ''),
                    args=fc.get('args', {})
                ))
            elif 'function_response' in part:
                fr = part['function_response']
                result.append(types.Part.from_function_response(
                    name=fr.get('name', ''),
                    response=fr.get('response', {})
                ))
        else:
            result.append(types.Part.from_text(text=str(part)))
    return result


class AIService:
    """Manages interactions with Google's Generative AI API."""
    
    def __init__(self):
        """Initialize the AI service with configuration."""
        self.client = genai.Client(api_key=GOOGLE_AI_KEY)
        self.model_name = "gemini-flash-latest"
        self.generation_config = TEXT_GENERATION_CONFIG
        self.safety_settings = SAFETY_SETTINGS
        self.message_history: Dict[int, Any] = {}
        self.chat_sessions: Dict[int, Any] = {}
        self.system_prompts: Dict[int, str] = {}
    
    def load_history(self, history_data: Dict[int, List[Dict[str, Any]]]) -> None:
        """
        Load previously saved chat history.
        Strips old system prompt entries that were stored as user messages.
        
        Args:
            history_data: Dictionary mapping channel IDs to chat histories
        """
        for channel_id, history in history_data.items():
            sanitized = _sanitize_history(history)
            if not sanitized:
                continue
            
            cleaned = self._strip_old_system_prompt_entries(sanitized)
            
            try:
                api_history = []
                for entry in cleaned:
                    role = entry.get('role', 'user')
                    parts = _build_parts_for_api(entry.get('parts', []))
                    api_history.append(types.Content(role=role, parts=parts))
                
                self.chat_sessions[channel_id] = self.client.aio.chats.create(
                    model=self.model_name,
                    history=api_history
                )
                self.message_history[channel_id] = cleaned
            except Exception:
                pass
    
    def _strip_old_system_prompt_entries(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove old-style system prompt entries from history.
        
        The old format stored prompts as:
        - {"role": "user", "parts": [{"text": "<prompt>"}]}
        - {"role": "model", "parts": [{"text": "Understood!"}]}
        
        These are now passed via system_instruction instead.
        """
        cleaned = []
        skip_next = False
        for i, entry in enumerate(history):
            if skip_next:
                skip_next = False
                # Check if this is the "Understood!" response
                parts = entry.get('parts', [])
                if len(parts) == 1 and isinstance(parts[0], dict):
                    if parts[0].get('text') == 'Understood!':
                        continue
                # Not an Understood! response, don't skip
                cleaned.append(entry)
                continue
            
            if entry.get('role') == 'user':
                parts = entry.get('parts', [])
                # Check if this looks like a system prompt entry
                # Old format: single text part that doesn't look like a normal message
                if len(parts) == 1 and isinstance(parts[0], dict) and 'text' in parts[0]:
                    text = parts[0]['text']
                    # Heuristic: system prompts are typically long, instructional texts
                    # or start with phrases like "You are", "Forget what", "Act as"
                    lower_text = text.lower()
                    is_system_like = (
                        len(text) > 50 and (
                            lower_text.startswith('you are') or
                            lower_text.startswith('ты ') or
                            lower_text.startswith('act as') or
                            lower_text.startswith('forget what') or
                            lower_text.startswith('забудь') or
                            'system prompt' in lower_text or
                            'system instruction' in lower_text or
                            'your role' in lower_text or
                            'your persona' in lower_text
                        )
                    )
                    if is_system_like:
                        skip_next = True
                        continue
            
            cleaned.append(entry)
        
        return cleaned
    
    def load_system_prompts(self, prompts: Dict[int, str]) -> None:
        """
        Load system prompts from persistent storage.
        
        Args:
            prompts: Dictionary mapping channel IDs to system prompt strings
        """
        self.system_prompts = prompts
    
    def _get_system_instruction(self, channel_id: int) -> Optional[str]:
        """Get system instruction for API config."""
        prompt = self.system_prompts.get(channel_id, '')
        if prompt:
            return prompt
        return SYSTEM_PROMPT if SYSTEM_PROMPT else None

    async def generate_response(self, channel_id: int, attachments: List[Dict[str, Any]], text: str) -> str:
        """
        Generate a response from the AI model for the given input.
        
        Args:
            channel_id: Discord channel ID for context
            attachments: List of attachment data dictionaries
            text: The user's message text
            
        Returns:
            The AI model's response text
            
        Raises:
            Exception: If the API call fails
        """
        response: Optional[Any] = None
        try:
            prompt_parts: List[Any] = []
            for attachment in attachments:
                prompt_parts.append(
                    types.Part.from_bytes(
                        data=attachment["data"],
                        mime_type=attachment["mime_type"]
                    )
                )
            prompt_parts.append(text)
            
            if channel_id not in self.chat_sessions:
                sanitized_template = _sanitize_history(BOT_TEMPLATE)
                api_history = []
                for entry in sanitized_template:
                    role = entry.get('role', 'user')
                    parts = _build_parts_for_api(entry.get('parts', []))
                    api_history.append(types.Content(role=role, parts=parts))
                
                self.chat_sessions[channel_id] = self.client.aio.chats.create(
                    model=self.model_name,
                    history=api_history if api_history else None
                )
                self.message_history[channel_id] = sanitized_template
            
            system_instr = self._get_system_instruction(channel_id)
            response = await self.chat_sessions[channel_id].send_message(
                message=prompt_parts,
                config=types.GenerateContentConfig(
                    **self.generation_config,
                    system_instruction=system_instr,
                    safety_settings=[
                        types.SafetySetting(**s) for s in self.safety_settings
                    ] if self.safety_settings else None
                )
            )
            
            user_parts = [{"text": text}]
            if attachments:
                for att in attachments:
                    user_parts.insert(0, {
                        "inline_data": {
                            "mime_type": att["mime_type"],
                            "data": base64.b64encode(att["data"]).decode('utf-8')
                        }
                    })
            self.message_history[channel_id].append({"role": "user", "parts": user_parts})
            
            if response and response.text:
                self.message_history[channel_id].append({"role": "model", "parts": [{"text": response.text}]})
            
            return response.text if response else ""
            
        except Exception as e:
            try:
                history_info = str(self.message_history.get(channel_id, "N/A"))
                candidates = str(response.candidates) if response else "N/A"
                parts = str(response.parts) if response else "N/A"
                prompt_feedbacks = str(response.prompt_feedback) if response else "N/A"
            except:
                history_info = "N/A"
                candidates = "N/A"
                parts = "N/A"
                prompt_feedbacks = "N/A"
            
            log_error(
                text=text,
                error_traceback=traceback.format_exc(),
                history=history_info,
                candidates=candidates,
                parts=parts,
                prompt_feedbacks=prompt_feedbacks
            )
            raise
    
    def reset_channel_history(self, channel_id: int, custom_template: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Reset the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            custom_template: Optional custom initial template for the chat
        """
        if custom_template is None:
            custom_template = BOT_TEMPLATE
        
        sanitized = _sanitize_history(custom_template)
        api_history = []
        for entry in sanitized:
            role = entry.get('role', 'user')
            parts = _build_parts_for_api(entry.get('parts', []))
            api_history.append(types.Content(role=role, parts=parts))
        
        self.chat_sessions[channel_id] = self.client.aio.chats.create(
            model=self.model_name,
            history=api_history if api_history else None
        )
        self.message_history[channel_id] = sanitized
    
    def delete_channel_history(self, channel_id: int) -> None:
        """
        Delete chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.message_history:
            del self.message_history[channel_id]
        if channel_id in self.chat_sessions:
            del self.chat_sessions[channel_id]
    
    def set_system_prompt(self, channel_id: int, prompt: str, keep_history: bool = True) -> List[Dict[str, Any]]:
        """
        Set or update the system prompt for a channel.
        The prompt is passed via system_instruction, not stored in history.
        
        Args:
            channel_id: Discord channel ID
            prompt: The system prompt text
            keep_history: If True, keep existing conversation history; if False, reset
            
        Returns:
            The new message history as a list of dicts
        """
        if prompt:
            self.system_prompts[channel_id] = prompt
        elif channel_id in self.system_prompts:
            del self.system_prompts[channel_id]
        
        if not keep_history or channel_id not in self.message_history:
            sanitized = _sanitize_history(BOT_TEMPLATE)
            self.message_history[channel_id] = sanitized
        
        api_history = []
        for entry in self.message_history[channel_id]:
            role = entry.get('role', 'user')
            parts = _build_parts_for_api(entry.get('parts', []))
            api_history.append(types.Content(role=role, parts=parts))
        
        self.chat_sessions[channel_id] = self.client.aio.chats.create(
            model=self.model_name,
            history=api_history if api_history else None
        )
        
        return self.message_history[channel_id]
    
    def get_system_prompt(self, channel_id: int) -> str:
        """
        Get the system prompt for a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            The system prompt string, or empty string if none set
        """
        return self.system_prompts.get(channel_id, '')
    
    def get_history(self, channel_id: int) -> List[Dict[str, Any]]:
        """
        Get the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            The chat history list
        """
        if channel_id in self.message_history:
            return self.message_history[channel_id]
        return []
