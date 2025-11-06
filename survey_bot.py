#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import json
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States
FULL_NAME, BIRTH_DATE, PROTOCOL_DATE, COURT_HEARING, PHONE = range(5)
RESULTS_FILE = 'survey_results.json'

# ВАЖНО: Замените на ID вашей группы/канала
# Чтобы получить ID: добавьте бота в группу, напишите что-то, бот залогирует chat_id
ADMIN_GROUP_ID = -1003266963357


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the survey"""
    await update.message.reply_text(
        "👋 Вітаю! Ви звернулися до юридичного бота щодо оскарження постанови за ч. 1 ст. 130 КУпАП.\n\n"
        "Я допоможу зібрати попередню інформацію, щоб наш юрист зміг з вами зв'язатися.\n\n"
        "📌 Будь ласка, вкажіть ваше прізвище, ім'я та по батькові."
    )
    return FULL_NAME


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store full name"""
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("📌 Вкажіть вашу дату народження (наприклад: 01.01.1990)")
    return BIRTH_DATE


async def get_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store birth date"""
    context.user_data['birth_date'] = update.message.text
    await update.message.reply_text("📌 Коли саме було складено протокол? (наприклад: 15.10.2025)")
    return PROTOCOL_DATE


async def get_protocol_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store protocol date"""
    context.user_data['protocol_date'] = update.message.text
    
    # Кнопки да/нет
    keyboard = [
        [KeyboardButton("Так"), KeyboardButton("Ні")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📌 Чи було вже судове засідання по вашій справі?",
        reply_markup=reply_markup
    )
    return COURT_HEARING


async def get_court_hearing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store court hearing answer"""
    answer = update.message.text.lower()
    
    if answer not in ['так', 'ні', 'да', 'нет', 'yes', 'no']:
        await update.message.reply_text("Будь ласка, оберіть 'Так' або 'Ні'")
        return COURT_HEARING
    
    context.user_data['court_hearing'] = update.message.text
    
    # Request phone
    contact_button = KeyboardButton("📱 Поділитися контактом", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📌 Залиште, будь ласка, ваш номер телефону для зв'язку.",
        reply_markup=keyboard
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store phone and complete survey"""
    user = update.effective_user
    
    # Get phone
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = "Не надано"
    
    # Collect all data
    survey_data = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user.id,
        'username': user.username if user.username else "Немає username",
        'first_name': user.first_name,
        'last_name': user.last_name if user.last_name else "",
        'full_name': context.user_data.get('full_name'),
        'birth_date': context.user_data.get('birth_date'),
        'protocol_date': context.user_data.get('protocol_date'),
        'court_hearing': context.user_data.get('court_hearing'),
        'phone': phone
    }
    
    # Save to file
    try:
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except FileNotFoundError:
            results = []
        
        results.append(survey_data)
        
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving: {e}")
    
    # Send to admin group if configured
    if ADMIN_GROUP_ID:
        try:
            admin_message = (
                "🔔 <b>Нова заявка</b>\n\n"
                f"<b>ПІБ:</b> {survey_data['full_name']}\n"
                f"<b>Дата народження:</b> {survey_data['birth_date']}\n"
                f"<b>Дата протоколу:</b> {survey_data['protocol_date']}\n"
                f"<b>Судове засідання:</b> {survey_data['court_hearing']}\n"
                f"<b>Телефон:</b> {phone}\n\n"
                f"<b>Telegram:</b> @{survey_data['username']}\n"
                f"<b>User ID:</b> <code>{survey_data['user_id']}</code>\n"
                f"<b>Час:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=admin_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending to admin group: {e}")
    
    # User confirmation
    summary = (
        "✅ Дякуємо!\n\n"
        "Я передам ваші дані юристу. Він зателефонує найближчим часом, щоб уточнити деталі.\n\n"
        "ℹ️ Ваші дані обробляються лише для надання юридичної допомоги та не передаються третім особам.\n\n"
        "Для нового звернення використовуйте /start"
    )
    
    await update.message.reply_text(summary, reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel survey"""
    await update.message.reply_text(
        "Опитування скасовано. Для нового звернення використовуйте /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def main():
    """Start the bot"""
    TOKEN = "8393177001:AAF9SvllSF3FkTSAVhxl47hEZsvMf9gzHok"
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_date)],
            PROTOCOL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_protocol_date)],
            COURT_HEARING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_court_hearing)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    print("\n" + "="*50)
    print("🤖 BOT IS RUNNING!")
    print("📱 Open: https://t.me/my_survey_130_bot")
    print("="*50 + "\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
