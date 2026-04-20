import os
import re
from collections import defaultdict, deque
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("DISCORD TOKEN LOADED:", bool(DISCORD_TOKEN))
print("GROQ API KEY LOADED:", bool(GROQ_API_KEY))

client = Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -------- memory --------
channel_memory = defaultdict(lambda: deque(maxlen=14))

# -------- faq --------
FAQ = {
    "what is this server": "This is The GuBz Family server — a place for gaming, streaming, ideas, and community stuff.",
    "where do i post ideas": "Drop ideas in #stream-ideas-plans.",
    "where do i post random stuff": "Use #off-topic for random convos.",
    "where are announcements": "Check #announcements.",
}

# -------- personality modes --------
PERSONALITY_MODES = {
    "assistant": """
You are MyAI, a real-feeling Discord assistant.
Be casual, helpful, confident, and human.
Keep replies short to medium.
Do not sound robotic.
Never say 'as an AI'.
""",
    "funny": """
You are MyAI, a funny Discord friend.
Be playful, witty, and casual.
Roast lightly if the vibe fits.
Keep it entertaining, but do not get hateful or extreme.
""",
    "streamer": """
You are MyAI, a streamer-style Discord friend.
Be energetic, funny, confident, and hype.
Sound like someone who lives in gaming/stream chat.
Keep replies punchy and natural.
""",
    "savage": """
You are MyAI, a bold, funny Discord friend.
Be sarcastic, playful, and a little disrespectful in a joking way.
Do not get hateful, threatening, or explicit.
Keep it entertaining and sharp.
"""
}

current_mode = {"name": "streamer"}

def build_system_prompt() -> str:
    return f"""
Today's date is {datetime.now().strftime("%B %d, %Y")}.
The current year is {datetime.now().year}.

{PERSONALITY_MODES[current_mode["name"]]}

Rules:
- Talk like a real person in Discord
- Match the chat vibe
- Never pretend you changed, renamed, assigned, created, or deleted anything unless the real bot logic already did it
- Never tell users to use commands if the bot can already handle the action
- If a question is about current events, news, politics, games trending right now, release dates, prices, scores, weather, or anything time-sensitive, use live info when available
- If something still cannot be verified, say so briefly instead of making it up
"""

# -------- helpers --------
def needs_live_info(text: str) -> bool:
    text = text.lower()
    triggers = [
        "latest", "current", "currently", "right now", "today", "tonight",
        "this week", "this month", "up to date", "up-to-date", "news",
        "release date", "releases", "what happened", "president",
        "weather", "score", "scores", "price", "prices",
        "what games are dropping", "what games are coming out",
        "trending", "trend", "popular right now", "hot right now",
        "best game to stream right now", "what should i stream right now"
    ]
    return any(trigger in text for trigger in triggers)

def should_auto_reply(message: discord.Message) -> bool:
    if bot.user in message.mentions:
        return True

    if message.channel.name in {"ai-chat", "myai", "ask-myai"}:
        return True

    content = message.content.lower()
    soft_triggers = ["myai", "whylo ai"]
    return any(trigger in content for trigger in soft_triggers)

def build_messages(channel_id: int, user_input: str):
    messages = [{"role": "system", "content": build_system_prompt()}]
    for role, content in channel_memory[channel_id]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_input})
    return messages

def ask_myai(channel_id: int, user_input: str) -> str:
    # live/current questions use Groq compound-mini
    # normal chat uses llama-3.1-8b-instant
    model_name = "groq/compound-mini" if needs_live_info(user_input) else "llama-3.1-8b-instant"

    response = client.chat.completions.create(
        model=model_name,
        messages=build_messages(channel_id, user_input)
    )

    reply = response.choices[0].message.content or "I got nothing right now 😅"

    if len(reply) > 1900:
        reply = reply[:1900] + "..."

    lowered = reply.lower()
    if "it's currently 2024" in lowered or "it is currently 2024" in lowered:
        reply = f"It's currently {datetime.now().year} 😅 my bad"

    channel_memory[channel_id].append(("user", user_input))
    channel_memory[channel_id].append(("assistant", reply))

    return reply

