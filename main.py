import telebot
from telebot import types
from yt_dlp import YoutubeDL
import instaloader
import logging

# Установите токен вашего бота здесь
bot = telebot.TeleBot('7618745443:AAHb315qHE3E3Le5bFapyyhB_imUlCwWqgo')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

markup = types.InlineKeyboardMarkup()
btn_1 = types.InlineKeyboardButton('▶️ YouTube', callback_data='dlyou')
btn_2 = types.InlineKeyboardButton('📸 Instagram', callback_data='dlins')
markup.row(btn_2, btn_1)

L = instaloader.Instaloader()

# Учетные данные Instagram
USERNAME = 'your_username'  # Замените на ваше имя пользователя Instagram
PASSWORD = 'your_password'  # Замените на ваш пароль Instagram

# Попробуем авторизацию без входа в аккаунт
# L.login(USERNAME, PASSWORD)

# Добавим словарь для отслеживания состояния обработки сообщений
message_processing = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        f'<strong>Привет, {message.from_user.first_name}!</strong> 😊'
        f'\nЯ твой помощник по скачиванию контента.\nВыбери, из какой соцсети мы будем скачивать 🤖:', parse_mode='html',
        reply_markup=markup
    )

@bot.message_handler(commands=['more'])
def more(message):
    bot.send_message(message.chat.id,
        f'<strong>Выбрать другую социальную сеть</strong> 🤖:\n', parse_mode='html',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == 'dlyou' or call.data == 'retry_dlyou':
        markup_back = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('🔙 Назад', callback_data='back')
        markup_back.row(btn_back)
        msg = bot.edit_message_text('▶️ <b>YouTube</b>\n Отправляйте ссылку...', call.message.chat.id, call.message.message_id, reply_markup=markup_back, parse_mode='html')
        bot.register_next_step_handler(msg, lambda msg: process_youtube_link(msg, call.message))
    elif call.data == 'dlins' or call.data == 'retry_dlins':
        markup_back = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('🔙 Назад', callback_data='back')
        markup_back.row(btn_back)
        msg = bot.edit_message_text('📸 <b>Instagram</b>\n Отправляйте ссылку...', call.message.chat.id, call.message.message_id, reply_markup=markup_back, parse_mode='html')
        bot.register_next_step_handler(msg, lambda msg: process_instagram_link(msg, call.message))
    elif call.data == 'back':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        more(call.message)

def process_youtube_link(message, instruction_message):
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "Команда не распознана. Попробуйте снова.")
        return
    if message.message_id in message_processing:
        return
    message_processing[message.message_id] = True
    processing_message = bot.send_message(message.chat.id, 'Ваша ссылка обрабатывается... ⏳')
    handle_youtube_link(message, processing_message, instruction_message)
    del message_processing[message.message_id]

def process_instagram_link(message, instruction_message):
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "Команда не распознана. Попробуйте снова.")
        return
    if message.message_id in message_processing:
        return
    message_processing[message.message_id] = True
    processing_message = bot.send_message(message.chat.id, 'Ваша ссылка обрабатывается... ⏳')
    handle_instagram_link(message, processing_message, instruction_message)
    del message_processing[message.message_id]

def handle_instagram_link(message, processing_message, instruction_message):
    url = message.text
    try:
        post = instaloader.Post.from_shortcode(L.context, url.split("/")[-2])
        if post.is_video:
            video_url = post.video_url
            bot.send_video(message.chat.id, video_url, caption='Ваше видео 🎬')
        elif post.typename == 'GraphSidecar':
            media_urls = [node.display_url for node in post.get_sidecar_nodes() if not node.is_video]
            media_count = len(media_urls)
            if media_count > 0:
                bot.send_message(message.chat.id, f'Ваши фото: {media_count} шт. 📸')
                media_group = [types.InputMediaPhoto(url) for url in media_urls]
                bot.send_media_group(message.chat.id, media_group)
            else:
                bot.send_message(message.chat.id, "Не удалось найти фотографии в этом посте.")
        else:
            bot.send_photo(message.chat.id, post.url, caption='Ваше фото 📸')
        send_retry_button(message, 'retry_dlins')
    except instaloader.exceptions.BadResponseException as e:
        logging.error(f"Error while processing Instagram link {url}: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении данных с Instagram. Пожалуйста, попробуйте позже.")
        send_retry_button(message, 'retry_dlins')
    except instaloader.exceptions.ConnectionException as e:
        logging.error(f"Connection error while processing Instagram link {url}: {e}")
        bot.send_message(message.chat.id, "Проблема с соединением при получении данных с Instagram. Попробуйте еще раз.")
        send_retry_button(message, 'retry_dlins')
    except instaloader.exceptions.PrivateProfileNotFollowedException as e:
        logging.error(f"Private profile error while processing Instagram link {url}: {e}")
        bot.send_message(message.chat.id, "Этот профиль является приватным, и мы не можем получить доступ к его контенту.")
        send_retry_button(message, 'retry_dlins')
    except Exception as e:
        logging.error(f"Unexpected error while processing Instagram link {url}: {e}")
        bot.send_message(message.chat.id, "Произошла неизвестная ошибка. Пожалуйста, попробуйте позже.")
        send_retry_button(message, 'retry_dlins')
    finally:
        bot.delete_message(message.chat.id, processing_message.message_id)
        bot.delete_message(message.chat.id, instruction_message.message_id)  # Удаляем сообщение с инструкциями и кнопкой "Назад"
        bot.delete_message(message.chat.id, message.message_id)  # Удаляем сообщение с ссылкой пользователя

def handle_youtube_link(message, processing_message, instruction_message):
    url = message.text
    ydl_opts = {'format': 'best'}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_url = info_dict.get("url", None)
            video_title = info_dict.get('title', None)
            bot.send_video(message.chat.id, video_url, caption=f'Ваше видео: {video_title} 🎬')
        send_retry_button(message, 'retry_dlyou')
    except Exception as e:
        logging.error(f"Error while processing link {url}: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при обработке ссылки. 😞")
        send_retry_button(message, 'retry_dlyou')
    finally:
        bot.delete_message(message.chat.id, processing_message.message_id)
        bot.delete_message(message.chat.id, instruction_message.message_id)  # Удаляем сообщение с инструкциями и кнопкой "Назад"
        bot.delete_message(message.chat.id, message.message_id)  # Удаляем сообщение с ссылкой пользователя

def send_retry_button(message, callback_data):
    markup_retry = types.InlineKeyboardMarkup()
    btn_retry = types.InlineKeyboardButton('🔄 Попробовать еще раз', callback_data=callback_data)
    markup_retry.row(btn_retry)
    bot.send_message(message.chat.id, 'Хотите попробовать снова? 🔄', reply_markup=markup_retry)

@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    bot.send_message(
        message.chat.id,
        f'<strong>{message.from_user.first_name}, я пока что не умею общаться с тобой 😊, но в дальнейшем я уверен, что смогу научиться! 🚀</strong>',
        parse_mode='html'
    )

bot.polling(none_stop=True)
