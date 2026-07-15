import os
import telebot

# Render ke environment variables se token retrieve karega
API_TOKEN = os.environ.get('8702563696:AAHb9hNZ4Q8Y5lnBOrr7AbooyLicmczV1bg')

# Bot instance initialize karein
bot = telebot.TeleBot(API_TOKEN)

# Real-time Join aur Left wale system messages ko instantly delete karne ke liye
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        # Jaise he message aye, instantly delete ho jaye
        bot.delete_message(message.chat.id, message.message_id)
        print(f"Instantly deleted join/left notification: {message.message_id}")
    except Exception as e:
        print(f"Error deleting message: {e}")

# Agar aapko pehle se maujood (old) messages ko manually ek baar saaf karna ho,
# to is function ko use kar sakte hain (isay start par chalane ke liye niche enable kar sakte hain)
def delete_old_notifications(chat_id, limit=100):
    try:
        print(f"Scanning last {limit} messages for old notifications...")
        history = bot.get_history(chat_id, limit=limit)
        for msg in history:
            if msg.content_type in ['new_chat_members', 'left_chat_member']:
                try:
                    bot.delete_message(chat_id, msg.message_id)
                    print(f"Deleted old system message: {msg.message_id}")
                except Exception:
                    pass
    except Exception as e:
        print(f"Could not retrieve history: {e}")

if __name__ == "__main__":
    print("Gold Expert Helper Bot is active and running...")
    
    # [Optional] Agar pehle se maujood system messages delete karne hain,
    # to niche wali line se '#' hata kar apne group ki ID likh dein (e.g. -100xxxxxxxxxx)
    # delete_old_notifications(-100xxxxxxxxx)
    
    # non_stop=True aur timeout=10 bot ki speed ko super-fast aur stable rakhta hai
    bot.infinity_polling(non_stop=True, timeout=10)
    
