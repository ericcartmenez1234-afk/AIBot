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
# RATE LIMIT (PREVENT GEMINI QUOTA ERROR)
# =====================================================

AI_COOLDOWN = 3
last_ai_time = 0
ai_lock = asyncio.Lock()

# =====================================================
# AI RESPONSE FUNCTION
# =====================================================

async def generate_ai_response(user_id, message):

    global last_ai_time

    async with ai_lock:

        now = asyncio.get_event_loop().time()
        wait_time = AI_COOLDOWN - (now - last_ai_time)

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        last_ai_time = asyncio.get_event_loop().time()

        try:

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

        except Exception as e:
            print("Gemini error:", e)
            return "Give me a second, my brain just hit the API limit."

# =====================================================
# SLASH COMMAND (WORKS EVERYWHERE)
# =====================================================

@bot.tree.command(
    name="ai",
    description="Chat with Julia"
)
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

        reply = await generate_ai_response(
            interaction.user.id,
            message
        )

        await interaction.followup.send(reply)

    except Exception as e:

        print("Slash error:", e)

        await interaction.followup.send(
            "Julia broke for a second.",
            ephemeral=True
        )

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
# AUTO CHAT (MENTIONS + DMS)
# =====================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    try:

        # Trigger in DMs or when mentioned
        if message.guild is None or bot.user in message.mentions:

            clean = message.content.replace(
                f"<@{bot.user.id}>",
                ""
            ).strip()

            if clean:

                await message.channel.typing()

                reply = await generate_ai_response(
                    message.author.id,
                    clean
                )

                await message.channel.send(reply)

    except Exception as e:
        print("Message error:", e)

    await bot.process_commands(message)

# =====================================================
# RUN BOT
# =====================================================

bot.run(DISCORD_TOKEN)
