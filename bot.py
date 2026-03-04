import os
import discord
from discord.ext import commands
import google.generativeai as genai
import asyncio

# =====================================================
# ENV
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
    "You remember conversation history."
)

# =====================================================
# SLASH COMMAND
# =====================================================

@bot.tree.command(name="ai", description="Chat with Julia")
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
            "AI failed.",
            ephemeral=True
        )


# =====================================================
# AI FUNCTION
# =====================================================

def generate_ai_response(user_id, message):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY:])

    prompt = f"{PERSONALITY}\n{context}\nUser: {message}\nJulia:"

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
# READY
# =====================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print("Sync error:", e)


# =====================================================
# MENTIONS + DM SUPPORT
# =====================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None or bot.user in message.mentions:

        clean = message.content.replace(
            f"<@{bot.user.id}>",
            ""
        ).strip()

        if clean:
            reply = await asyncio.to_thread(
                generate_ai_response,
                message.author.id,
                clean
            )

            await message.channel.send(reply)

    await bot.process_commands(message)


# =====================================================
# RUN
# =====================================================

bot.run(DISCORD_TOKEN)
