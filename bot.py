import os
import discord
from discord.ext import commands
import google.generativeai as genai

# =====================================================
# ENV VARIABLES
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
# PERSONALITY
# =====================================================

PERSONALITY = (
    "You are Julia. "
    "You speak naturally and confidently. "
    "You act like a real human chatting casually. "
    "You remember conversation context."
)

# Memory storage
user_memory = {}
MAX_MEMORY = 30

# =====================================================
# SLASH COMMAND (WORKS FOR USER + GUILD INSTALL)
# =====================================================

@bot.tree.command(
    name="ai",
    description="Chat with Julia AI"
)
async def ai_command(
    interaction: discord.Interaction,
    message: str
):

    # Support all install contexts
    if interaction.context not in (
        discord.InteractionContext.guild,
        discord.InteractionContext.bot_dm,
        discord.InteractionContext.private_channel,
    ):
        await interaction.response.send_message(
            "Unsupported context.",
            ephemeral=True
        )
        return

    # Immediately defer so Discord doesn't timeout
    await interaction.response.defer()

    try:
        await handle_message(
            interaction.user.id,
            interaction.channel,
            message
        )

    except Exception as e:
        print("Slash error:", e)
        await interaction.followup.send(
            "AI failed to respond.",
            ephemeral=True
        )

# =====================================================
# READY EVENT (FORCE COMMAND SYNC)
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
# MESSAGE LISTENER (MENTIONS + DM AUTO CHAT)
# =====================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Trigger if DM OR bot mentioned
    if message.guild is None or bot.user in message.mentions:

        cleaned = message.content.replace(
            f"<@{bot.user.id}>",
            ""
        ).strip()

        if cleaned:
            await handle_message(
                message.author.id,
                message.channel,
                cleaned
            )

    await bot.process_commands(message)

# =====================================================
# AI CORE FUNCTION
# =====================================================

async def handle_message(user_id, channel, text):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY:])

    prompt = (
        f"{PERSONALITY}\n"
        f"{context}\n"
        f"User: {text}\n"
        f"Julia:"
    )

    try:
        response = model.generate_content(
            {"parts": [{"text": prompt}]}
        )

        reply = response.text if response.text else "..."

        # Enforce Discord message limit
        reply = reply[:2000]

        await channel.send(reply)

        # Save memory
        memory.append(f"User: {text}")
        memory.append(f"Julia: {reply}")

        if len(memory) > MAX_MEMORY:
            user_memory[user_id] = memory[-MAX_MEMORY:]

    except Exception as e:
        print("Gemini Error:", e)
        await channel.send("AI error occurred.")

# =====================================================
# RUN BOT
# =====================================================

bot.run(DISCORD_TOKEN)

