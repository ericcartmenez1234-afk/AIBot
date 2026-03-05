import os
import discord
from discord.ext import commands
import google.generativeai as genai
import asyncio

# ==========================================
# ENVIRONMENT
# ==========================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("Missing environment variables!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Better free quota model
model = genai.GenerativeModel("gemini-1.5-flash")

# ==========================================
# BOT SETUP
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# MEMORY
# ==========================================

user_memory = {}
MAX_MEMORY = 25

# ==========================================
# AI SETTINGS
# ==========================================

AI_COOLDOWN = 2
ai_lock = asyncio.Lock()

PERSONALITY = (
    "You are Julia. "
    "You speak casually and confidently like a real human woman. "
    "You are funny, snappy, chaotic, but still friendly. "
    "You keep sentences short but expressive. "
    "You remember previous conversation messages."
)

# ==========================================
# AI GENERATION
# ==========================================

async def generate_ai_response(user_id, message):

    async with ai_lock:

        while True:

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

                await asyncio.sleep(AI_COOLDOWN)

                return reply

            except Exception as e:

                error = str(e)

                if "429" in error or "quota" in error.lower():

                    print("Rate limit hit. Waiting 20 seconds...")
                    await asyncio.sleep(20)

                else:

                    print("Gemini error:", e)
                    return "My brain just crashed for a second."

# ==========================================
# SLASH COMMAND
# ==========================================

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
            "Julia's brain froze for a moment.",
            ephemeral=True
        )

# ==========================================
# !CHAT COMMAND
# ==========================================

@bot.command()
async def chat(ctx, *, message: str):

    reply = await generate_ai_response(
        ctx.author.id,
        message
    )

    await ctx.send(reply)

# ==========================================
# READY EVENT
# ==========================================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    try:

        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")

    except Exception as e:

        print("Sync error:", e)

# ==========================================
# MENTION + DM CHAT
# ==========================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Respond in DMs
    if message.guild is None:

        reply = await generate_ai_response(
            message.author.id,
            message.content
        )

        await message.channel.send(reply)

        return

    # Respond when mentioned
    if bot.user in message.mentions:

        clean = message.content.replace(
            f"<@{bot.user.id}>",
            ""
        ).strip()

        if clean:

            reply = await generate_ai_response(
                message.author.id,
                clean
            )

            await message.channel.send(reply)

    await bot.process_commands(message)

# ==========================================
# RUN BOT
# ==========================================

bot.run(DISCORD_TOKEN)
bot.run(DISCORD_TOKEN)

