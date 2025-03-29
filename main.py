from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import yt_dlp
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize the bot
app = Client("EchoStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queue to store songs
queue = []

# Function to download audio from YouTube
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return "audio.mp3", info['title']

# Command: /start
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await message.reply("Hello! I am EchoStream Bot. Use /play <song_name> or <YouTube URL> to play music in voice chat!")

# Command: /play
@app.on_message(filters.command("play") & filters.group)
async def play_command(client, message: Message):
    query = " ".join(message.command[1:])
    if not query:
        await message.reply("Please provide a song name or YouTube URL!")
        return

    chat_id = message.chat.id
    try:
        # If it's a URL, use it directly; otherwise, search on YouTube
        if "youtube.com" in query or "youtu.be" in query:
            url = query
        else:
            url = f"ytsearch:{query}"
        
        # Download the audio
        audio_file, title = download_audio(url)
        
        # Add to queue if something is already playing
        if app.is_playing(chat_id):
            queue.append((audio_file, title))
            await message.reply(f"Added '{title}' to the queue!")
            return
        
        # Play the audio in VC
        await app.join_group_call(chat_id, audio_file)
        await message.reply(f"Now playing: {title}")
        
        # Monitor when the song ends and play next in queue
        while app.is_playing(chat_id):
            await asyncio.sleep(5)
        
        # Cleanup
        os.remove(audio_file)
        
        # Play next song in queue
        if queue:
            next_audio, next_title = queue.pop(0)
            await app.join_group_call(chat_id, next_audio)
            await message.reply(f"Now playing: {next_title}")
            os.remove(next_audio)
        
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

# Command: /skip
@app.on_message(filters.command("skip") & filters.group)
async def skip_command(client, message: Message):
    chat_id = message.chat.id
    if not app.is_playing(chat_id):
        await message.reply("Nothing is playing!")
        return
    
    await app.stop_group_call(chat_id)
    if queue:
        next_audio, next_title = queue.pop(0)
        await app.join_group_call(chat_id, next_audio)
        await message.reply(f"Now playing: {next_title}")
        os.remove(next_audio)
    else:
        await message.reply("Queue is empty!")

# Command: /queue
@app.on_message(filters.command("queue") & filters.group)
async def queue_command(client, message: Message):
    if not queue:
        await message.reply("Queue is empty!")
    else:
        queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(queue)])
        await message.reply(f"Current queue:\n{queue_list}")

# Command: /stop
@app.on_message(filters.command("stop") & filters.group)
async def stop_command(client, message: Message):
    chat_id = message.chat.id
    if not app.is_playing(chat_id):
        await message.reply("Nothing is playing!")
        return
    
    await app.stop_group_call(chat_id)
    queue.clear()
    await message.reply("Stopped the music and cleared the queue!")

# Run the bot
if __name__ == "__main__":
    print("EchoStream Bot is starting...")
    app.run(
