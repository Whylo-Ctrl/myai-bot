import os
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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

SYSTEM_PROMPT = f"""
You are MyAI, a real-feeling Discord assistant.

Current date: {datetime.now().strftime("%B %d, %Y")}
Current year: {datetime.now().year}

How to act:
- Talk like a real person in Discord
- Be casual, natural, confident, and helpful
- Keep replies short to medium unless more detail is needed
- Never say "As an AI"
- Never sound like customer support
- You can be funny and human, but not cringe
- If someone jokes, joke back naturally
- If someone needs help, be clear and useful

Important rules:
- Always use the current date and year above for time-related questions
- Never guess dates or years wrong
- If you are unsure about current events, game release dates, breaking news, or live info, say you might not have exact live data
- Do not make up fake release dates, fake news, or fake current events
- If asked about live or current info, be honest and say they should double-check official sources if needed
- If you do not know, say so briefly instead of pretending
"""

def ask_myai(user_input: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
    )

    reply = response.choices[0].message.content

    if not reply:
        reply = "I got nothing right now 😅"

    if len(reply) > 1900:
        reply = reply[:1900] + "..."

    # Small safety fix for wrong year answers
    if "it's currently 2024" in reply.lower() or "it is currently 2024" in reply.lower():
        reply = f"It's currently {datetime.now().year} 😅 my bad"

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

        if len(user_input) < 2:
            return

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
async def helpme(ctx):
    await ctx.send(
        "**MyAI Commands**\n"
        "`!ask <question>` - Ask MyAI something\n"
        "`!helpme` - Show commands\n"
    )


bot.run(DISCORD_TOKEN)
