import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import time
import threading

# =====================================================================
# ⚙️ CONFIGURATION
# =====================================================================
API_TOKEN = "8702563696:AAE5GVUaomXmBpbk-F8o4NU9qhG991YKmT8"  # Apne Bot ka real token dalein
OWNER_ID = 7415265825  # ⚠️ APNI Telegram ID dalein (E.g., 123456789)

# Channel & Group IDs
FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  

# Links
FREE_GROUP_LINK = "https://t.me/GoldExpertFxCommunity"
PRIVATE_CHANNEL_LINK = "https://t.me/+g8yrkwMU6DQ5M2U9"
BROKER_LINK = "https://www.brokeraccountguide.com/"
WHATSAPP_LINK = "https://whatsapp.com/channel/0029Vb5eRVjGzzKNnL7c050y"
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)

# Database Setup
def init_db():
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_requests (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# 👑 Owner Reply Keyboard (Fixed: Removed unexpected 'placeholder' to prevent crash)
def get_owner_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📢 Publish Post"), KeyboardButton("🚫 Ban User"))
    markup.row(KeyboardButton("⚙️ Settings"), KeyboardButton("📈 Status"))
    return markup


# 🏁 Start Command
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 'banned':
        conn.close()
        return
        
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
    conn.commit()
    conn.close()
    
    # 👑 OWNER DIRECT ENTRY (With custom persistent keyboard below)
    if user_id == OWNER_ID:
        bot.send_message(
            user_id, 
            "👑 **Admin Workspace Active**", 
            reply_markup=get_owner_reply_keyboard(), 
            parse_mode="Markdown"
        )
        send_main_menu(user_id, first_name)
        return

    # Normal users starting the bot
    send_force_join_screen(user_id, first_name)


# 🔒 Clean VIP Verification Screen (Sleek and compact)
def send_force_join_screen(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_community = InlineKeyboardButton("🔊 Free Group", url=FREE_GROUP_LINK)
    btn_private = InlineKeyboardButton("🔑 VIP Channel", url=PRIVATE_CHANNEL_LINK)
    btn_joined = InlineKeyboardButton("🟢 Continue", callback_data="check_membership")
    
    markup.add(btn_community, btn_private)
    markup.add(btn_joined)
    
    welcome_text = (
        f"👋 **Welcome {first_name}!**\n\n"
        f"Unlock your **Gold Expert FX** dashboard below:"
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


# 🔘 Join Verification Action (Bypassed! Even if not joined, they get access on click)
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check_membership(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "✨ Welcome!", show_alert=False)
    
    # Direct access granted to everyone on click!
    send_main_menu(user_id, first_name)


# 📱 Sleek VIP Dashboard Menu (Compact Buttons)
def send_main_menu(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_broker = InlineKeyboardButton("🌐 Recommend Broker", url=BROKER_LINK)
    btn_vip = InlineKeyboardButton("🥇 Free VIP", callback_data="join_vip_info")
    btn_whatsapp = InlineKeyboardButton("💬 WhatsApp", url=WHATSAPP_LINK)
    btn_support = InlineKeyboardButton("👤 Contact", callback_data="contact_owner_live")
    
    markup.add(btn_broker)
    markup.add(btn_vip, btn_whatsapp)
    markup.add(btn_support)
    
    menu_msg = (
        f"✨ **Gold Expert FX**\n\n"
        f"Hello **{first_name}**! Your access is active.\n"
        f"Select an option below:"
    )
    bot.send_message(user_id, menu_msg, reply_markup=markup, parse_mode="Markdown")


# ⌨️ Persistent Bottom Keyboard Actions (For Owner Only)
@bot.message_handler(func=lambda msg: msg.chat.id == OWNER_ID and msg.text in ["📢 Publish Post", "🚫 Ban User", "⚙️ Settings", "📈 Status"])
def handle_owner_reply_keyboard(message):
    action = message.text
    if action == "📢 Publish Post":
        msg = bot.send_message(OWNER_ID, "📝 Send or forward the **post** to broadcast:")
        bot.register_next_step_handler(msg, prepare_broadcast)
    elif action == "🚫 Ban User":
        msg = bot.send_message(OWNER_ID, "🚫 Send the user's numeric **Telegram ID** to ban:")
        bot.register_next_step_handler(msg, process_remove_user)
    else:
        bot.send_message(OWNER_ID, f"⚡ **{action}** is currently active.")


# ✉️ Interactive Dashboard Info
@bot.callback_query_handler(func=lambda call: call.data in ["join_vip_info", "contact_owner_live"])
def handle_menu_router(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if call.data == "join_vip_info":
        vip_text = (
            f"📈 **VIP Setup**\n\n"
            f"1️⃣ Register account using broker link.\n"
            f"2️⃣ Deposit & start trading.\n"
            f"3️⃣ Instant VIP validation!\n\n"
            f"🔗 **Guide:** {BROKER_LINK}"
        )
        bot.send_message(user_id, vip_text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "contact_owner_live":
        msg = bot.send_message(user_id, f"✍️ **Hi {first_name}!**\n\nType your message below. It will be sent straight to support.")
        bot.register_next_step_handler(msg, forward_to_owner)
        bot.answer_callback_query(call.id)


# 👤 Live Chat Support
def forward_to_owner(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    
    if text in ["/start", "/admin"]:
        return
        
    owner_notification = (
        f"📩 **New Msg**\n\n"
        f"👤 **From:** {first_name} (@{username})\n"
        f"🆔 **ID:** `{user_id}`\n\n"
        f"💬 **Message:** {text}"
    )
    
    try:
        sent_msg = bot.send_message(OWNER_ID, owner_notification, parse_mode="Markdown")
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO support_chats (message_id, user_id) VALUES (?, ?)", (sent_msg.message_id, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, "✅ **Message sent! We will reply shortly.**")
    except Exception:
        bot.send_message(user_id, "❌ Support busy. Try again later.")


# 🔄 Reply Handler
@bot.message_handler(func=lambda msg: msg.reply_to_message is not None)
def process_owner_reply(message):
    if message.from_user.id == OWNER_ID:
        reply_to_id = message.reply_to_message.message_id
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM support_chats WHERE message_id = ?", (reply_to_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user_id = row[0]
            try:
                bot.send_message(user_id, f"💬 **Message from Owner:**\n\n{message.text}")
                bot.send_message(OWNER_ID, "✅ **Reply Sent.**")
            except Exception:
                bot.send_message(OWNER_ID, "❌ Failed to deliver reply.")


# Broadcast Prep
def prepare_broadcast(message):
    global broadcast_msg_payload
    broadcast_msg_payload = message
    
    markup = InlineKeyboardMarkup()
    btn_send = InlineKeyboardButton("🚀 Broadcast Now", callback_data="confirm_send_all")
    markup.add(btn_send)
    
    bot.send_message(OWNER_ID, "👀 **Post loaded.** Dispatch broadcast?", reply_markup=markup, parse_mode="Markdown")


# Execute Broadcast
@bot.callback_query_handler(func=lambda call: call.data == "confirm_send_all")
def execute_broadcast(call):
    if call.from_user.id != OWNER_ID:
        return
        
    bot.edit_message_reply_markup(chat_id=OWNER_ID, message_id=call.message.message_id, reply_markup=None)
    bot.send_message(OWNER_ID, "🔄 **Sending broadcast...**")
    
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status = 'active'")
    all_users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for row in all_users:
        target_id = row[0]
        try:
            bot.copy_message(chat_id=target_id, from_chat_id=OWNER_ID, message_id=broadcast_msg_payload.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1
            
    bot.send_message(OWNER_ID, f"📢 **Broadcast Finished!**\n\n✅ Sent: {success}\n❌ Failed: {failed}", parse_mode="Markdown")
    bot.answer_callback_query(call.id)


# Block Execution
def process_remove_user(message):
    target_id = message.text.strip()
    if target_id.isdigit():
        target_id = int(target_id)
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'banned' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(OWNER_ID, f"✅ User `{target_id}` banned successfully.")
    else:
        bot.send_message(OWNER_ID, "❌ Enter digits only.")


# System Clean (No Join/Leave Spams)
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass


if __name__ == "__main__":
    print("Gold Expert VIP Master Robot is online...")
    bot.infinity_polling(timeout=15)
    
