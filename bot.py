import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("DISCORD TOKEN LOADED:", bool(DISCORD_TOKEN))
print("GROQ API KEY LOADED:", bool(GROQ_API_KEY))

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


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
            user_input = "Say something cool"

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are MyAI, a smart, slightly edgy, confident assistant. Keep replies short, natural, and Discord-friendly."
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ]
            )

            reply = response.choices[0].message.content

            if not reply:
                reply = "I got nothing right now 😅"

            if len(reply) > 1900:
                reply = reply[:1900] + "..."

            await message.channel.send(reply)

        except Exception as e:
            print("GROQ ERROR:", repr(e))
            await message.channel.send("Something broke 😅")

    await bot.process_commands(message)


bot.run(DISCORD_TOKEN)
