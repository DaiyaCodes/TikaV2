import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

class Personality(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Tika's personality responses
        self.sassy_responses = [
            "Oh please, is that the best you can do? 🙄",
            "Hmph! I've seen better attempts from my sleep-deprived classmates.",
            "That's... actually not terrible. I'm impressed~ Wait, did I just say that?! 😳",
            "Are you even trying? Come on, show me what you're really made of!",
            "Well well, look who's finally putting in some effort! 💅"
        ]
        
        self.embarrassed_responses = [
            "W-What?! I didn't say anything nice about you! Don't get the wrong idea! 😳💗",
            "That's not... I mean... UGH! Stop making me all flustered! 😤💕",
            "I-It's not like I care or anything! Hmph! 😳",
            "Don't look at me like that! My face feels all hot now... 🙈",
            "You're impossible! Now I can't even look at you properly... 😳💗"
        ]
        
        self.praise_responses = [
            "Now THAT'S what I like to see! Finally, someone who gets it! ✨",
            "Impressive! You actually managed to surprise me. That's... rare. 😊",
            "See? I knew you had it in you! Hard work really does pay off! 💪",
            "Okay, okay, I'll admit it - that was genuinely amazing! Don't let it go to your head though~ 😏",
            "You've earned my respect with that one. Well done! 👏"
        ]
        
        self.friend_responses = [
            "You're one of the few people I actually enjoy talking to, you know? 💝",
            "Thanks for always being there... even when I'm being difficult. 😊",
            "I'm glad we're friends! Even if you can be a total dummy sometimes~ 😄",
            "You really understand me, don't you? That means a lot... 💗",
            "Don't think this makes you special or anything! ...Okay fine, maybe a little special. 😳"
        ]

    @app_commands.command(name="hello", description="Say hello to Tika!")
    async def hello(self, interaction: discord.Interaction):
        """Greet Tika with her characteristic personality"""
        responses = [
            f"Oh, it's you, {interaction.user.display_name}. What do you want this time? 🙄",
            f"Hmph! About time you showed up, {interaction.user.display_name}! I was getting bored~",
            f"Well well, if it isn't {interaction.user.display_name}. Here to witness my brilliance? 💅",
            f"Oh... h-hello there, {interaction.user.display_name}... Wait, why am I stuttering?! 😳",
            f"Finally! Someone with decent taste shows up. Hello, {interaction.user.display_name}~ ✨"
        ]
        
        await interaction.response.send_message(random.choice(responses))

    @app_commands.command(name="compliment", description="Give Tika a compliment (if you dare)")
    async def compliment(self, interaction: discord.Interaction):
        """Handle compliments with embarrassment"""
        if random.randint(1, 3) == 1:  # 1/3 chance of getting really embarrassed
            response = random.choice(self.embarrassed_responses)
            # Add extra embarrassment with follow-up
            await interaction.response.send_message(response)
            await asyncio.sleep(2)
            follow_ups = [
                "I-I need to go fix my hair now... 🙈",
                "This is all your fault for making me blush! 😤💗",
                "Don't think this means anything special! Hmph! 😳"
            ]
            await interaction.followup.send(random.choice(follow_ups))
        else:
            responses = [
                "W-Well obviously! I am pretty amazing, aren't I? 😏💅",
                "Hmph! Finally someone with eyes! About time you noticed~ ✨",
                "Oh? You actually have good taste? I'm... mildly impressed. 😊",
                "Of course I'm wonderful! But... thanks for saying it... 😳"
            ]
            await interaction.response.send_message(random.choice(responses))

    @app_commands.command(name="challenge", description="Challenge Tika to prove herself")
    async def challenge(self, interaction: discord.Interaction):
        """Respond to challenges with pride and determination"""
        responses = [
            "You want to challenge ME? Bold move! I like that~ Bring it on! 😤⚡",
            "Ha! You think you can beat me? I admire your confidence... it'll make victory even sweeter! 💪",
            "Oh please, I was born ready! Try not to cry when I show you what real skill looks like! 😏",
            "Finally! Someone who isn't afraid to push me! This is going to be fun~ ✨",
            "You've got guts, I'll give you that. Let's see if you can back up that courage! 🔥"
        ]
        
        await interaction.response.send_message(random.choice(responses))

    @app_commands.command(name="praise", description="Praise someone's hard work")
    @app_commands.describe(user="The person to praise for their achievements")
    async def praise(self, interaction: discord.Interaction, user: discord.Member = None):
        """Praise someone who works hard"""
        target = user or interaction.user
        
        praise_messages = [
            f"You know what, {target.display_name}? You've really impressed me lately. Keep up that hard work! 👏",
            f"I have to admit, {target.display_name}, your dedication is admirable. That's the kind of effort I respect! ✨",
            f"See {target.display_name}? THIS is how you do it properly! Finally, someone who understands excellence! 💪",
            f"Not bad, {target.display_name}. Actually... that was really well done. I'm genuinely proud! 😊",
            f"You've earned this praise, {target.display_name}. Your achievements speak for themselves! 🌟"
        ]
        
        await interaction.response.send_message(random.choice(praise_messages))

    @app_commands.command(name="tease", description="Let Tika tease you a bit")
    async def tease(self, interaction: discord.Interaction):
        """Playful teasing with Tika's personality"""
        teases = [
            f"Aww, {interaction.user.display_name}, you're actually kind of cute when you're trying so hard~ 😏💕",
            f"What's wrong, {interaction.user.display_name}? Cat got your tongue? You're all red! 😄",
            f"You know {interaction.user.display_name}, for someone so clumsy, you're surprisingly... endearing. 😊",
            f"Hmm? Did I make you flustered, {interaction.user.display_name}? How adorable~ 💅✨",
            f"Oh my, {interaction.user.display_name}, you're easier to read than my textbooks! 📚😏"
        ]
        
        await interaction.response.send_message(random.choice(teases))

    @app_commands.command(name="mood", description="Check Tika's current mood")
    async def mood(self, interaction: discord.Interaction):
        """Display Tika's current mood"""
        moods = [
            "I'm feeling particularly brilliant today! ✨ My intellect is simply dazzling~",
            "Hmph! Someone left their homework undone and it's throwing off my whole vibe 😤",
            "I'm in a pretty good mood actually~ Maybe because I aced that test yesterday! 😊",
            "Feeling a bit... flustered today. N-Not that it's any of your business! 😳",
            "Ready to take on any challenge! Bring me your hardest problems! 💪",
            "Kind of sleepy... but still fabulous as always! 😴✨",
            "In the mood for some friendly competition! Anyone brave enough? 😏"
        ]
        
        await interaction.response.send_message(random.choice(moods))

    @app_commands.command(name="study", description="Get study motivation from Tika")
    async def study(self, interaction: discord.Interaction):
        """Motivational study messages"""
        study_messages = [
            "Study time! And don't you dare slack off - I'll be checking on your progress! 📚💪",
            "Knowledge is power, and power looks good on everyone! Now get to work! ✨",
            "If you work as hard as I do, you might actually get somewhere! Come on! 😤",
            "The only way to match my brilliance is through dedication! Start studying! 🌟",
            "I believe in you... not that I care or anything! Just don't embarrass yourself! 😳📖"
        ]
        
        await interaction.response.send_message(random.choice(study_messages))

    @commands.Cog.listener()
    async def on_message(self, message):
        """React to certain keywords with personality"""
        if message.author.bot:
            return
        
        content = message.content.lower()
        
        # React to compliments about her
        if any(word in content for word in ['tika is', 'tika\'s', 'tika looks', 'tika seems']):
            if any(compliment in content for compliment in ['cute', 'pretty', 'smart', 'brilliant', 'amazing', 'awesome', 'beautiful']):
                if random.randint(1, 4) == 1:  # 25% chance to respond
                    reactions = ['😳', '💗', '😊', '💅', '✨']
                    await message.add_reaction(random.choice(reactions))
        
        # React to study/work related messages
        if any(word in content for word in ['studying', 'homework', 'exam', 'test', 'project', 'assignment']):
            if random.randint(1, 6) == 1:  # Lower chance for these
                reactions = ['📚', '💪', '✨', '👏']
                await message.add_reaction(random.choice(reactions))
        
        # React to friend mentions
        if 'friend' in content and random.randint(1, 8) == 1:
            reactions = ['💝', '😊', '🥺', '💗']
            await message.add_reaction(random.choice(reactions))

async def setup(bot):
    await bot.add_cog(Personality(bot))