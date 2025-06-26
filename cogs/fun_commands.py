import discord
from discord.ext import commands
from discord import app_commands
import random
import re
import asyncio
from typing import List

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Pre-compile regex for better performance
        self.dice_pattern = re.compile(r'^(\d+)d(\d+)$', re.IGNORECASE)
        
        # Constants for better maintainability
        self.COIN_STICKERS = [
            "https://media.discordapp.net/stickers/1377651154565206047.gif?size=256&name=misakacoin",
            "https://media.discordapp.net/stickers/1377651797484900462.gif?size=256&name=cointoss"
        ]
        self.DICE_STICKER = "https://media.discordapp.net/stickers/1377648107386441879.gif?size=256&name=dicethrow"
        
        # Animation timing
        self.ANIMATION_DELAY = 3

        # Tika's personality responses for games
        self.coin_comments = [
            "Hmph! Let's see if luck favors the brilliant~",
            "Obviously I'll predict this correctly. I'm good at everything! 💅",
            "Even coin flips bow to my superior intellect!",
            "This is child's play, but I'll humor you~",
            "Watch and learn how it's done! ✨"
        ]
        
        self.dice_comments = [
            "Rolling dice? How... quaint. But I'll show you how it's done! 🎲",
            "Let me demonstrate my superior luck! Watch this!",
            "Dice rolling is an art form, and I'm the master! 😏",
            "Even random chance respects my abilities~",
            "Prepare to witness perfection in action! ✨"
        ]

    @app_commands.command(name="coinflip", description="Let Tika flip a coin for you!")
    async def coinflip(self, interaction: discord.Interaction):
        """Flip a coin with Tika's commentary"""
        chosen_sticker = random.choice(self.COIN_STICKERS)
        
        # Tika's pre-flip comment
        comment = random.choice(self.coin_comments)
        
        # Create animation embed
        animation_embed = discord.Embed(
            title="🪙 Flipping Coin...",
            description=comment,
            color=0xFFFF00
        )
        animation_embed.set_image(url=chosen_sticker)
        
        await interaction.response.send_message(embed=animation_embed)
        await asyncio.sleep(self.ANIMATION_DELAY)
        
        # Generate result
        result = random.choice(["Heads", "Tails"])
        color = 0x00FF00 if result == "Heads" else 0xFF0000
        
        # Tika's reaction to the result
        reactions = {
            "Heads": [
                "Ha! Of course it's heads! I knew it all along~ 😏",
                "Heads it is! My prediction skills are unmatched! ✨",
                "See? Even coins know I'm always right! 💅",
                "Heads! Just as I calculated... probably. 😊"
            ],
            "Tails": [
                "Tails! Well, that was... unexpected. But I totally saw it coming! 😤",
                "Hmph! Tails? The coin clearly has questionable taste. 🙄",
                "Tails it is! Even I can't control everything... unfortunately. 😏",
                "Tails! Not bad, coin. Not bad at all~ ✨"
            ]
        }
        
        # Create result embed
        result_embed = discord.Embed(
            title=f"🪙 Coin Flip Result: {result}!",
            description=random.choice(reactions[result]),
            color=color
        )
        result_embed.set_image(url=chosen_sticker)
        
        await interaction.edit_original_response(embed=result_embed)

    @app_commands.command(name="roll", description="Let Tika roll dice for you!")
    @app_commands.describe(dice="Dice notation (e.g., 1d6, 2d20, 3d8)")
    async def roll_dice(self, interaction: discord.Interaction, dice: str):
        """Roll dice with Tika's personality"""
        
        # Validate and parse dice notation
        validation_result = self._validate_dice_input(dice)
        if not validation_result["valid"]:
            # Tika's sassy error messages
            error_messages = [
                f"Ugh, {validation_result['error']} Do I have to explain everything? 🙄",
                f"Seriously? {validation_result['error']} Pay attention next time! 😤",
                f"*sigh* {validation_result['error']} Here I thought you were smarter than this~"
            ]
            
            await interaction.response.send_message(
                random.choice(error_messages),
                ephemeral=True
            )
            return
        
        num_dice, die_sides = validation_result["num_dice"], validation_result["die_sides"]
        
        # Show animation with Tika's comment
        comment = random.choice(self.dice_comments)
        animation_embed = discord.Embed(
            title=f"🎲 Rolling {dice.upper()}...",
            description=comment,
            color=0xFFFF00
        )
        animation_embed.set_image(url=self.DICE_STICKER)
        
        await interaction.response.send_message(embed=animation_embed)
        await asyncio.sleep(self.ANIMATION_DELAY)
        
        # Generate rolls
        rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
        
        # Create result embed with Tika's commentary
        result_embed = self._create_dice_result_embed(dice, rolls, num_dice, die_sides)
        await interaction.edit_original_response(embed=result_embed)

    def _validate_dice_input(self, dice: str) -> dict:
        """Validate dice input and return parsed values"""
        match = self.dice_pattern.match(dice.strip())
        
        if not match:
            return {
                "valid": False,
                "error": "Invalid dice format! Use format like `1d6`, `2d20`, etc."
            }
        
        num_dice = int(match.group(1))
        die_sides = int(match.group(2))
        
        if not (1 <= num_dice <= 100):
            return {
                "valid": False,
                "error": "Number of dice must be between 1 and 100!"
            }
        
        if not (2 <= die_sides <= 1000):
            return {
                "valid": False,
                "error": "Die sides must be between 2 and 1000!"
            }
        
        return {
            "valid": True,
            "num_dice": num_dice,
            "die_sides": die_sides
        }

    def _create_dice_result_embed(self, dice: str, rolls: List[int], num_dice: int, die_sides: int) -> discord.Embed:
        """Create the dice result embed with Tika's commentary"""
        
        # Tika's reaction based on rolls
        total = sum(rolls) if num_dice > 1 else rolls[0]
        max_possible = num_dice * die_sides
        
        if num_dice == 1:
            if rolls[0] == die_sides:  # Max roll
                comments = [
                    "Perfect! Maximum roll! Obviously my luck is incredible~ ✨",
                    "Ha! See that? That's what happens when I'm involved! 😏",
                    "Maximum roll! I told you I was good at everything! 💅"
                ]
            elif rolls[0] == 1:  # Min roll
                comments = [
                    "What?! A one?! This dice is clearly defective! 😤",
                    "Hmph! Even the greatest minds face setbacks... occasionally. 🙄",
                    "A one? Well... everyone has off days. Even me, apparently. 😳"
                ]
            else:
                comments = [
                    f"Not bad! A solid {rolls[0]}! 😊",
                    f"{rolls[0]}? I've seen worse, I suppose~ 😏",
                    f"A {rolls[0]}! Perfectly adequate! ✨"
                ]
        else:
            percentage = (total / max_possible) * 100
            if percentage >= 90:
                comments = [
                    "Incredible! Look at those numbers! My brilliance shines through everything! ✨",
                    "Outstanding rolls! Obviously my superior aura influenced the dice! 😏",
                    "Amazing! These dice clearly recognize talent when they see it! 💅"
                ]
            elif percentage >= 70:
                comments = [
                    "Very nice! Those are some respectable numbers! 😊",
                    "Good rolls! You're learning from the best~ ✨",
                    "Solid performance! I'm... actually impressed! 😏"
                ]
            elif percentage >= 40:
                comments = [
                    "Eh, average. Could be better, could be worse~ 🙄",
                    "Not terrible! There's room for improvement though. 😤",
                    "Decent enough, I suppose. Try harder next time! 💪"
                ]
            else:
                comments = [
                    "Oof... those are some rough rolls. Even I can't fix everything! 😅",
                    "Well that's... unfortunate. The dice clearly weren't cooperating! 😬",
                    "Don't worry! Even the best of us have bad luck sometimes... 😊"
                ]
        
        result_embed = discord.Embed(
            title=f"🎲 {dice.upper()} Results",
            description=random.choice(comments),
            color=0x3498DB
        )
        
        if num_dice == 1:
            result_embed.add_field(
                name="Result",
                value=f"**{rolls[0]}**",
                inline=False
            )
        else:
            # Use more efficient string joining
            rolls_str = ", ".join(str(roll) for roll in rolls)
            result_embed.add_field(
                name="Individual Rolls",
                value=rolls_str,
                inline=False
            )
            result_embed.add_field(
                name="Total",
                value=f"**{sum(rolls)}**",
                inline=False
            )
        
        result_embed.set_image(url=self.DICE_STICKER)
        return result_embed

    @app_commands.command(name="rps", description="Play Rock Paper Scissors with Tika!")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock", value="rock"),
        app_commands.Choice(name="Paper", value="paper"),
        app_commands.Choice(name="Scissors", value="scissors")
    ])
    async def rock_paper_scissors(self, interaction: discord.Interaction, choice: str):
        """Play Rock Paper Scissors with Tika"""
        
        choices = ["rock", "paper", "scissors"]
        tika_choice = random.choice(choices)
        
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        # Determine winner
        if choice == tika_choice:
            result = "tie"
            color = 0xFFFF00
            comments = [
                "A tie?! Great minds think alike, I suppose~ 😏",
                "Hmph! You copied my strategy! That's... actually smart. 😊",
                "A draw! We're more alike than I thought... 😳"
            ]
        elif (choice == "rock" and tika_choice == "scissors") or \
             (choice == "paper" and tika_choice == "rock") or \
             (choice == "scissors" and tika_choice == "paper"):
            result = "win"
            color = 0x00FF00
            comments = [
                "What?! How did you... That was just luck! 😤",
                "Impossible! I must have let you win... yeah, that's it! 😳",
                "Fine, fine! You win this round! Don't let it go to your head! 🙄"
            ]
        else:
            result = "lose"
            color = 0xFF0000
            comments = [
                "Ha! Victory is mine! Did you really think you could beat me? 😏",
                "Too easy! My strategic brilliance shines once again! ✨",
                "Better luck next time! Maybe study my techniques~ 💅"
            ]
        
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors!",
            color=color
        )
        
        embed.add_field(
            name="Your Choice",
            value=f"{emojis[choice]} {choice.title()}",
            inline=True
        )
        
        embed.add_field(
            name="Tika's Choice", 
            value=f"{emojis[tika_choice]} {tika_choice.title()}",
            inline=True
        )
        
        embed.add_field(
            name="Result",
            value=f"You {'Won' if result == 'win' else 'Lost' if result == 'lose' else 'Tied'}!",
            inline=False
        )
        
        embed.add_field(
            name="💬 Tika says:",
            value=random.choice(comments),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FunCommands(bot))