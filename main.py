import logging

import telebot

from bot import config, handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    bot = telebot.TeleBot(config.BOT_TOKEN, threaded=True)
    handlers.register(bot)
    logging.getLogger(__name__).info("Bot started, polling...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
