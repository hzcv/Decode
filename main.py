import os
import base64
import zlib
import marshal
import dis
from io import StringIO
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from threading import Thread
from flask import Flask, jsonify

app = Flask(__name__)

# Get bot token from Replit secrets
BOT_TOKEN = os.environ.get('BOT_TOKEN')

@app.route('/')
def home():
    return "Telegram Deobfuscator Bot is running!"

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🛠 Python Deobfuscator Bot\n\n"
        "Send me an obfuscated .py file (with exec+base64+zlib+marshal pattern) "
        "and I'll return the decoded human-readable version as a .txt file."
    )

def extract_payload(content: str) -> str:
    """Extracts the encoded payload from the obfuscated Python file"""
    start = content.find('("') + 2
    end = content.rfind('")')
    if start < 2 or end < 0:
        raise ValueError("Could not find encoded payload in the file")
    return content[start:end]

def decode_obfuscated(payload: str) -> str:
    """Decodes the multi-layer obfuscation"""
    reversed_b64 = payload[::-1]
    decoded_bytes = base64.b64decode(reversed_b64)
    decompressed = zlib.decompress(decoded_bytes)
    code_obj = marshal.loads(decompressed)
    return decompile_code(code_obj)

def decompile_code(code_obj) -> str:
    """Attempts to decompile the code object to Python source"""
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
    """Handles incoming document (Python file)"""
    if not update.message.document.file_name.endswith('.py'):
        update.message.reply_text("❌ Please send a .py file")
        return

    file = context.bot.get_file(update.message.document.file_id)
    file.download('temp.py')
    
    try:
        with open('temp.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        payload = extract_payload(content)
        decoded_code = decode_obfuscated(payload)
        
        with open('decoded_output.txt', 'w', encoding='utf-8') as f:
            f.write(decoded_code)
        
        with open('decoded_output.txt', 'rb') as f:
            update.message.reply_document(
                document=InputFile(f, filename='decoded_output.txt'),
                caption="✅ Here's the decoded output"
            )
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        for filename in ['temp.py', 'decoded_output.txt']:
            if os.path.exists(filename):
                os.remove(filename)

def run_bot():
    """Run the Telegram bot"""
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))

    updater.start_polling()
    updater.idle()

def run_flask():
    """Run the Flask web server"""
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        exit(1)
    
    # Install required packages
    os.system('pip install python-telegram-bot uncompyle6 flask')
    
    # Start bot and Flask in separate threads
    Thread(target=run_bot).start()
    Thread(target=run_flask).start()
