from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import DatabaseManager, create_collage, hide_img
import os
import cv2
from config import API_TOKEN, DATABASE
import threading
import schedule
import time

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)
manager.create_tables()

IMG_DIR = "img"
HIDDEN_IMG_DIR = "hidden_img"


def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=str(prize_id)))
    return markup


@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, "Привет! Добро пожаловать! Каждый час тебе будут приходить новые картинки. "
                              "Только три первых пользователя получат картинку!")


@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|' for x in res]
    res_text = '\n'.join(res)
    bot.send_message(message.chat.id, f"|USER_NAME    |COUNT_PRIZE|\n{res_text}")


@bot.message_handler(commands=['get_my_score'])
def get_my_score(message):
    user_id = message.chat.id
    prizes = manager.get_winners_img(user_id)

    if not prizes:
        bot.send_message(user_id, "У тебя пока нет призов!")
        return

    image_paths = [f"{IMG_DIR}/{x}" if x in prizes else f"{HIDDEN_IMG_DIR}/{x}" for x in os.listdir(IMG_DIR)]
    collage = create_collage(image_paths)
    if collage is None:
        bot.send_message(user_id, "Коллаж не удалось создать!")
        return

    temp_path = f"temp_{user_id}.png"
    cv2.imwrite(temp_path, collage)
    with open(temp_path, "rb") as f:
        bot.send_photo(user_id, f)
    os.remove(temp_path)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = int(call.data)
    user_id = call.message.chat.id

    if manager.get_winners_count(prize_id) < 3:
        res = manager.add_winner(user_id, prize_id)
        if res:
            img = manager.get_prize_img(prize_id)
            with open(f'{IMG_DIR}/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку!")
        else:
            bot.send_message(user_id, "Ты уже получил эту картинку!")
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз.")


def send_message():
    prize_data = manager.get_random_prize()
    if not prize_data:
        return

    prize_id, img, _ = prize_data
    manager.mark_prize_used(prize_id)
    hide_img(img)

    for user in manager.get_users():
        with open(f'{HIDDEN_IMG_DIR}/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))


def schedule_thread():
    schedule.every().hour.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)


def polling_thread():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    threading.Thread(target=polling_thread).start()
    threading.Thread(target=schedule_thread).start()
  
