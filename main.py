import os
import base64
import zlib
import marshal
import dis
from io import BytesIO, StringIO
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Replace with your actual bot token
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

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
    # Reverse the string (common obfuscation technique)
    reversed_b64 = payload[::-1]
    
    # Base64 decode → zlib decompress → marshal load
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
        # Fallback to bytecode disassembly
        output = []
        for instr in dis.get_instructions(code_obj):
            output.append(f"{instr.opname} {instr.argrepr}")
        return "⚠ uncompyle6 not installed. Showing bytecode:\n\n" + "\n".join(output)

def handle_document(update: Update, context: CallbackContext) -> None:
    """Handles incoming document (Python file)"""
    if not update.message.document.file_name.endswith('.py'):
        update.message.reply_text("❌ Please send a .py file")
        return

    # Download the file
    file = context.bot.get_file(update.message.document.file_id)
    file.download('temp.py')
    
    try:
        # Read and process the file
        with open('temp.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        payload = extract_payload(content)
        decoded_code = decode_obfuscated(payload)
        
        # Save as text file
        output_filename = 'decoded_output.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(decoded_code)
        
        # Send back the decoded file
        with open(output_filename, 'rb') as f:
            update.message.reply_document(
                document=InputFile(f, filename='decoded_output.txt'),
                caption="✅ Here's the decoded output"
            )
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        # Clean up temporary files
        if os.path.exists('temp.py'):
            os.remove('temp.py')
        if os.path.exists(output_filename):
            os.remove(output_filename)

def main() -> None:
    """Start the bot"""
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
