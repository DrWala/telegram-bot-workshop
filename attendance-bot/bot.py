import json
import logging

from telegram import (
    ReplyKeyboardMarkup,
    Update
)
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

token = "[YOUR TOKEN HERE]"

# ConversationHandler stuff
CLASS = range(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Class defining an attendance session
class AttendanceSession:
    def __init__(self, chat_id: int, message_id: int, message: str) -> None:
        self.chat_id = chat_id
        self.message_id = message_id
        self.message = message

    def to_json(self) -> dict:
        json_data = {
            'chat_id': self.chat_id,
            'message_id': self.message_id,
            'message': self.message
        }
        return json.dumps(json_data)


# Store JSONs as separate maps in memory. These variables should
# eventually be persisted to a database of some sort, but for now
# we store it all in the program's runtime memory.
CLASS_TO_STUDENTS = {
    "XII-A": {
        "Azeem Vasanwala": "azeemvasanwala"
    }
}
STUDENTS_TO_CLASS = {}
CLASS_TO_SESSION = {}
USERNAME_TO_IDS = {}


########################################
########### COMMON COMMANDS ############
########################################


def start(update: Update, _: CallbackContext) -> None:
    global USERNAME_TO_IDS
    USERNAME_TO_IDS[update.message.from_user.username] = update.message.from_user.id
    update.message.reply_text(
        'Welcome! Your username has been stored in our very secure servers.')


########################################
####### COMMANDS FOR THE TEACHER #######
########################################


def start_attendance_session(update: Update, _: CallbackContext) -> None:
    # Keyboard for choosing class
    keyboard = [
        [class_str for class_str in CLASS_TO_STUDENTS.keys()]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Choose class:', reply_markup=reply_markup)

    return CLASS


def class_handler(update: Update, context: CallbackContext) -> None:
    # Create attendance session
    chat_id = update.message.from_user.id
    message_text = f'Attendance session for {update.message.text}:'
    message = update.message.reply_text(message_text)
    session = AttendanceSession(
        chat_id=chat_id, message_id=message.message_id, message=message_text)

    # Save session in dictionary
    CLASS_TO_SESSION[update.message.text] = session.to_json()

    # Send message to students in class
    class_list = CLASS_TO_STUDENTS[update.message.text].values()
    update.message.reply_text('Sending attendance messages...')
    send_attendance_messages(context, class_list)

    return ConversationHandler.END


# Command to cancel ConversationHandler


def cancel(update: Update, _: CallbackContext) -> None:
    update.message.reply_text('Attendance session creation has been canceled.')


# Send messages to all users in usernames


def send_attendance_messages(context: CallbackContext, usernames: list[str]) -> None:
    for username in usernames:
        chat_id = USERNAME_TO_IDS[username]
        context.bot.send_message(
            chat_id=chat_id,
            text='Mark attendance!'
        )


########################################
####### COMMANDS FOR THE STUDENT #######
########################################


def mark_attendance(update: Update, context: CallbackContext) -> None:
    # Get attendance session
    classname = STUDENTS_TO_CLASS[update.message.from_user.username]
    session = json.loads(CLASS_TO_SESSION[classname])

    context.bot.edit_message_text(
        text=update_attendance_message(
            session, f'{update.message.from_user.first_name} {update.message.from_user.last_name}'),
        chat_id=session['chat_id'],
        message_id=session['message_id']
    )
    update.message.reply_text("Attendance marked!")


def update_attendance_message(session: dict, username: str) -> str:
    session['message'] += '\n' + username
    return session['message']


########################################
############# BOT SETUP ################
########################################


def init_data() -> None:
    for classname, students in CLASS_TO_STUDENTS.items():
        for _, student_id in students.items():
            STUDENTS_TO_CLASS[student_id] = classname


def main() -> None:
    # Init data
    init_data()

    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('mark_attendance', mark_attendance))

    # Add conversation handler with to start attendance session
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(
            'start_attendance', start_attendance_session)],
        states={
            CLASS: [MessageHandler(Filters.text, class_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
