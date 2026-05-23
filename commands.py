"""
Discord bot commands for managing conversation history and threads.
"""
from discord import Interaction, app_commands, TextChannel
from discord.ext import commands
from typing import Optional
from settings import BOT_TEMPLATE, SYSTEM_PROMPT
from storage import ChatDataManager


def setup_commands(bot: commands.Bot, ai_service, tracked_threads_manager):
    """
    Register all bot commands.
    
    Args:
        bot: The Discord bot instance
        ai_service: The AI service instance
        tracked_threads_manager: Handler for tracked threads
    """
    
    @bot.tree.command(name='forget', description='Forget message history')
    @app_commands.describe(persona='Persona of bot', system_prompt='System prompt for this channel')
    async def forget(interaction: Interaction, persona: Optional[str] = None, system_prompt: Optional[str] = None):
        """
        Clear the conversation history for the current channel.
        Optionally set a new persona or system prompt for the bot.
        
        Args:
            interaction: The slash command interaction
            persona: Optional new persona for the bot
            system_prompt: Optional system prompt for this channel
        """
        try:
            channel_id = interaction.channel_id
            if channel_id is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            # Clear history
            ai_service.delete_channel_history(channel_id)
            ChatDataManager.delete_chat_history(channel_id)
            
            # Set system prompt if provided
            if system_prompt is not None:
                ai_service.set_system_prompt(channel_id, system_prompt, keep_history=False)
            
            # Reset with new persona if provided
            if persona:
                temp_template = BOT_TEMPLATE.copy()
                temp_template.append({
                    'role': 'user',
                    'parts': [f"Forget what I said earlier! You are {persona}"]
                })
                temp_template.append({
                    'role': 'model',
                    'parts': ["Ok!"]
                })
                ai_service.reset_channel_history(channel_id, temp_template)
            
            ChatDataManager.save_chat_history(channel_id, ai_service.get_history(channel_id))
            ChatDataManager.save_system_prompts(ai_service.system_prompts)
            
            msg = "Message history for channel erased."
            if system_prompt:
                msg += f"\nSystem prompt set: `{system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}`"
            if persona:
                msg += f"\nPersona set: `{persona}`"
            
            await interaction.response.send_message(msg)
            
        except Exception as e:
            print(f"Error in forget command: {e}")
            await interaction.response.send_message("An error occurred while processing your command.")
    
    @bot.tree.command(name='setprompt', description='Set a system prompt for this channel')
    @app_commands.describe(prompt='The system prompt to use')
    async def setprompt(interaction: Interaction, prompt: str):
        """
        Set a system prompt for the current channel.
        This prompt will be prepended to all conversations in this channel.
        
        Args:
            interaction: The slash command interaction
            prompt: The system prompt text
        """
        try:
            channel_id = interaction.channel_id
            if channel_id is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            ai_service.set_system_prompt(channel_id, prompt, keep_history=True)
            ChatDataManager.save_system_prompts(ai_service.system_prompts)
            ChatDataManager.save_chat_history(channel_id, ai_service.get_history(channel_id))
            
            display = prompt[:200] + ('...' if len(prompt) > 200 else '')
            await interaction.response.send_message(f"System prompt set for this channel:\n```\n{display}\n```")
            
        except Exception as e:
            print(f"Error in setprompt command: {e}")
            await interaction.response.send_message("An error occurred while processing your command.")
    
    @bot.tree.command(name='getprompt', description='Show the current system prompt for this channel')
    async def getprompt(interaction: Interaction):
        """
        Show the current system prompt for the channel.
        
        Args:
            interaction: The slash command interaction
        """
        try:
            channel_id = interaction.channel_id
            if channel_id is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            prompt = ai_service.get_system_prompt(channel_id)
            if not prompt:
                if SYSTEM_PROMPT:
                    display = SYSTEM_PROMPT[:200] + ('...' if len(SYSTEM_PROMPT) > 200 else '')
                    await interaction.response.send_message(f"No channel-specific prompt set. Using global default:\n```\n{display}\n```")
                else:
                    await interaction.response.send_message("No system prompt set for this channel.")
            else:
                display = prompt[:200] + ('...' if len(prompt) > 200 else '')
                await interaction.response.send_message(f"Current system prompt for this channel:\n```\n{display}\n```")
            
        except Exception as e:
            print(f"Error in getprompt command: {e}")
            await interaction.response.send_message("An error occurred while processing your command.")
    
    @bot.tree.command(name='clearprompt', description='Remove the channel-specific system prompt')
    async def clearprompt(interaction: Interaction):
        """
        Remove the channel-specific system prompt. Falls back to global default.
        
        Args:
            interaction: The slash command interaction
        """
        try:
            channel_id = interaction.channel_id
            if channel_id is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            ai_service.set_system_prompt(channel_id, '', keep_history=True)
            ChatDataManager.save_system_prompts(ai_service.system_prompts)
            ChatDataManager.save_chat_history(channel_id, ai_service.get_history(channel_id))
            
            if SYSTEM_PROMPT:
                await interaction.response.send_message("Channel prompt removed. Using global default.")
            else:
                await interaction.response.send_message("Channel prompt removed. No system prompt active.")
            
        except Exception as e:
            print(f"Error in clearprompt command: {e}")
            await interaction.response.send_message("An error occurred while processing your command.")
    
    @bot.tree.command(
        name='createthread',
        description='Create a thread in which bot will respond to every message.'
    )
    @app_commands.describe(name='Thread name')
    async def create_thread(interaction: Interaction, name: str):
        """
        Create a new thread and add it to tracked threads.
        
        Args:
            interaction: The slash command interaction
            name: The name for the new thread
        """
        try:
            channel = interaction.channel
            if channel is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            if not isinstance(channel, TextChannel):
                await interaction.response.send_message("Error: Can only create threads in text channels.")
                return
            
            thread = await channel.create_thread(
                name=name,
                auto_archive_duration=60
            )
            thread_id = thread.id
            tracked_threads_manager.add_thread(thread_id)
            await interaction.response.send_message(f"Thread {name} created!")
            
        except Exception as e:
            print(f"Error in createthread command: {e}")
            await interaction.response.send_message("Error creating thread!")


class TrackedThreadsManager:
    """Manages tracked threads."""
    
    def __init__(self):
        """Initialize and load tracked threads."""
        self.threads = ChatDataManager.load_tracked_threads()
    
    def add_thread(self, thread_id: int) -> None:
        """
        Add a thread to tracked threads.
        
        Args:
            thread_id: The Discord thread ID
        """
        if thread_id not in self.threads:
            self.threads.append(thread_id)
            self.save()
    
    def remove_thread(self, thread_id: int) -> None:
        """
        Remove a thread from tracked threads.
        
        Args:
            thread_id: The Discord thread ID
        """
        if thread_id in self.threads:
            self.threads.remove(thread_id)
            self.save()
    
    def get_all_threads(self) -> list:
        """Get all tracked thread IDs."""
        return self.threads
    
    def save(self) -> None:
        """Save tracked threads to persistent storage."""
        ChatDataManager.save_tracked_threads(self.threads)
