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
OWNER_ID = 7415265825  # ⚠️ APNI Telegram ID dalein

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


# 👑 Owner Reply Keyboard (Persistent Menu at Bottom)
def get_owner_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, placeholder="Owner Controls")
    markup.row(KeyboardButton("🎛️ Buttons Editor"), KeyboardButton("📝 Posts Editor"))
    markup.row(KeyboardButton("💵 Balance"), KeyboardButton("🔒 Admin"))
    return markup


# 🔍 Live Verification Status check
def verify_user_status(user_id):
    if user_id == OWNER_ID:
        return True, True

    in_free_group = False
    in_private_channel = False

    # 1. Free Group Check
    try:
        member = bot.get_chat_member(FREE_GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            in_free_group = True
    except ApiTelegramException:
        in_free_group = False

    # 2. Private VIP Request Check
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pending_requests WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is not None:
        in_private_channel = True
    else:
        try:
            member = bot.get_chat_member(PRIVATE_CHANNEL_ID, user_id)
            if member.status in ['member', 'administrator', 'creator', 'restricted']:
                in_private_channel = True
        except ApiTelegramException:
            in_private_channel = False
            
    return in_free_group, in_private_channel


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
    
    # 👑 OWNER DIRECT ENTRY (With persistent Keyboard)
    if user_id == OWNER_ID:
        bot.send_message(
            user_id, 
            "👑 **Welcome back, Admin!**\nYour control keyboard is activated below.", 
            reply_markup=get_owner_reply_keyboard(), 
            parse_mode="Markdown"
        )
        send_main_menu(user_id, first_name)
        return

    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        send_main_menu(user_id, first_name)
    else:
        send_force_join_screen(user_id, first_name)


# 🔒 Force Join Screen (Clean, Short, Premium Emojis)
def send_force_join_screen(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_community = InlineKeyboardButton("🔊 Join Free", url=FREE_GROUP_LINK)
    btn_private = InlineKeyboardButton("🔑 Request VIP", url=PRIVATE_CHANNEL_LINK)
    btn_joined = InlineKeyboardButton("✅ Done", callback_data="check_membership")
    
    markup.add(btn_community, btn_private)
    markup.add(btn_joined)
    
    welcome_text = (
        f"👋 **Welcome {first_name}!**\n\n"
        f"**Access Verification:**\n"
        f"1. Join our **Free Community**\n"
        f"2. Request access to **Private VIP**\n\n"
        f"Tap **✅ Done** once completed."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


# 🔘 Join Verification Action
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check_membership(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if user_id == OWNER_ID:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(user_id, first_name)
        return

    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✨ Verified!", show_alert=False)
        send_main_menu(user_id, first_name)
    else:
        if not in_free and not in_private:
            err_msg = "⚠️ Please join Free Community & request Private VIP first."
        elif not in_free:
            err_msg = "⚠️ You haven't joined the Free Community yet."
        else:
            err_msg = "⚠️ Please send a request to the Private VIP Channel."
            
        bot.answer_callback_query(call.id, err_msg, show_alert=True)


# 📱 Sleek Dashboard Menu (Shorter, Cleaner Inline Buttons)
def send_main_menu(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_broker = InlineKeyboardButton("🌐 Broker Guide", url=BROKER_LINK)
    btn_vip = InlineKeyboardButton("🥇 Join VIP", callback_data="join_vip_info")
    btn_whatsapp = InlineKeyboardButton("💬 WhatsApp", url=WHATSAPP_LINK)
    btn_support = InlineKeyboardButton("👤 Contact", callback_data="contact_owner_live")
    
    markup.add(btn_broker)
    markup.add(btn_vip, btn_whatsapp)
    markup.add(btn_support)
    
    menu_msg = (
        f"🏆 **Gold Expert FX**\n\n"
        f"Hello **{first_name}**! Your access is fully active.\n"
        f"Select an option below to start:"
    )
    bot.send_message(user_id, menu_msg, reply_markup=markup, parse_mode="Markdown")


# ⌨️ Handler for Owner Bottom Keyboard Menu Press
@bot.message_handler(func=lambda msg: msg.chat.id == OWNER_ID and msg.text in ["🎛️ Buttons Editor", "📝 Posts Editor", "💵 Balance", "🔒 Admin"])
def handle_owner_reply_keyboard(message):
    action = message.text
    if action == "🔒 Admin":
        handle_admin_panel(message)
    elif action == "📝 Posts Editor":
        msg = bot.send_message(OWNER_ID, "📢 Send or forward the **post** you want to broadcast:")
        bot.register_next_step_handler(msg, prepare_broadcast)
    else:
        # Placeholder responses for customization
        bot.send_message(OWNER_ID, f"⚡ **{action}** selected. (Under development / Customize as needed!)")


# ✉️ Interactive Dashboard Actions
@bot.callback_query_handler(func=lambda call: call.data in ["join_vip_info", "contact_owner_live"])
def handle_menu_router(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if call.data == "join_vip_info":
        vip_text = (
            f"📈 **VIP Setup Guide**\n\n"
            f"1️⃣ Create an account on our broker link.\n"
            f"2️⃣ Deposit & start trading.\n"
            f"3️⃣ Get verified for lifetime access!\n\n"
            f"🔗 **Link:** {BROKER_LINK}"
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
        f"📩 **New Message**\n\n"
        f"👤 **User:** {first_name} (@{username})\n"
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
    except Exception as e:
        bot.send_message(user_id, "❌ Service temporary offline. Try again later.")


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
            except Exception as e:
                bot.send_message(OWNER_ID, f"❌ Failed to deliver reply: {e}")


# 📥 Join Request Auto Approval
@bot.chat_join_request_handler()
def handle_incoming_request(update):
    if update.chat.id == PRIVATE_CHANNEL_ID:
        user_id = update.from_user.id
        first_name = update.from_user.first_name
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO pending_requests (user_id, first_name, status) VALUES (?, ?, 'pending')", (user_id, first_name))
        conn.commit()
        conn.close()
        
        in_free, _ = verify_user_status(user_id)
        if in_free:
            approve_user_access(user_id, first_name)


# Approver Execution
def approve_user_access(user_id, first_name):
    try:
        bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        try:
            bot.send_message(user_id, f"🎉 Join request approved! Welcome, **{first_name}**!")
        except Exception:
            pass
    except ApiTelegramException as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()


# Background scan for VIP approvals
def scan_all_pending_requests():
    while True:
        try:
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name FROM pending_requests WHERE status = 'pending'")
            all_pending = cursor.fetchall()
            conn.close()
            
            for user_id, first_name in all_pending:
                in_free, _ = verify_user_status(user_id)
                if in_free:
                    approve_user_access(user_id, first_name)
        except Exception as e:
            pass
        time.sleep(15)

threading.Thread(target=scan_all_pending_requests, daemon=True).start()


# 👑 ADMIN PANEL
def handle_admin_panel(message):
    markup = InlineKeyboardMarkup()
    btn_broadcast = InlineKeyboardButton("📢 Publish", callback_data="admin_broadcast")
    btn_remove = InlineKeyboardButton("❌ Ban User", callback_data="admin_remove")
    markup.add(btn_broadcast, btn_remove)
    
    bot.send_message(OWNER_ID, "🛠️ **Admin Controls**", reply_markup=markup, parse_mode="Markdown")


# Admin Actions Router
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id != OWNER_ID:
        return
        
    if call.data == "admin_broadcast":
        msg = bot.send_message(OWNER_ID, "📢 Send or forward the **post** to publish:")
        bot.register_next_step_handler(msg, prepare_broadcast)
        bot.answer_callback_query(call.id)
        
    elif call.data == "admin_remove":
        msg = bot.send_message(OWNER_ID, "🚫 Send the user's numeric **Telegram ID** to ban:")
        bot.register_next_step_handler(msg, process_remove_user)
        bot.answer_callback_query(call.id)


# Broadcast Prep
def prepare_broadcast(message):
    global broadcast_msg_payload
    broadcast_msg_payload = message
    
    markup = InlineKeyboardMarkup()
    btn_send = InlineKeyboardButton("🚀 Send All", callback_data="confirm_send_all")
    markup.add(btn_send)
    
    bot.send_message(OWNER_ID, "👀 **Post loaded.** Ready to broadcast?", reply_markup=markup, parse_mode="Markdown")


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
            
    bot.send_message(OWNER_ID, f"📢 **Broadcast Finished!**\n\n✅ Sent: {success}\n❌ Blocked: {failed}", parse_mode="Markdown")
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
        bot.send_message(OWNER_ID, "❌ Please enter digits only.")


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
    
