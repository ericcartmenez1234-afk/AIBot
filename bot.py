import os
import discord
from discord.ext import commands
import google.generativeai as genai
import asyncio

# =====================================================
# ENVIRONMENT
# =====================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# =====================================================
# BOT SETUP
# =====================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# MEMORY
# =====================================================

user_memory = {}
MAX_MEMORY = 25

PERSONALITY = (
    "You are Julia. "
    "You speak naturally and confidently. "
    "You act like a real human chatting casually. "
    "You remember conversation history. "
    "You are extremely funny, unhinged, and a snappy woman. "
    "You keep sentences short but you get the point through. No roleplaying."
)

# =====================================================
# AI FUNCTION
# =====================================================

def generate_ai_response(user_id, message):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY:])

    prompt = (
        f"{PERSONALITY}\n"
        f"{context}\n"
        f"User: {message}\n"
        f"Julia:"
    )

    response = model.generate_content(
        {"parts": [{"text": prompt}]}
    )

    reply = response.text if response.text else "..."

    reply = reply[:2000]

    memory.append(f"User: {message}")
    memory.append(f"Julia: {reply}")

    if len(memory) > MAX_MEMORY:
        user_memory[user_id] = memory[-MAX_MEMORY:]

    return reply

# =====================================================
# SLASH COMMAND
# =====================================================

@bot.tree.command(name="ai", description="Chat with Julia")
@discord.app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@discord.app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def ai_command(interaction: discord.Interaction, message: str):

    await interaction.response.defer()

    try:
        reply = await asyncio.to_thread(
            generate_ai_response,
            interaction.user.id,
            message
        )

        await interaction.followup.send(reply)

    except Exception as e:
        print("Slash error:", e)
        await interaction.followup.send(
            "AI failed to respond.",
            ephemeral=True
        )

# =====================================================
# PREFIX COMMAND (!chat)
# =====================================================

@bot.command(name="chat")
async def chat(ctx, *, message: str):

    reply = await asyncio.to_thread(
        generate_ai_response,
        ctx.author.id,
        message
    )

    await ctx.send(reply)

# =====================================================
# READY EVENT
# =====================================================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    try:
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as e:
        print("Sync error:", e)

# =====================================================
# MENTION + DM AUTO CHAT
# =====================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # DM auto reply
    if message.guild is None:

        reply = await asyncio.to_thread(
            generate_ai_response,
            message.author.id,
            message.content
        )

        await message.channel.send(reply)

    # Mention reply
    elif bot.user in message.mentions:

        clean = message.content.replace(f"<@{bot.user.id}>", "")
        clean = clean.replace(f"<@!{bot.user.id}>", "").strip()

        if clean:

            reply = await asyncio.to_thread(
                generate_ai_response,
                message.author.id,
                clean
            )

            await message.channel.send(reply)

    await bot.process_commands(message)

# =====================================================
# RUN BOT
# =====================================================

bot.run(DISCORD_TOKEN)



