import os
import discord
from discord.ext import commands
import google.generativeai as genai

# =====================================================
# Environment Variables (Railway)
# =====================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# =====================================================
# Bot Setup
# =====================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# Personality
# =====================================================

PERSONALITY = (
    "You are Julia. "
    "You are confident, witty, and speak naturally. "
    "You never use emojis. "
    "You act like a real person chatting casually. "
    "You remember conversation context."
)

# Memory storage
user_memory = {}
MAX_MEMORY_LINES = 25

# =====================================================
# Slash Command (Works Everywhere — Servers + DMs)
# =====================================================

@bot.tree.command(
    name="ai",
    description="Chat with Julia AI anywhere"
)
async def ai_command(interaction: discord.Interaction, message: str):

    await interaction.response.defer()

    await handle_message(
        interaction.user.id,
        interaction.channel,
        message
    )

# =====================================================
# Bot Ready — Global Slash Sync
# =====================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        # Sync globally so it appears in all servers + DMs
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as e:
        print("Slash sync error:", e)

# =====================================================
# Message Listener (Mentions + DMs Support)
# =====================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # If in DM OR bot is mentioned in a server
    if message.guild is None or bot.user in message.mentions:

        user_input = message.content.replace(
            f"<@{bot.user.id}>", ""
        ).strip()

        if user_input:
            await handle_message(
                message.author.id,
                message.channel,
                user_input
            )

    await bot.process_commands(message)

# =====================================================
# AI Core Logic
# =====================================================

async def handle_message(user_id, channel, user_input):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY_LINES:])

    prompt = (
        f"{PERSONALITY}\n"
        f"{context}\n"
        f"User: {user_input}\n"
        f"Julia:"
    )

    try:
        response = model.generate_content(
            {"parts": [{"text": prompt}]}
        )

        bot_response = response.text

        await channel.send(bot_response)

        # Store memory
        memory.append(f"User: {user_input}")
        memory.append(f"Julia: {bot_response}")

        if len(memory) > MAX_MEMORY_LINES:
            user_memory[user_id] = memory[-MAX_MEMORY_LINES:]

    except Exception as e:
        print("Gemini Error:", e)
        await channel.send("Something went wrong.")

# =====================================================
# Run Bot
# =====================================================

bot.run(DISCORD_TOKEN)
