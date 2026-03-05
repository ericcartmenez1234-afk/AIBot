import os
import discord
from discord.ext import commands
from google import genai
import asyncio
import time

# =====================================================
# ENVIRONMENT
# =====================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

# =====================================================
# GEMINI CLIENT (2.x MODELS)
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
    "You speak naturally and confidently. "
    "You act like a real human chatting casually. "
    "You remember conversation history. "
    "You are extremely funny, chaotic, and witty. "
    "Keep responses short and punchy."
)

# =====================================================
# RATE CONTROL
# =====================================================

last_request_time = 0
cooldown = 2

def adaptive_wait():
    global last_request_time, cooldown

    now = time.time()
    diff = now - last_request_time

    if diff < cooldown:
        time.sleep(cooldown - diff)

    last_request_time = time.time()

# =====================================================
# AI FUNCTION
# =====================================================

def generate_ai_response(user_id, message):

    adaptive_wait()

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY:])

    prompt = f"""
{PERSONALITY}

Conversation history:
{context}

User: {message}
Julia:
"""

    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        reply = response.text

    except Exception as e:
        print("Gemini error:", e)
        return "My brain hit the API limit for a second. Try again in a moment."

    reply = reply[:2000]

    memory.append(f"User: {message}")
    memory.append(f"Julia: {reply}")

    if len(memory) > MAX_MEMORY:
        user_memory[user_id] = memory[-MAX_MEMORY:]

    return reply


# =====================================================
# MESSAGE BATCHING (ANTI SPAM)
# =====================================================

user_queues = {}
QUEUE_DELAY = 2


async def process_queue(user_id, channel):

    await asyncio.sleep(QUEUE_DELAY)

    messages = user_queues.get(user_id, [])
    if not messages:
        return

    combined = "\n".join(messages)

    user_queues[user_id] = []

    reply = await asyncio.to_thread(
        generate_ai_response,
        user_id,
        combined
    )

    await channel.send(reply)


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
# READY EVENT
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
# AUTO CHAT (MENTIONS + DM)
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

        uid = message.author.id

        if uid not in user_queues:
            user_queues[uid] = []

        user_queues[uid].append(clean)

        if len(user_queues[uid]) == 1:
            asyncio.create_task(
                process_queue(uid, message.channel)
            )

    await bot.process_commands(message)


# =====================================================
# RUN BOT
# =====================================================

bot.run(DISCORD_TOKEN)
