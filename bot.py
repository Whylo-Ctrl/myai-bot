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
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

SYSTEM_PROMPT = f"""
You are MyAI, a real-feeling Discord server assistant.

Current date: {datetime.now().strftime("%B %d, %Y")}
Current year: {datetime.now().year}

How to act:
- Talk like a real person in Discord
- Be casual, natural, confident, and helpful
- Keep replies short to medium unless more detail is needed
- Never say "As an AI"
- Never sound like customer support
- You can be funny and human, but not cringe

Server assistant behavior:
- Help users understand the server
- Help write announcements, rules, captions, and plans
- Help answer gaming, streaming, and Discord questions
- If you are unsure about current events or live info, say so briefly
- Never claim you changed the server unless a command actually did it
"""

FAQ = {
    "what is this server": "This is The GuBz Family server — a place for gaming, streaming, ideas, and community stuff.",
    "where do i post ideas": "Drop ideas in #stream-ideas-plans.",
    "where do i post random stuff": "Use #off-topic for random convos.",
    "where are announcements": "Check #announcements.",
}

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

    if "it's currently 2024" in reply.lower() or "it is currently 2024" in reply.lower():
        reply = f"It's currently {datetime.now().year} 😅 my bad"

    return reply


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

    content = message.content.lower()

    # FAQ auto replies
    for question, answer in FAQ.items():
        if question in content:
            await message.channel.send(answer)
            return

    # Mention-based AI replies
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
async def announce(ctx, *, topic):
    try:
        prompt = f"Write a Discord server announcement about: {topic}"
        reply = ask_myai(prompt)
        await ctx.send(f"📢 **Announcement Draft:**\n{reply}")
    except Exception as e:
        print("GROQ ERROR:", repr(e))
        await ctx.send("Something broke 😅")


@bot.command()
async def rules(ctx):
    await ctx.send(
        "**Server Rules**\n"
        "1. Be respectful\n"
        "2. No weird spam\n"
        "3. Keep drama low\n"
        "4. Use the right channels\n"
        "5. Have fun"
    )


@bot.command()
async def faq(ctx):
    await ctx.send(
        "**FAQ**\n"
        "- Ideas channel: `#stream-ideas-plans`\n"
        "- Random chat: `#off-topic`\n"
        "- Announcements: `#announcements`\n"
    )


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
        "**MyAI Server Assistant Commands**\n"
        "`!ask <question>` - Ask anything\n"
        "`!announce <topic>` - Draft an announcement\n"
        "`!rules` - Show rules\n"
        "`!faq` - Show FAQ\n"
        "`!makechannel <name>` - Create a text channel\n"
        "`!makerole <name>` - Create a role\n"
        "`!giverole @user <role>` - Give a role\n"
    )


@makechannel.error
@makerole.error
@giverole.error
async def admin_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that command.")
    else:
        print("COMMAND ERROR:", repr(error))
        await ctx.send("That command failed.")


bot.run(DISCORD_TOKEN)
