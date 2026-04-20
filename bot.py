import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

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
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()

        if not user_input:
            user_input = "Say something cool"

        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are MyAI, a smart, slightly edgy, confident assistant."},
                    {"role": "user", "content": user_input}
                ]
            )

            reply = response.choices[0].message.content
            await message.channel.send(reply)

        except Exception as e:
            print("AI ERROR:", repr(e))
            await message.channel.send("Something broke 😅")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
