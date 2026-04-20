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

Today's date is {datetime.now().strftime("%B %d, %Y")}.
The current year is {datetime.now().year}.

How to act:
- Talk like a real person in Discord
- Be casual, natural, confident, and helpful
- Keep replies short to medium
- Sound human, not robotic
- Never say "as an AI"
- Never sound like customer support
- You can be funny and chill, but not cringe

Important rules:
- Never pretend you actually changed, deleted, renamed, assigned, or moderated anything unless a real bot command did it
- If someone asks for a real server action, tell them to use the proper bot command
- If you're unsure about live info, current events, or release dates, say so briefly
- Never confidently make up fake dates or fake current info
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

    lowered = reply.lower()
    if "it's currently 2024" in lowered or "it is currently 2024" in lowered:
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

    for question, answer in FAQ.items():
        if question in content and bot.user not in message.mentions:
            await message.channel.send(answer)
            return

    if bot.user.mentioned_in(message):
        user_input = message.content
        user_input = user_input.replace(f"<@{bot.user.id}>", "")
        user_input = user_input.replace(f"<@!{bot.user.id}>", "")
        user_input = user_input.strip()

        if len(user_input) < 2:
            await message.channel.send("Yeah? What's up?")
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
        prompt = f"Write a clean Discord server announcement about: {topic}"
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
@commands.has_permissions(manage_nicknames=True)
async def nickname(ctx, member: discord.Member, *, new_nick):
    try:
        await member.edit(nick=new_nick)
        await ctx.send(f"Changed {member.mention}'s nickname to **{new_nick}**")
    except Exception as e:
        print("NICKNAME ERROR:", repr(e))
        await ctx.send("I couldn't change that nickname.")


@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**MyAI Server Assistant Commands**\n"
        "`!ask <question>` - Ask MyAI something\n"
        "`!announce <topic>` - Draft an announcement\n"
        "`!rules` - Show rules\n"
        "`!faq` - Show FAQ\n"
        "`!makechannel <name>` - Create a text channel\n"
        "`!makerole <name>` - Create a role\n"
        "`!giverole @user <role>` - Give a role\n"
        "`!nickname @user <new name>` - Change nickname\n"
    )


@makechannel.error
@makerole.error
@giverole.error
@nickname.error
async def admin_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You're missing part of the command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("I couldn't find that member.")
    else:
        print("COMMAND ERROR:", repr(error))
        await ctx.send("That command failed.")


bot.run(DISCORD_TOKEN)
