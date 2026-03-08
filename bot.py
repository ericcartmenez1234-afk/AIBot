import os
import discord
from discord.ext import commands
from google import genai
import asyncio
import time
from collections import defaultdict

# =====================================================
# ENVIRONMENT
# =====================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

# =====================================================
# GEMINI (2.0 SDK)
# =====================================================

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.0-flash"

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
    "You speak naturally, confidently, and casually. "
    "You are funny, witty, chaotic but smart. "
    "Keep responses short and punchy."
)

# =====================================================
# RATE LIMIT SYSTEM
# =====================================================

global_last_request = 0
GLOBAL_COOLDOWN = 3

user_cooldowns = defaultdict(float)

response_cache = {}
CACHE_LIMIT = 100

# =====================================================
# RATE CONTROL + CACHE
# =====================================================

def enforce_limits(user_id, prompt):

    global global_last_request

    now = time.time()

    # ---- Global cooldown ----
    diff = now - global_last_request
    if diff < GLOBAL_COOLDOWN:
        time.sleep(GLOBAL_COOLDOWN - diff)

    global_last_request = time.time()

    # ---- Per-user cooldown ----
    last_user = user_cooldowns[user_id]
    if now - last_user < 5:
        time.sleep(5 - (now - last_user))

    user_cooldowns[user_id] = time.time()

    # ---- Cache ----
    if prompt in response_cache:
        return response_cache[prompt]

    return None


# =====================================================
# AI FUNCTION
# =====================================================

def generate_ai_response(user_id, message):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY:])

    prompt = f"""
{PERSONALITY}

Conversation:
{context}

User: {message}
Julia:
"""

    cached = enforce_limits(user_id, prompt)
    if cached:
        return cached

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        reply = response.text or "..."

    except Exception as e:

    print("FULL GEMINI ERROR:")
    print(e)

    error_text = str(e)

    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
        print("Rate limited — retrying after delay...")
        time.sleep(10)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            reply = response.text or "..."

        except Exception as retry_error:
            print("Retry failed:", retry_error)
            return "Julia hit the API limit."

    else:
        return "Julia's brain crashed."

    reply = reply[:2000]

    # ---- Cache store ----
    response_cache[prompt] = reply

    if len(response_cache) > CACHE_LIMIT:
        response_cache.clear()

    # ---- Memory store ----
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

    reply = await asyncio.to_thread(
        generate_ai_response,
        interaction.user.id,
        message
    )

    await interaction.followup.send(reply)


# =====================================================
# AUTO RESPOND TO MENTIONS + DM
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

        if not clean:
            return

        reply = await asyncio.to_thread(
            generate_ai_response,
            message.author.id,
            clean
        )

        await message.channel.send(reply)

    await bot.process_commands(message)


# =====================================================
# READY
# =====================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print("Sync error:", e)


# =====================================================
# RUN
# =====================================================

bot.run(DISCORD_TOKEN)

