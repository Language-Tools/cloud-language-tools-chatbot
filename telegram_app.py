import logging
import os
import pprint
import tempfile

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)    

logger = logging.getLogger(__name__)

import cloudlanguagetools.servicemanager
import cloudlanguagetools_chatbot.chatmodel
import cloudlanguagetools.options

clt_manager = cloudlanguagetools.servicemanager.ServiceManager()
clt_manager.configure_default()

# docs
# https://github.com/python-telegram-bot/python-telegram-bot
# https://docs.python-telegram-bot.org/en/stable/
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot
# bot api features:
# https://core.telegram.org/bots/features#what-features-do-bots-have

import telegram

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import telegram.constants


TOKEN = os.environ['TELEGRAM_BOT_TOKEN']

def received_message_lambda(bot, chat_id):
    async def send_message(message): 
        await bot.send_message(chat_id=chat_id, text=message)
    return send_message

def received_audio_lambda(bot, chat_id):
    async def send_audio(audio_tempfile: tempfile.NamedTemporaryFile):
        # https://docs.python-telegram-bot.org/en/stable/telegram.bot.html#telegram.Bot.send_voice
        # tell using we are sending a voice note
        await bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.UPLOAD_VOICE)
        await bot.send_voice(chat_id=chat_id, voice=audio_tempfile.name)
    return send_audio

def received_error_lambda(bot, chat_id):
    async def send_error(message):
        await bot.send_message(chat_id=chat_id, text=f'error: {message}')
    return send_error

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, 
        text="Please enter a sentence in your target language (language that you are learning)")
    context.user_data.clear()
    context.user_data['chat_model'] = cloudlanguagetools_chatbot.chatmodel.ChatModel(clt_manager, 
        audio_format=cloudlanguagetools.options.AudioFormat.ogg_opus)
    # the chatmodel needs to know which functions to call when it has a message to send
    context.user_data['chat_model'].set_send_message_callback(
        received_message_lambda(context.bot, update.effective_chat.id),
        received_audio_lambda(context.bot, update.effective_chat.id),
        received_error_lambda(context.bot, update.effective_chat.id))

async def handle_set_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions = ' '.join(context.args)
    context.user_data['chat_model'].set_instruction(instructions)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"My instructions are now: {instructions}")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # tell user we are typing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    input_text = update.message.text
    await context.user_data['chat_model'].process_message(input_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # tell user we are typing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)

    # download file
    file_id = update.message.voice.file_id
    voice_note_file = await context.bot.getFile(file_id)
    voice_tempfile = tempfile.NamedTemporaryFile(prefix='telegram_voice_', suffix='.ogg')
    await voice_note_file.download_to_drive(voice_tempfile.name)

    # recognize text
    text = await context.user_data['chat_model'].process_audio(voice_tempfile)


if __name__ == '__main__':
    # set default basic logging with info level

    logging.info('starting up telegram bot')

    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler("start", start)
    set_instructions_handler = CommandHandler("set_instructions", handle_set_instructions)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_message)
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), handle_voice)

    application.add_handler(start_handler)
    application.add_handler(set_instructions_handler)
    application.add_handler(message_handler)
    application.add_handler(voice_handler)
    application.run_polling()