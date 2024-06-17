# states.py
from telebot.handler_back have been_with_db import State, StatesGroup

class AdminState(StatesGroup):
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()
