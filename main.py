import os
import base64
import zlib
import marshal
import dis
from io import StringIO
from telegram import Update, BotCommand, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from threading import Thread
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = ''

COMMANDS = [
    BotCommand("start", "Show welcome message"),
    BotCommand("id", "Show your Telegram ID"),
    BotCommand("help", "Get help with the bot"),
    BotCommand("decode", "Decode an obfuscated Python file")
]

@app.route('/')
def home():
    return "Telegram Deobfuscator Bot is running!"

def set_commands(updater: Updater):
    updater.bot.set_my_commands(commands=COMMANDS)

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(
        f"🛠 <b>Python Deobfuscator Bot</b>\n\n"
        f"👤 <b>Your ID:</b> <code>{user.id}</code>\n\n"
        "Send me an obfuscated .py file or use /decode command\n\n"
        "<b>Available commands:</b>\n"
        "/start - Show this message\n"
        "/id - Show your Telegram ID\n"
        "/help - Show help information\n"
        "/decode - Decode a Python file",
        parse_mode='HTML'
    )

def show_id(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(
        f"👤 <b>Your Telegram ID:</b> <code>{user.id}</code>",
        parse_mode='HTML'
    )

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🤖 <b>Python Deobfuscator Bot Help</b>\n\n"
        "This bot decodes obfuscated Python files that use common patterns.\n\n"
        "<b>Supported Patterns:</b>\n"
        "- exec + base64 + zlib + marshal\n"
        "- Multi-layer encoded Python\n\n"
        "<b>How to use:</b>\n"
        "1. Send me an obfuscated .py file\n"
        "2. Or use /decode command\n\n"
        "<b>Commands:</b>\n"
        "/start - Show welcome message\n"
        "/id - Show your Telegram ID\n"
        "/help - This help message\n"
        "/decode - Decode a Python file",
        parse_mode='HTML'
    )

def decode_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📁 Please send me the obfuscated Python file you want to decode.\n"
        "It should use the common exec+base64+zlib+marshal pattern."
    )

def extract_payload(content: str) -> str:
    start = content.find('("') + 2
    end = content.rfind('")')
    if start < 2 or end < 0:
        raise ValueError("Could not find encoded payload in the file")
    return content[start:end]

def decode_obfuscated(payload: str) -> str:
    reversed_b64 = payload[::-1]
    decoded_bytes = base64.b64decode(reversed_b64)
    decompressed = zlib.decompress(decoded_bytes)
    code_obj = marshal.loads(decompressed)
    return decompile_code(code_obj)

def decompile_code(code_obj) -> str:
    try:
        import uncompyle6
        output = StringIO()
        uncompyle6.uncompyle(code_obj, out=output)
        return output.getvalue()
    except ImportError:
        output = []
        for instr in dis.get_instructions(code_obj):
            output.append(f"{instr.opname} {instr.argrepr}")
        return "⚠ uncompyle6 not installed. Showing bytecode:\n\n" + "\n".join(output)

def handle_document(update: Update, context: CallbackContext) -> None:
    if not update.message.document.file_name.endswith('.py'):
        update.message.reply_text("❌ Please send a .py file")
        return

    update.message.reply_text("🔍 Decoding file, please wait...")
    
    try:
        file = context.bot.get_file(update.message.document.file_id)
        file.download('temp.py')
        
        with open('temp.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        payload = extract_payload(content)
        decoded_code = decode_obfuscated(payload)
        
        decoded_code = f"// Decoded for user ID: {update.effective_user.id}\n\n" + decoded_code
        
        with open('decoded_output.txt', 'w', encoding='utf-8') as f:
            f.write(decoded_code)
        
        with open('decoded_output.txt', 'rb') as f:
            update.message.reply_document(
                document=InputFile(f, filename='decoded_output.txt'),
                caption="✅ Here's your decoded file",
                parse_mode='HTML'
            )
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        for filename in ['temp.py', 'decoded_output.txt']:
            if os.path.exists(filename):
                os.remove(filename)

def run_bot():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("id", show_id))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("decode", decode_command))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))

    set_commands(updater)
    updater.start_polling()
    updater.idle()

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        exit(1)
    
    os.system('pip install python-telegram-bot==13.7 uncompyle6==3.8.0 flask==2.0.1')
    
    Thread(target=run_bot).start()
    Thread(target=run_flask).start()
