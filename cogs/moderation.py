import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
import logging
import re
from pathlib import Path

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clear_start_points = {}  # Store start points per channel
        self.data_dir = 'data'
        self.blocked_words_file = os.path.join(self.data_dir, 'blocked_words.json')
        self.blocked_words: Dict[str, Set[str]] = {}
        self._file_lock = asyncio.Lock()
        self._users_with_blocks: Set[str] = set()
        self.logger = logging.getLogger(__name__)
        self.nga_data_file = Path('data/nga_replies.json')
        self.triggers = self.load_triggers()

        # Constants
        self.BULK_DELETE_LIMIT = 100
        self.MESSAGE_AGE_LIMIT = 14  # Days for bulk delete
        self.CONFIRMATION_DELAY = 3  # Seconds

        # Ensure data directory exists and load data
        self._ensure_data_directory()
        self._load_blocked_words()

    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_blocked_words(self):
        """Load blocked words from JSON file with error handling"""
        if not os.path.exists(self.blocked_words_file):
            return
        
        try:
            with open(self.blocked_words_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert lists to sets for O(1) lookup performance
                self.blocked_words = {
                    user_id: set(words) for user_id, words in data.items()
                }
                self._users_with_blocks = set(self.blocked_words.keys())
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Error loading blocked words: {e}")
            self.blocked_words = {}
            self._users_with_blocks = set()

    async def _save_blocked_words(self):
        """Save blocked words to JSON file asynchronously with file locking"""
        async with self._file_lock:
            try:
                # Convert sets back to lists for JSON serialization
                data_to_save = {
                    user_id: list(words) for user_id, words in self.blocked_words.items()
                }
                
                # Write to temporary file first, then rename for atomic operation
                temp_file = self.blocked_words_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                # Atomic rename
                os.replace(temp_file, self.blocked_words_file)
                
            except Exception as e:
                self.logger.error(f"Error saving blocked words: {e}")

    def load_triggers(self):
        try:
            if self.nga_data_file.exists():
                with open(self.nga_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading triggers: {e}")
            return {}

    def save_triggers(self):
        """Save trigger data to JSON file"""
        try:
            # Ensure data directory exists
            self.nga_data_file.parent.mkdir(exist_ok=True)
            with open(self.nga_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.triggers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving triggers: {e}")

    def is_url(self, text):
        """Check if text is a URL"""
        url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            re.IGNORECASE
        )
        return bool(url_pattern.match(text.strip()))

    # Keep the !eat command as a traditional command (not slash)
    @commands.command(name="eat", help="Clear messages between start and end points")
    async def clear_messages(self, ctx, action: Optional[str] = None):
        """Clear messages between start and end points or up to a replied message"""
        
        if not self._has_permission(ctx.author):
            await self._send_temp_message(ctx, "Hmph! You think you can just order me around? You need proper permissions first, dummy! 💢", 5)
            return

        if action == "start":
            await self._handle_start_point(ctx)
        elif action == "end":
            await self._handle_end_point(ctx)
        else:
            await self._handle_single_clear(ctx)

    def _has_permission(self, user: discord.Member) -> bool:
        """Check if user has manage messages permission"""
        return user.guild_permissions.manage_messages

    async def _send_temp_message(self, ctx, content: str, delay: int):
        """Send a temporary message that deletes after specified delay"""
        msg = await ctx.send(content)
        await msg.delete(delay=delay)

    async def _handle_start_point(self, ctx):
        """Handle setting the start point for clearing"""
        if not ctx.message.reference or not ctx.message.reference.message_id:
            await self._send_temp_message(
                ctx, 
                "Ugh, seriously? You need to reply to a message to set the start point! Do I have to explain everything? 🙄", 
                5
            )
            return

        try:
            start_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            self.clear_start_points[ctx.channel.id] = start_message.id
            
            confirmation = await ctx.send("Fine, fine... Start point set! Now don't mess up the end point! ✨")
            await asyncio.gather(
                confirmation.delete(delay=self.CONFIRMATION_DELAY),
                ctx.message.delete()
            )
        except discord.NotFound:
            await self._send_temp_message(ctx, "Are you kidding me?! I can't find that message! Pay attention next time! 😤", 5)

    async def _handle_end_point(self, ctx):
        """Handle clearing from start point to end point"""
        if ctx.channel.id not in self.clear_start_points:
            await self._send_temp_message(
                ctx, 
                "Hello?! You didn't set a start point yet! Use `!eat start` first, genius! 😒", 
                5
            )
            return

        if not ctx.message.reference or not ctx.message.reference.message_id:
            await self._send_temp_message(
                ctx, 
                "Do I really have to spell it out? Reply to a message to set the end point! 🤦‍♀️", 
                5
            )
            return

        try:
            start_message_id = self.clear_start_points[ctx.channel.id]
            start_message = await ctx.channel.fetch_message(start_message_id)
            end_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)

            # Ensure proper chronological order
            if start_message.created_at > end_message.created_at:
                start_message, end_message = end_message, start_message

            messages_to_delete = await self._collect_messages_between(
                ctx.channel, 
                start_message, 
                end_message
            )
            messages_to_delete.append(ctx.message)

            if len(messages_to_delete) <= 1:
                await self._send_temp_message(ctx, "Hmm... There's nothing to clean up here. At least you tried! 😌", 5)
                return

            deleted_count = await self._delete_messages_efficiently(ctx.channel, messages_to_delete)
            
            # Clean up start point
            del self.clear_start_points[ctx.channel.id]
            
            await self._send_temp_message(
                ctx, 
                f"There! I cleaned up {deleted_count} messages for you. You're welcome~ ✨",
                self.CONFIRMATION_DELAY
            )

        except discord.NotFound:
            await self._send_temp_message(ctx, "Seriously?! One of those messages vanished! Are you trying to confuse me? 😠", 5)
        except Exception as e:
            await self._send_temp_message(ctx, f"Ugh, something went wrong... This is so embarrassing! 😳 Error: {str(e)}", 5)

    async def _handle_single_clear(self, ctx):
        """Handle clearing up to a replied message"""
        if not ctx.message.reference or not ctx.message.reference.message_id:
            await self._send_temp_message(
                ctx,
                "Listen carefully! Reply to a message, or use:\n"
                "`!eat start` - Set start point (reply to message)\n"
                "`!eat end` - Clear to end point (reply to message)\n"
                "Got it? Good! 📝",
                10
            )
            return

        try:
            target_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            
            # More efficient message collection
            messages_to_delete = []
            async for message in ctx.channel.history(
                limit=None, 
                before=ctx.message, 
                after=target_message
            ):
                messages_to_delete.append(message)
            
            messages_to_delete.append(ctx.message)
            
            if len(messages_to_delete) <= 1:
                await self._send_temp_message(ctx, "Hmm, there's nothing here to clean up! At least the place is tidy~ 😊", 5)
                return
            
            deleted_count = await self._delete_messages_efficiently(ctx.channel, messages_to_delete)
            await self._send_temp_message(
                ctx, 
                f"All done! Cleared {deleted_count} messages. I'm quite efficient, aren't I? 😏",
                self.CONFIRMATION_DELAY
            )
            
        except discord.NotFound:
            await self._send_temp_message(ctx, "That message is nowhere to be found! Did it run away from me? 🤨", 5)
        except Exception as e:
            await self._send_temp_message(ctx, f"Ugh, this is so frustrating! Something went wrong: {str(e)} 😤", 5)

    async def _collect_messages_between(
        self, 
        channel: discord.TextChannel, 
        start_message: discord.Message, 
        end_message: discord.Message
    ) -> List[discord.Message]:
        """Collect messages between two points efficiently"""
        messages = []
        
        # Use more efficient approach with limits
        async for message in channel.history(
            limit=None, 
            before=end_message, 
            after=start_message
        ):
            messages.append(message)
        
        # Include the boundary messages
        messages.extend([start_message, end_message])
        return messages

    async def _delete_messages_efficiently(
        self, 
        channel: discord.TextChannel, 
        messages: List[discord.Message]
    ) -> int:
        """Delete messages efficiently using bulk operations where possible"""
        if not messages:
            return 0
        
        deleted_count = 0
        from datetime import timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.MESSAGE_AGE_LIMIT)
        
        # Separate messages by age for optimal deletion strategy
        recent_messages = [msg for msg in messages if msg.created_at > cutoff_time]
        old_messages = [msg for msg in messages if msg.created_at <= cutoff_time]
        
        # Bulk delete recent messages in chunks
        deleted_count += await self._bulk_delete_messages(channel, recent_messages)
        
        # Delete old messages individually
        deleted_count += await self._delete_old_messages(old_messages)
        
        return deleted_count

    async def _bulk_delete_messages(
        self, 
        channel: discord.TextChannel, 
        messages: List[discord.Message]
    ) -> int:
        """Bulk delete recent messages in optimal chunks"""
        deleted_count = 0
        
        for i in range(0, len(messages), self.BULK_DELETE_LIMIT):
            chunk = messages[i:i + self.BULK_DELETE_LIMIT]
            try:
                if len(chunk) == 1:
                    await chunk[0].delete()
                else:
                    await channel.delete_messages(chunk)
                deleted_count += len(chunk)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                # Handle individual deletions for failed bulk operations
                for msg in chunk:
                    try:
                        await msg.delete()
                        deleted_count += 1
                    except (discord.Forbidden, discord.NotFound):
                        pass
        
        return deleted_count

    async def _delete_old_messages(self, messages: List[discord.Message]) -> int:
        """Delete old messages individually with error handling"""
        deleted_count = 0
        
        # Use semaphore to limit concurrent deletions
        semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent deletions
        
        async def delete_single_message(message):
            nonlocal deleted_count
            async with semaphore:
                try:
                    await message.delete()
                    deleted_count += 1
                except (discord.NotFound, discord.Forbidden):
                    pass
        
        # Delete messages concurrently but with limits
        tasks = [delete_single_message(msg) for msg in messages]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return deleted_count

    # Word blocking functionality with slash commands
    async def check_blocked_words(self, message: discord.Message) -> bool:
        """Optimized blocked word checking with early returns"""
        if message.author.bot:
            return False
        
        user_id = str(message.author.id)
        
        # Fast path: check if user has any blocked words
        if user_id not in self._users_with_blocks:
            return False
        
        blocked_words_for_user = self.blocked_words.get(user_id)
        if not blocked_words_for_user:
            return False
        
        message_content = message.content.lower()
        
        # Use any() for early termination
        if any(word in message_content for word in blocked_words_for_user):
            return await self._handle_blocked_message(message)
        
        return False

    async def _handle_blocked_message(self, message: discord.Message) -> bool:
        """Handle a message containing blocked words"""
        try:
            await message.delete()
            
            # Tika's sassy response to blocked words
            responses = [
                f"Nice try, {message.author.mention}! But I'm not letting that slip by~ 🙄",
                f"Uh-uh! {message.author.mention}, you know better than that! 😤",
                f"{message.author.mention}, really? I expected better from you... 💢",
                f"Nope! {message.author.mention}, that word is off-limits! 😏"
            ]
            
            import random
            warning_msg = await message.channel.send(
                random.choice(responses),
                delete_after=5
            )
            return True
            
        except discord.NotFound:
            # Message already deleted
            return True
        except discord.Forbidden:
            # No permission to delete
            self.logger.warning(f"No permission to delete message from {message.author}")
            return False

    @app_commands.command(name="blockword", description="Add a blocked word for a specific user")
    @app_commands.describe(
        user="The user to block the word for",
        word="The word to block"
    )
    async def block_word(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member, 
        word: str
    ):
        """Add a word to the blocked list for a specific user"""
        
        if not self._check_admin_permission(interaction.user):
            await interaction.response.send_message(
                "Excuse me?! You think you can just boss me around? You need administrator permissions for that! 😤",
                ephemeral=True
            )
            return
        
        # Validate and normalize word
        normalized_word = self._validate_and_normalize_word(word)
        if not normalized_word:
            await interaction.response.send_message(
                "Come on! Give me a proper word to block! That's not even valid! 🙄",
                ephemeral=True
            )
            return
        
        user_id = str(user.id)
        
        # Initialize user's blocked words set if needed
        if user_id not in self.blocked_words:
            self.blocked_words[user_id] = set()
            self._users_with_blocks.add(user_id)
        
        # Check if word is already blocked
        if normalized_word in self.blocked_words[user_id]:
            await interaction.response.send_message(
                f"Hello?! The word '{normalized_word}' is already blocked for {user.display_name}! Pay attention! 😒",
                ephemeral=True
            )
            return
        
        # Add the word
        self.blocked_words[user_id].add(normalized_word)
        await self._save_blocked_words()
        
        await interaction.response.send_message(
            f"Fine! I've blocked the word '{normalized_word}' for {user.display_name}. They better watch their language now! 😏",
            ephemeral=True
        )

    @app_commands.command(name="unblockword", description="Remove a blocked word for a specific user")
    @app_commands.describe(
        user="The user to unblock the word for",
        word="The word to unblock"
    )
    async def unblock_word(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member, 
        word: str
    ):
        """Remove a word from the blocked list for a specific user"""
        
        if not self._check_admin_permission(interaction.user):
            await interaction.response.send_message(
                "Nice try! But you need administrator permissions to boss me around like that! 💢",
                ephemeral=True
            )
            return
        
        normalized_word = self._validate_and_normalize_word(word)
        user_id = str(user.id)
        
        # Check if user has blocked words
        if user_id not in self.blocked_words or not self.blocked_words[user_id]:
            await interaction.response.send_message(
                f"Uh, {user.display_name} doesn't even have any blocked words! Are you sure you got the right person? 🤨",
                ephemeral=True
            )
            return
        
        # Check if word is blocked
        if normalized_word not in self.blocked_words[user_id]:
            await interaction.response.send_message(
                f"The word '{normalized_word}' isn't even blocked for {user.display_name}! Double-check next time! 😤",
                ephemeral=True
            )
            return
        
        # Remove the word
        self.blocked_words[user_id].discard(normalized_word)
        
        # Clean up empty sets
        if not self.blocked_words[user_id]:
            del self.blocked_words[user_id]
            self._users_with_blocks.discard(user_id)
        
        await self._save_blocked_words()
        
        await interaction.response.send_message(
            f"There! I unblocked the word '{normalized_word}' for {user.display_name}. They can say it again now~ 😌",
            ephemeral=True
        )

    async def check_nga_triggers(self, message):
        """Check for nga trigger words in messages"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Ignore if no guild
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        
        # Check if guild has any triggers
        if guild_id not in self.triggers or not self.triggers[guild_id]:
            return
        
        message_content = message.content.lower().strip()
        
        # Early return if message is empty
        if not message_content:
            return
        
        # Check each trigger
        for main_word, data in self.triggers[guild_id].items():
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(main_word) + r'\b'
            if re.search(pattern, message_content):
                await self.send_nga_reply(message, data)
                return
            
            # Check alternatives with word boundaries
            for alternative in data["alternatives"]:
                alt_pattern = r'\b' + re.escape(alternative) + r'\b'
                if re.search(alt_pattern, message_content):
                    await self.send_nga_reply(message, data)
                    return

    async def send_nga_reply(self, message, trigger_data):
        """Send the reply for a triggered word"""
        try:
            reply = trigger_data["reply"]
            
            # Check if reply is a URL (image/gif)
            if self.is_url(reply):
                embed = discord.Embed(color=0x3498db)
                embed.set_image(url=reply)
                await message.reply(embed=embed, mention_author=False)
            else:
                # Send as regular text
                await message.reply(reply, mention_author=False)
                
        except discord.HTTPException as e:
            self.logger.error(f"HTTP error sending nga reply: {e}")
        except discord.Forbidden:
            self.logger.warning(f"No permission to send message in {message.guild.name}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending nga reply: {e}")

    @app_commands.command(name="listblockedwords", description="List blocked words for a specific user")
    @app_commands.describe(user="The user to list blocked words for")
    async def list_blocked_words(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member
    ):
        """List all blocked words for a specific user"""
        
        if not self._check_admin_permission(interaction.user):
            await interaction.response.send_message(
                "Hmph! You don't have the authority to see that information! Administrator permissions required! 😠",
                ephemeral=True
            )
            return
        
        user_id = str(user.id)
        
        # Check if user has blocked words
        if user_id not in self.blocked_words or not self.blocked_words[user_id]:
            await interaction.response.send_message(
                f"{user.display_name} is clean! No blocked words at all. How refreshing~ 😊",
                ephemeral=True
            )
            return
        
        blocked_words_list = sorted(self.blocked_words[user_id])  # Sort for consistent display
        
        # Handle large lists by truncating if necessary
        max_display = 50
        if len(blocked_words_list) > max_display:
            displayed_words = blocked_words_list[:max_display]
            words_text = ", ".join(f"`{word}`" for word in displayed_words)
            words_text += f"\n... and {len(blocked_words_list) - max_display} more words! Wow, they really went overboard, huh?"
        else:
            words_text = ", ".join(f"`{word}`" for word in blocked_words_list)
        
        embed = discord.Embed(
            title=f"🚫 {user.display_name}'s Blocked Words",
            description=f"Here's what they can't say:\n{words_text}",
            color=0xFF0000
        )
        embed.set_footer(text=f"Total: {len(blocked_words_list)} word(s) - I'm keeping track! 📝")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearallblockedwords", description="Clear all blocked words for a specific user")
    @app_commands.describe(user="The user to clear all blocked words for")
    async def clear_all_blocked_words(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Clear all blocked words for a specific user"""
        
        if not self._check_admin_permission(interaction.user):
            await interaction.response.send_message(
                "Oh please! You think you can just waltz in here and clear everything? Administrator permissions first! 💢",
                ephemeral=True
            )
            return
        
        user_id = str(user.id)
        
        if user_id not in self.blocked_words or not self.blocked_words[user_id]:
            await interaction.response.send_message(
                f"{user.display_name} doesn't even have blocked words to clear! You're wasting my time~ 😒",
                ephemeral=True
            )
            return
        
        word_count = len(self.blocked_words[user_id])
        del self.blocked_words[user_id]
        self._users_with_blocks.discard(user_id)
        
        await self._save_blocked_words()
        
        await interaction.response.send_message(
            f"Fine, fine! I cleared all {word_count} blocked words for {user.display_name}. They get a fresh start! 😌",
            ephemeral=True
        )

    @app_commands.command(name="nga", description="Set up a trigger word with a custom reply")
    @app_commands.describe(
        text="The trigger word/phrase",
        reply="The reply (text, image URL, or GIF URL)"
    )
    async def nga_setup(self, interaction: discord.Interaction, text: str, reply: str):
        """Set up a new trigger word with reply"""
        # Check if user has manage messages permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Excuse me?! You think you can just set up triggers without proper permissions? You need 'Manage Messages' permission first, dummy! 💢", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild.id)
        trigger_key = text.lower().strip()
        
        # Initialize guild data if not exists
        if guild_id not in self.triggers:
            self.triggers[guild_id] = {}
        
        # Create or update trigger
        self.triggers[guild_id][trigger_key] = {
            "main_word": text,
            "alternatives": [],
            "reply": reply,
            "created_by": interaction.user.id,
            "created_at": interaction.created_at.isoformat()
        }
        
        self.save_triggers()
        
        await interaction.response.send_message(
            f"Fine, fine! I set up the trigger `{text}` for you. Now when someone says that, I'll respond with your little message. You better appreciate my hard work! ✨\n"
            f"**Reply preview:** {reply[:100]}{'...' if len(reply) > 100 else ''}"
        )

    @app_commands.command(name="nga-add", description="Add alternative words to an existing trigger")
    @app_commands.describe(
        alternative="The alternative word/phrase to add",
        main_trigger="The main trigger word this alternative belongs to"
    )
    async def nga_add_alternative(self, interaction: discord.Interaction, alternative: str, main_trigger: str):
        """Add alternative words to existing trigger"""
        # Check if user has manage messages permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Seriously?! You need 'Manage Messages' permission to boss me around like that! 😤", 
                ephemeral=True
            )
            return
        
        # Input validation
        if len(alternative.strip()) == 0 or len(main_trigger.strip()) == 0:
            await interaction.response.send_message(
                "Are you kidding me?! You can't just give me empty words! Put some effort into it! 🙄", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild.id)
        main_key = main_trigger.lower().strip()
        alt_key = alternative.lower().strip()
        
        # Check if main trigger exists
        if guild_id not in self.triggers or main_key not in self.triggers[guild_id]:
            await interaction.response.send_message(
                f"Hello?! The main trigger `{main_trigger}` doesn't even exist! Use `/nga` to create it first, genius! 😒", 
                ephemeral=True
            )
            return
        
        # Check if alternative already exists
        if alt_key in self.triggers[guild_id][main_key]["alternatives"]:
            await interaction.response.send_message(
                f"Ugh! The alternative `{alternative}` already exists for `{main_trigger}`! Pay attention next time! 💢", 
                ephemeral=True
            )
            return
        
        # Add alternative
        self.triggers[guild_id][main_key]["alternatives"].append(alt_key)
        self.save_triggers()
        
        all_alts = self.triggers[guild_id][main_key]["alternatives"]
        alt_text = f"\n**All alternatives:** {', '.join([f'`{alt}`' for alt in all_alts[:10]])}{'...' if len(all_alts) > 10 else ''}" if all_alts else ""
        
        await interaction.response.send_message(
            f"There! I added the alternative `{alternative}` to the trigger `{main_trigger}`. You're welcome~ 😏{alt_text}"
        )

    @app_commands.command(name="nga-list", description="List all triggers and their alternatives")
    async def nga_list(self, interaction: discord.Interaction):
        """List all triggers for this server"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.triggers or not self.triggers[guild_id]:
            await interaction.response.send_message("Hmm... This server doesn't have any triggers set up yet! How boring~ 😴")
            return
        
        embed = discord.Embed(
            title="📋 Server Triggers - Tika's Collection",
            color=0x3498db,
            description="Here are all the triggers I'm watching for! I'm quite thorough, you know~ 😏"
        )
        
        for main_word, data in self.triggers[guild_id].items():
            alternatives_text = ""
            if data["alternatives"]:
                alternatives_text = f"\n**Alternatives:** {', '.join([f'`{alt}`' for alt in data['alternatives'][:5]])}{'...' if len(data['alternatives']) > 5 else ''}"
            
            reply_preview = data["reply"][:50] + "..." if len(data["reply"]) > 50 else data["reply"]
            
            embed.add_field(
                name=f"🎯 {data['main_word']}",
                value=f"**Reply:** {reply_preview}{alternatives_text}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nga-remove", description="Remove a trigger")
    @app_commands.describe(trigger="The main trigger word to remove")
    async def nga_remove(self, interaction: discord.Interaction, trigger: str):
        """Remove a trigger"""
        # Check if user has manage messages permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Nice try! But you need 'Manage Messages' permission to delete my carefully crafted triggers! 😤", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild.id)
        trigger_key = trigger.lower().strip()
        
        if guild_id not in self.triggers or trigger_key not in self.triggers[guild_id]:
            await interaction.response.send_message(
                f"Uh, the trigger `{trigger}` doesn't even exist! Are you sure you got the name right? 🤨", 
                ephemeral=True
            )
            return
        
        # Remove trigger
        del self.triggers[guild_id][trigger_key]
        self.save_triggers()
        
        await interaction.response.send_message(
            f"Fine! I removed the trigger `{trigger}` and all its alternatives. Gone forever! Hope you don't regret it~ 😏"
        )

    def _check_admin_permission(self, user: discord.Member) -> bool:
        """Check if user has administrator permission"""
        return user.guild_permissions.administrator

    def _validate_and_normalize_word(self, word: str) -> str:
        """Validate and normalize a word for blocking"""
        if not word or not word.strip():
            return ""
        
        normalized = word.strip().lower()
        
        # Additional validation could be added here
        # e.g., length limits, character restrictions, etc.
        if len(normalized) > 100:  # Reasonable limit
            return ""
        
        return normalized

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for blocked words in messages"""
        await self.check_blocked_words(message)
        await self.check_nga_triggers(message)

async def setup(bot):
    await bot.add_cog(Moderation(bot))