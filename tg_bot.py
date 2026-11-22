import os
from pathlib import Path
import telebot

from exporter import save_html
from scanner import run_investigation

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable set nahi hai.")

bot = telebot.TeleBot(BOT_TOKEN)
REPORTS_DIR = Path("tg_reports")
REPORTS_DIR.mkdir(exist_ok=True)


@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    bot.reply_to(
        message,
        "MailAccess TG Bot ready hai!\n\n"
        "Use:\n"
        "`/investigate user@example.com`\n\n"
        "Sirf apni email ya authorized kaam ke liye use karein.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["investigate"])
def handle_investigate(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "Sahi format use karein: `/investigate email@example.com`", parse_mode="Markdown")
        return

    target_email = parts[1].strip()
    status_msg = bot.reply_to(message, f"Scanning `{target_email}`...", parse_mode="Markdown")

    try:
        report = run_investigation(target_email, Path("platforms.json"))
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in target_email)
        html_path = REPORTS_DIR / f"{safe_name}.html"
        save_html(report, html_path)

        summary = report.get("summary", {})
        reply_text = (
            f"*Target:* `{report['target_email']}`\n"
            f"*Username Pivot:* `{report['username_pivot']}`\n"
            f"*Domain Type:* `{report['domain_type']}`\n"
            f"*Exposure Score:* *{report['exposure_score']}/100*\n"
            f"*Confirmed:* {summary.get('confirmed', 0)} | "
            f"*Username Matches:* {summary.get('username_matches', 0)} | "
            f"*Possible:* {summary.get('possible', 0)}"
        )

        bot.edit_message_text(
            reply_text,
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown",
        )

        with html_path.open("rb") as doc:
            bot.send_document(message.chat.id, doc, caption=f"HTML Report — {target_email}")

    except ValueError as e:
        bot.edit_message_text(f"Invalid input: {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"Scan error: {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)


if __name__ == "__main__":
    print("TG bot running...")
    bot.infinity_polling(skip_pending=True)