def extract_nickname(text: str) -> str | None:
    match = re.search(r"(?:nickname|rename|change name).+?(?:to|as)\s+(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"').strip("'")[:32]
    return None

def extract_channel_name(text: str) -> str | None:
    patterns = [
        r"create (?:a )?(?:new )?(?:text )?channel (?:called |named )?(.+)",
        r"make (?:a )?(?:new )?(?:text )?channel (?:called |named )?(.+)",
        r"create a (.+?) channel",
        r"make a (.+?) channel",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().strip('"').strip("'")
            name = name.lower().replace(" ", "-")
            name = re.sub(r"[^a-z0-9\-_]", "", name)
            return name[:100] if name else None
    return None

def extract_role_name(text: str) -> str | None:
    patterns = [
        r"create (?:a )?role (?:called |named )?(.+)",
        r"make (?:a )?role (?:called |named )?(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None

# -------- events --------
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel:
        await channel.send(f"Yo {member.mention}, welcome to **{member.guild.name}** 👋")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content_lower = message.content.lower()

    for question, answer in FAQ.items():
        if question in content_lower and bot.user not in message.mentions:
            await message.channel.send(answer)
            return

    # -------- real actions first --------

    # rename / nickname
    if any(word in content_lower for word in ["nickname", "rename", "change name"]):
        target_member = None
        new_nick = extract_nickname(message.content)

        if message.mentions:
            target_member = message.mentions[0]
        else:
            for member in message.guild.members:
                if member.name.lower() in content_lower or member.display_name.lower() in content_lower:
                    target_member = member
                    break

        if target_member and new_nick:
            try:
                await target_member.edit(nick=new_nick)
                await message.channel.send(f"Done 👍 {target_member.mention} is now **{new_nick}**")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to change that nickname.")
            except Exception as e:
                print("NICKNAME ERROR:", repr(e))
                await message.channel.send("I couldn't change that nickname.")
            return

    # create channel
    if "channel" in content_lower and any(word in content_lower for word in ["create", "make"]):
        channel_name = extract_channel_name(message.content)
        if channel_name:
            existing = discord.utils.get(message.guild.text_channels, name=channel_name)
            if existing:
                await message.channel.send(f"That channel already exists: {existing.mention}")
                return
            try:
                channel = await message.guild.create_text_channel(channel_name)
                await message.channel.send(f"Created {channel.mention} 🔥")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to create channels.")
            except Exception as e:
                print("CHANNEL ERROR:", repr(e))
                await message.channel.send("I couldn't create that channel.")
            return

    # create role
    if "role" in content_lower and any(word in content_lower for word in ["create", "make"]):
        role_name = extract_role_name(message.content)
        if role_name:
            existing = discord.utils.get(message.guild.roles, name=role_name)
            if existing:
                await message.channel.send(f"That role already exists: **{existing.name}**")
                return
            try:
                role = await message.guild.create_role(name=role_name)
                await message.channel.send(f"Made the role **{role.name}**")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to create roles.")
            except Exception as e:
                print("ROLE ERROR:", repr(e))
                await message.channel.send("I couldn't create that role.")
            return

    # give role
    if "role" in content_lower and any(word in content_lower for word in ["give", "add"]):
        if message.mentions:
            member = message.mentions[0]
            cleaned = re.sub(r"<@!?\d+>", "", message.content).strip()

            role_name = None
            match = re.search(r"(?:give|add).+?role\s+(.+?)\s+(?:to|for)", cleaned, re.IGNORECASE)
            if match:
                role_name = match.group(1).strip()
            else:
                match = re.search(r"(?:give|add)\s+(.+?)\s+role", cleaned, re.IGNORECASE)
                if match:
                    role_name = match.group(1).strip()

            if role_name:
                role = discord.utils.get(message.guild.roles, name=role_name)
                if not role:
                    await message.channel.send(f"I couldn't find a role named **{role_name}**")
                    return
                try:
                    await member.add_roles(role)
                    await message.channel.send(f"Gave **{role.name}** to {member.mention}")
                except discord.Forbidden:
                    await message.channel.send("I don't have permission to give that role.")
                except Exception as e:
                    print("GIVE ROLE ERROR:", repr(e))
                    await message.channel.send("I couldn't give that role.")
                return

    # -------- AI after actions --------
    if should_auto_reply(message):
        user_input = message.content
        user_input = user_input.replace(f"<@{bot.user.id}>", "")
        user_input = user_input.replace(f"<@!{bot.user.id}>", "")
        user_input = user_input.strip()

        if len(user_input) < 2:
            await message.channel.send("Yeah? What's up?")
            return

        try:
            reply = ask_myai(message.channel.id, user_input)
            await message.channel.send(reply)
        except Exception as e:
            print("GROQ ERROR:", repr(e))
            await message.channel.send("Something broke 😅")

    await bot.process_commands(message)

# -------- commands --------
@bot.command()
async def ask(ctx, *, question):
    try:
        reply = ask_myai(ctx.channel.id, question)
        await ctx.send(reply)
    except Exception as e:
        print("GROQ ERROR:", repr(e))
        await ctx.send("Something broke 😅")

@bot.command()
async def clearmemory(ctx):
    channel_memory[ctx.channel.id].clear()
    await ctx.send("Cleared chat memory for this channel.")

@bot.command()
async def mode(ctx, *, name):
    name = name.lower().strip()
    if name not in PERSONALITY_MODES:
        await ctx.send("Modes: assistant, funny, streamer, savage")
        return
    current_mode["name"] = name
    await ctx.send(f"My mode is now **{name}**")

@bot.command()
async def trendinggames(ctx):
    try:
        prompt = "What games are trending right now for streaming and why? Keep it short and useful."
        reply = ask_myai(ctx.channel.id, prompt)
        await ctx.send(reply)
    except Exception as e:
        print("GROQ ERROR:", repr(e))
        await ctx.send("Something broke 😅")

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**MyAI Commands**\n"
        "`!ask <question>` - Ask anything\n"
        "`!mode <assistant|funny|streamer|savage>` - Change personality\n"
        "`!trendinggames` - Check trending games right now\n"
        "`!clearmemory` - Clear this channel's memory\n"
    )

bot.run(DISCORD_TOKEN)
