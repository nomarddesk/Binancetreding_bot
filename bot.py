import os
import logging
import json
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY = os.getenv('API_KEY', '')  # Your exchange API key
API_SECRET = os.getenv('API_SECRET', '')  # Your exchange API secret

# Mock API connection state
class APIManager:
    def __init__(self):
        self.connected = False
        self.api_key = ""
        self.api_secret = ""
        self.wallet_addresses = {}
        self.balances = {}
    
    def connect(self, api_key: str, api_secret: str) -> bool:
        """Mock API connection function"""
        if api_key and api_secret:
            self.api_key = api_key
            self.api_secret = api_secret
            self.connected = True
            # Mock balances
            self.balances = {
                'BTC': 0.5,
                'ETH': 3.2
            }
            return True
        return False
    
    def get_balances(self):
        """Get user balances"""
        return self.balances if self.connected else {}
    
    def withdraw(self, asset: str, amount: float, address: str) -> Dict:
        """Mock withdrawal function"""
        if not self.connected:
            return {"success": False, "message": "API not connected"}
        
        if asset not in ['BTC', 'ETH']:
            return {"success": False, "message": "Only BTC and ETH supported"}
        
        if asset in self.balances and self.balances[asset] >= amount:
            # Save withdrawal address
            self.wallet_addresses[asset] = address
            
            # Mock successful withdrawal
            self.balances[asset] -= amount
            
            return {
                "success": True,
                "message": f"Withdrawal successful!\n{amount} {asset} sent to {address[:10]}...",
                "txid": f"mock_tx_id_{asset}_{amount}"
            }
        else:
            return {"success": False, "message": "Insufficient balance"}

# Initialize API manager
api_manager = APIManager()

