import telebot

# Yahan apna real token paste karein (Double quotes "" ke andar)
API_TOKEN = "8702563696:AAHb9hNZ4Q8Y5lnBOrr7AbooyLicmczV1bg"

bot = telebot.TeleBot(API_TOKEN)

# Naye aane wale aur left hone wale users ke messages instantly delete karne ke liye
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        # Jaise he message screen par show ho, instantly delete ho jaye
        bot.delete_message(message.chat.id, message.message_id)
        print(f"Instantly deleted system message: {message.message_id}")
    except Exception as e:
        print(f"Error deleting message: {e}")

if __name__ == "__main__":
    print("Gold Expert Helper Bot is active and running securely...")
    # non_stop parameter ko hata diya hai taake crash na ho
    bot.infinity_polling(timeout=10)
    
