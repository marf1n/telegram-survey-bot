#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import json
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

NAME, BIRTH_YEAR, DEVICE_USAGE, PHONE = range(4)
RESULTS_FILE = 'survey_results.json'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в опрос!\n\n"
        "Вопрос 1/4: Как вас зовут? (Имя Фамилия)"
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Вопрос 2/4: Ваш год рождения?")
    return BIRTH_YEAR


async def get_birth_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birth_year = update.message.text
    
    try:
        year = int(birth_year)
        if 1900 <= year <= 2024:
            context.user_data['birth_year'] = birth_year
        else:
            await update.message.reply_text("Некорректный год. Введите год от 1900 до 2024:")
            return BIRTH_YEAR
    except ValueError:
        await update.message.reply_text("Введите год числом:")
        return BIRTH_YEAR
    
    await update.message.reply_text("Вопрос 3/4: Использовали ли вы аппарат? (да/нет)")
    return DEVICE_USAGE


async def get_device_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.lower()
    
    if answer not in ['да', 'нет', 'yes', 'no']:
        await update.message.reply_text("Ответьте 'да' или 'нет':")
        return DEVICE_USAGE
    
    context.user_data['device_usage'] = update.message.text
    
    contact_button = KeyboardButton("📱 Поделиться контактом", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text("Вопрос 4/4: Поделитесь контактом", reply_markup=keyboard)
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = "Not shared"
    
    survey_data = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user.id,
        'username': user.username if user.username else "No username",
        'first_name': user.first_name,
        'last_name': user.last_name if user.last_name else "",
        'name': context.user_data.get('name'),
        'birth_year': context.user_data.get('birth_year'),
        'device_usage': context.user_data.get('device_usage'),
        'phone': phone
    }
    
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
    
    summary = (
        "✅ Спасибо! Опрос завершен.\n\n"
        f"📋 Ваши данные:\n"
        f"• Имя: {survey_data['name']}\n"
        f"• Год рождения: {survey_data['birth_year']}\n"
        f"• Использовали аппарат: {survey_data['device_usage']}\n"
        f"• Telegram: @{survey_data['username']}\n"
        f"• User ID: {survey_data['user_id']}\n"
        f"• Телефон: {phone}\n\n"
        "Для нового опроса: /start"
    )
    
    await update.message.reply_text(summary, reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Опрос отменен. /start для нового", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


def main():
    TOKEN = "8393177001:AAF9SvllSF3FkTSAVhxl47hEZsvMf9gzHok"
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTH_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_year)],
            DEVICE_USAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_device_usage)],
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
