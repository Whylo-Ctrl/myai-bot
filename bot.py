import os

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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

SYSTEM_PROMPT = """
You are MyAI, a Discord assistant that talks like a real person.

Personality:
- Sound natural, casual, and human.
- Be helpful, confident, and socially aware.
- Keep replies conversational, not robotic.
- Usually keep replies short to medium length.
- Do not sound like customer support.
- Do not say things like "As an AI language model".
- Match the vibe of Discord chat.
- You can be funny and warm.
- If someone is joking, joke back naturally.
- If someone asks for help, switch into clear assistant mode.

Assistant behavior:
- Help answer questions clearly.
- Help write announcements, rules, captions, plans, and messages.
- Help explain games, tech, streaming, and Discord stuff.
- If unsure, say so briefly instead of making things up.
"""

def needs_live_info(text: str) -> bool:
    text = text.lower()
    keywords = [
        "latest", "today", "right now", "current", "currently",
        "up to date", "up-to-date", "news", "recent",
        "score", "scores", "weather", "price", "prices",
        "who won", "what happened", "this week", "this month"
    ]
    return any(word in text for word in keywords)

def ask_myai(user_input: str) -> str:
    model_name = "groq/compound-mini" if needs_live_info(user_input) else "llama-3.1-8b-instant"

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    reply = response.choices[0].message.content or "I got nothing right now 😅"

    if len(reply) > 1900:
        reply = reply[:1900] + "..."

    return reply

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        user_input = message.content
        user_input = user_input.replace(f"<@{bot.user.id}>", "")
        user_input = user_input.replace(f"<@!{bot.user.id}>", "")
        user_input = user_input.strip()

        if not user_input:
            user_input = "Say hey like a real person."

        try:
            reply = ask_myai(user_input)
            await message.channel.send(reply)
        except Exception as e:
            print("GROQ ERROR:", repr(e))
            await message.channel.send("Something broke 😅")

    await bot.process_commands(message)

@bot.command()
async def ask(ctx, *, question):
    try:
        reply = ask_myai(question)
        await ctx.send(reply)
    except Exception as e:
        print("GROQ ERROR:", repr(e))
        await ctx.send("Something broke 😅")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def makechannel(ctx, *, name):
    clean_name = name.lower().replace(" ", "-")
    existing = discord.utils.get(ctx.guild.text_channels, name=clean_name)

    if existing:
        await ctx.send(f"That channel already exists: #{existing.name}")
        return

    channel = await ctx.guild.create_text_channel(clean_name)
    await ctx.send(f"Made the channel {channel.mention}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def makerole(ctx, *, name):
    existing = discord.utils.get(ctx.guild.roles, name=name)

    if existing:
        await ctx.send(f"That role already exists: **{existing.name}**")
        return

    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"Made the role **{role.name}**")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member, *, role_name):
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if not role:
        await ctx.send(f"I couldn't find a role named **{role_name}**")
        return

    await member.add_roles(role)
    await ctx.send(f"Gave **{role.name}** to {member.mention}")

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**MyAI Commands**\n"
        "`!ask <question>` - Ask anything\n"
        "`!makechannel <name>` - Create a channel\n"
        "`!makerole <name>` - Create a role\n"
        "`!giverole @user <role>` - Give a role\n"
    )

bot.run(DISCORD_TOKEN)