# Main menu keyboard
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔌 Connect API", callback_data='connect_api')],
        [InlineKeyboardButton("💰 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("📊 Check Balance", callback_data='balance')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🤖 *Welcome to Crypto Bot* 🤖

*Features:*
• Connect to your exchange API
• Withdraw BTC/ETH to any address
• Check your balances

*Available Commands:*
/start - Show this menu
/connect - Connect API
/withdraw - Start withdrawal
/balance - Check balances

⚠️ *Security Note:* This is a demonstration bot. Never share your real API keys.
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# Connect API handler
async def connect_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if api_manager.connected:
        await query.edit_message_text(
            text="✅ API is already connected!\n\nYour balances:\n" + 
                 "\n".join([f"• {asset}: {amount}" for asset, amount in api_manager.get_balances().items()]),
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Ask for API key
    context.user_data['awaiting_api_key'] = True
    await query.edit_message_text(
        text="🔑 *Step 1/2: Enter your API Key*\n\n"
             "Please send your API key in the next message.\n"
             "⚠️ For demo purposes, you can use 'demo_key'",
        parse_mode='Markdown'
    )

# Withdraw handler
async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not api_manager.connected:
        await query.edit_message_text(
            text="❌ Please connect API first!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("BTC", callback_data='withdraw_btc')],
        [InlineKeyboardButton("ETH", callback_data='withdraw_eth')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]
    
    balances = api_manager.get_balances()
    balance_text = "\n".join([f"• {asset}: {amount}" for asset, amount in balances.items()])
    
    await query.edit_message_text(
        text=f"💰 *Withdrawal Menu*\n\n"
             f"*Your Balances:*\n{balance_text}\n\n"
             f"Select cryptocurrency to withdraw:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle withdrawal selection
async def withdraw_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    asset = query.data.split('_')[1].upper()  # 'btc' or 'eth'
    
    # Store selected asset in context
    context.user_data['withdraw_asset'] = asset
    
    await query.edit_message_text(
        text=f"💸 *Withdraw {asset}*\n\n"
             f"Please send the amount of {asset} you want to withdraw.\n"
             f"Available: {api_manager.balances.get(asset, 0)} {asset}",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_amount'] = True

# Balance check
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if api_manager.connected:
        balances = api_manager.get_balances()
        if balances:
            balance_text = "\n".join([f"• {asset}: {amount}" for asset, amount in balances.items()])
            message = f"📊 *Your Balances*\n\n{balance_text}"
        else:
            message = "No balances found."
    else:
        message = "❌ API not connected. Please connect first."
    
    await query.edit_message_text(
        text=message,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# Back to main menu
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Main Menu",
        reply_markup=main_menu_keyboard()
    )

# Handle messages (for API key input, amount input, address input)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    if context.user_data.get('awaiting_api_key'):
        # Store API key and ask for secret
        context.user_data['api_key'] = user_input
        context.user_data['awaiting_api_key'] = False
        context.user_data['awaiting_api_secret'] = True
        
        await update.message.reply_text(
            "🔐 *Step 2/2: Enter your API Secret*\n\n"
            "Please send your API secret.\n"
            "⚠️ For demo purposes, you can use 'demo_secret'",
            parse_mode='Markdown'
        )
    
    elif context.user_data.get('awaiting_api_secret'):
        # Complete API connection
        api_key = context.user_data.get('api_key', '')
        api_secret = user_input
        
        # Connect API
        success = api_manager.connect(api_key, api_secret)
        
        if success:
            context.user_data.clear()
            balances = api_manager.get_balances()
            balance_text = "\n".join([f"• {asset}: {amount}" for asset, amount in balances.items()])
            
            await update.message.reply_text(
                f"✅ *API Connected Successfully!*\n\n"
                f"*Your Balances:*\n{balance_text}\n\n"
                f"You can now use withdrawal features.",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Connection failed. Please try again with /connect",
                reply_markup=main_menu_keyboard()
            )
    
    elif context.user_data.get('awaiting_amount'):
        # Process withdrawal amount
        try:
            amount = float(user_input)
            asset = context.user_data.get('withdraw_asset')
            
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive!")
                return
            
            available = api_manager.balances.get(asset, 0)
            if amount > available:
                await update.message.reply_text(
                    f"❌ Insufficient balance!\n"
                    f"Available: {available} {asset}\n"
                    f"Requested: {amount} {asset}"
                )
                return
            
            # Store amount and ask for address
            context.user_data['withdraw_amount'] = amount
            context.user_data['awaiting_amount'] = False
            context.user_data['awaiting_address'] = True
            
            await update.message.reply_text(
                f"📍 *Step 2/2: Enter {asset} Address*\n\n"
                f"Please send the destination wallet address for {amount} {asset}",
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number!")
    
    elif context.user_data.get('awaiting_address'):
        # Process withdrawal address
        address = user_input.strip()
        asset = context.user_data.get('withdraw_asset')
        amount = context.user_data.get('withdraw_amount')
        
        # Validate address format (basic check)
        if len(address) < 26:
            await update.message.reply_text("❌ Invalid address format!")
            return
        
        # Execute withdrawal
        result = api_manager.withdraw(asset, amount, address)
        
        if result["success"]:
            await update.message.reply_text(
                f"✅ *Withdrawal Successful!*\n\n"
                f"*Details:*\n"
                f"• Amount: {amount} {asset}\n"
                f"• To: {address[:15]}...\n"
                f"• TXID: {result['txid']}\n\n"
                f"*Remaining Balance:*\n"
                f"• {asset}: {api_manager.balances.get(asset, 0)}",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Withdrawal failed!\n\n"
                f"Error: {result['message']}",
                reply_markup=main_menu_keyboard()
            )
        
        # Clear context
        context.user_data.clear()

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again.",
            reply_markup=main_menu_keyboard()
        )

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect_api))
    application.add_handler(CommandHandler("withdraw", withdraw_menu))
    application.add_handler(CommandHandler("balance", check_balance))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(connect_api, pattern='^connect_api$'))
    application.add_handler(CallbackQueryHandler(withdraw_menu, pattern='^withdraw$'))
    application.add_handler(CallbackQueryHandler(withdraw_selection, pattern='^withdraw_'))
    application.add_handler(CallbackQueryHandler(check_balance, pattern='^balance$'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back$'))
    
    # Add message handler
    application.add_handler(telegram.ext.MessageHandler(
        telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND,
        handle_message
    ))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
