import os
import discord
from discord.ext import commands
import google.generativeai as genai

# ==============================
# Environment Variables (Railway)
# ==============================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ==============================
# Bot Setup
# ==============================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# Personality
# ==============================

PERSONALITY = (
    "You are Julia. "
    "You are a confident, witty, snappy woman who speaks naturally. "
    "You are playful but respectful. "
    "You never use emojis. "
    "You respond like a real person chatting casually. "
    "You remember context from past messages."
)

# Memory system
user_memory = {}
MAX_MEMORY_LINES = 20

# ==============================
# Bot Events
# ==============================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ==============================
# Commands
# ==============================

@bot.command(name="chat")
async def chat(ctx, *, user_input: str):
    await handle_message(ctx.author.id, ctx.channel, user_input)


@bot.command(name="ai")
async def ai(ctx, *, user_input: str):
    """Global AI command"""
    await handle_message(ctx.author.id, ctx.channel, user_input)


# ==============================
# Mention Handling
# ==============================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # If bot is mentioned
    if bot.user and bot.user.mentioned_in(message):
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if user_input:
            await handle_message(message.author.id, message.channel, user_input)

    await bot.process_commands(message)


# ==============================
# Core AI Function
# ==============================

async def handle_message(user_id, channel, user_input):

    if user_id not in user_memory:
        user_memory[user_id] = []

    memory = user_memory[user_id]

    context = "\n".join(memory[-MAX_MEMORY_LINES:])
    prompt = f"{PERSONALITY}\n{context}\nUser: {user_input}\nJulia:"

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
        print("Gemini API Error:", e)
        await channel.send("Sorry, something went wrong.")

# ==============================
# Run Bot
# ==============================

bot.run(DISCORD_TOKEN)
