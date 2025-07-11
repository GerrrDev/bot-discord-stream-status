import discord
from discord.ext import commands, tasks
import os
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
print(f"Token leído: {TOKEN[:10]}...")  # Muestra sólo las primeras 10 letras para no exponer el token completo
print(f"Token tipo: {type(TOKEN)}")
print(f"Token es None? {'Sí' if TOKEN is None else 'No'}")
print(f"Token está vacío? {'Sí' if TOKEN == '' else 'No'}")

if TOKEN is None or TOKEN == "":
    print("ERROR: El token de Discord no está definido o está vacío. Verifica tu variable de entorno DISCORD_TOKEN.")
    exit(1)

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USER = os.getenv("TWITCH_USER")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MESSAGE_ID = os.getenv("MESSAGE_ID")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

twitch_token = None

custom_status_today = ""
custom_horario_uy = ("18:00", "22:00")  # inicio, fin
stream_cancelado = False

horario_offsets = {
    "Chile": -1,
    "Colombia": -2,
    "España": +5,
    "México": -3,
    "Perú": -2
}

flags = {
    "Uruguay": "🇺🇾",
    "Chile": "🇨🇱",
    "Colombia": "🇨🇴",
    "España": "🇪🇸",
    "México": "🇲🇽",
    "Perú": "🇵🇪"
}

async def get_twitch_token():
    global twitch_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            twitch_token = data.get("access_token")

async def check_stream():
    global twitch_token
    if not twitch_token:
        await get_twitch_token()
    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USER}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            return len(data.get("data", [])) > 0

def ajustar_horario(uy_inicio, uy_fin, offset):
    fmt = "%H:%M"
    dt_inicio = datetime.strptime(uy_inicio, fmt)
    dt_fin = datetime.strptime(uy_fin, fmt)
    dt_inicio += timedelta(hours=offset)
    dt_fin += timedelta(hours=offset)
    return dt_inicio.strftime(fmt), dt_fin.strftime(fmt)

async def update_embed():
    channel = bot.get_channel(CHANNEL_ID)
    message = None
    if MESSAGE_ID and MESSAGE_ID != "":
        try:
            message = await channel.fetch_message(int(MESSAGE_ID))
        except Exception as e:
            print(f"No se pudo obtener el mensaje: {e}")
            message = None

    # Hora local de Uruguay (UTC-3)
    now = datetime.utcnow() - timedelta(hours=3)
    weekday = now.weekday()

    online = await check_stream()
    status = "ON" if online else "OFF"

    if stream_cancelado or weekday >= 5:
        estado_detallado = "❌ Hoy no hay stream"
    elif status == "OFF":
        estado_detallado = "⏳ Hoy hay stream"
    else:
        estado_detallado = "✅ Stream activo ahora mismo"

    embed_color = 0x2ecc71 if status == "ON" else 0x9146FF  # Verde ON, Morado Twitch OFF

    uy_inicio, uy_fin = custom_horario_uy
    horarios = [f"{flags['Uruguay']} {uy_inicio} - {uy_fin}"]

    for pais, offset in horario_offsets.items():
        inicio, fin = ajustar_horario(uy_inicio, uy_fin, offset)
        flag = flags[pais]
        horarios.append(f"{flag} {inicio} - {fin}")

    embed = discord.Embed(
        title="🚨 Estado del Stream de Cholito_o:",
        color=embed_color
    )

    estado_actual = "🟢 **ON**" if status == "ON" else "🔴 **OFF**"

    embed.add_field(name="Estado actual :", value=estado_actual, inline=False)
    embed.add_field(name="Estado detallado :", value=estado_detallado, inline=False)
    embed.add_field(name="Horario del stream:", value="\n".join(horarios), inline=False)

    embed.add_field(
        name="",
        value=(
            "⚠️ Recuerda que en Instagram siempre se avisa antes que en cualquier otro lugar "
            "sobre cambios o streams especiales.\n\n"
            "👉 Síguelo para no perderte nada: https://www.instagram.com/cholit0_o/"
        ),
        inline=False
    )

    embed.set_footer(text=f"Última actualización: {now.strftime('%d-%m-%Y %H:%M')} (UY)")
    embed.set_thumbnail(url="https://static-cdn.jtvnw.net/jtv_user_pictures/cholito_o-profile_image-70a1a8e045a2c260-70x70.png")

    if message:
        await message.edit(embed=embed)
    else:
        m = await channel.send(embed=embed)
        print(f"Nuevo mensaje ID: {m.id}")

@tasks.loop(minutes=1)
async def periodic_update():
    await update_embed()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def cancelar(ctx):
    global stream_cancelado
    stream_cancelado = True
    await ctx.send("✅ El stream de hoy ha sido cancelado.")
    await update_embed()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def horario(ctx, inicio: str, fin: str):
    global custom_horario_uy
    custom_horario_uy = (inicio, fin)
    await ctx.send(f"✅ Horario actualizado: 🇺🇾 {inicio} - {fin}")
    await update_embed()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def reset(ctx):
    global stream_cancelado, custom_horario_uy
    stream_cancelado = False
    custom_horario_uy = ("18:00", "22:00")
    await ctx.send("✅ Estado y horario reseteados a los valores por defecto.")
    await update_embed()

@bot.event
async def on_ready():
    print(f"{bot.user} está listo.")
    await update_embed()  # Primer update inmediato
    periodic_update.start()

bot.run(TOKEN)
