import discord
from discord.ext import commands
import asyncio
import logging
import os
from pathlib import Path

# what am I doing
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tika.log'),
        logging.StreamHandler()
    ]
)

class TikaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # Create data directory
        Path('data').mkdir(exist_ok=True)
    
    async def setup_hook(self):
        """Load all cogs when bot starts"""
        cogs = [
            'cogs.personality',
            'cogs.fun_commands', 
            'cogs.moderation'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
    
    async def on_ready(self):
        print(f'🎀 {self.user} is now online and ready to be sassy!')
        print(f'📊 Connected to {len(self.guilds)} servers')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"✨ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors with Tika's personality"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Hmph! You don't have permission for that. Maybe work harder next time? 💅")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Slow down there! You can use this again in {error.retry_after:.1f} seconds. Patience is a virtue, you know~")
        else:
            await ctx.send("Ugh, something went wrong... Don't blame me for this mess! 😤")
            print(f"Command error: {error}")

def main():
    # Check for bot token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ No bot token found! Set DISCORD_BOT_TOKEN environment variable.")
        return
    
    bot = TikaBot()
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
    except KeyboardInterrupt:
        print("\n👋 Bot shutting down...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()