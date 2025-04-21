
import openai
import os
import csv
import datetime
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

(ASK_NAME, ASK_AGE, ASK_WEIGHT, ASK_FTP, ASK_GOAL, ASK_SWIM_PACE, ASK_RESULTS, FEEDBACK) = range(8)
user_data = {}

def start(update, context):
    update.message.reply_text("Йоу, бро! Давай тебя зарегаем. Как тебя звать, хоуми?")
    return ASK_NAME

def ask_age(update, context):
    user_data["name"] = update.message.text
    update.message.reply_text("Сколько тебе лет, чувак?")
    return ASK_AGE

def ask_weight(update, context):
    user_data["age"] = update.message.text
    update.message.reply_text("Сколько вешаем, брат? (в кг)")
    return ASK_WEIGHT

def ask_ftp(update, context):
    user_data["weight"] = update.message.text
    update.message.reply_text("Ну и FTP твой какой? Не стесняйся.")
    return ASK_FTP

def ask_goal(update, context):
    user_data["ftp"] = update.message.text
    update.message.reply_text("Какая у тебя цель, зверюга? Ironman или ты просто кайфуешь?")
    return ASK_GOAL

def ask_swim_pace(update, context):
    user_data["goal"] = update.message.text
    update.message.reply_text("Если шаришь в бассейне — напиши свой темп (например, 2:00 / 100 м).")
    return ASK_SWIM_PACE

def ask_results(update, context):
    user_data["swim_pace"] = update.message.text
    update.message.reply_text("Кинь фотку или файл с прошлыми стартами, если есть. Или просто ссылку. Будет круто.")
    return ASK_RESULTS

def save_results(update, context):
    user = update.message.from_user.username or update.message.from_user.id
    user_data["username"] = user
    user_data["date"] = str(datetime.date.today())

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file = context.bot.get_file(file_id)
        file_path = f"{user}_results.jpg"
        file.download(file_path)
        user_data["results_file"] = file_path
    elif update.message.document:
        file = context.bot.get_file(update.message.document.file_id)
        file_path = f"{user}_results_{update.message.document.file_name}"
        file.download(file_path)
        user_data["results_file"] = file_path
    else:
        user_data["results_file"] = "Нет файла"

    with open("users.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=user_data.keys())
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(user_data)

    update.message.reply_text("Бро, ты в системе. Красавчик. Пиши /plan и получай задание!")
    return ConversationHandler.END

def send_plan(update, context):
    today = str(datetime.date.today())
    plan = f"Ну чё, {today} у нас жарища:\n- 60 мин вело в Z2 (каденс 85–90)\n- Каждые 30 мин — угли, чувак\n- И заминка, как у чемпиона"
    update.message.reply_text(plan)

def start_feedback(update, context):
    update.message.reply_text("Йоу! Как прошла сессия, бро? Напиши: [Оценка 1–10, Где развалился, Как спал]")
    return FEEDBACK

def save_feedback(update, context):
    user = update.message.from_user.username or update.message.from_user.id
    today = str(datetime.date.today())
    feedback_text = update.message.text
    with open("feedback_log.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([user, today, feedback_text])
    update.message.reply_text("Принял, брат! Всё запишу, потом разберём.")
    return ConversationHandler.END

def gpt_response(update, context):
    prompt = update.message.text
    reply = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Ты — дерзкий, уличный, но заботливый тренер, который говорит 'бро', 'чувак', 'хоуми', не церемонится, но даёт топ советы."},
            {"role": "user", "content": prompt}
        ]
    ).choices[0].message["content"]
    update.message.reply_text(reply)

def cancel(update, context):
    update.message.reply_text("Окей, бро. Регу скипаем.")
    return ConversationHandler.END

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    registration = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_age)],
            ASK_AGE: [MessageHandler(Filters.text & ~Filters.command, ask_weight)],
            ASK_WEIGHT: [MessageHandler(Filters.text & ~Filters.command, ask_ftp)],
            ASK_FTP: [MessageHandler(Filters.text & ~Filters.command, ask_goal)],
            ASK_GOAL: [MessageHandler(Filters.text & ~Filters.command, ask_swim_pace)],
            ASK_SWIM_PACE: [MessageHandler(Filters.text & ~Filters.command, ask_results)],
            ASK_RESULTS: [MessageHandler(Filters.document | Filters.photo | Filters.text, save_results)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    feedback_conv = ConversationHandler(
        entry_points=[CommandHandler("feedback", start_feedback)],
        states={FEEDBACK: [MessageHandler(Filters.text & ~Filters.command, save_feedback)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(registration)
    dp.add_handler(feedback_conv)
    dp.add_handler(CommandHandler("plan", send_plan))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, gpt_response))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
