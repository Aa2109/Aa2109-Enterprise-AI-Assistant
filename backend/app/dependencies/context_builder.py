from fastapi import Depends
from app.services.conversation_context_builder import ConversationContextBuilder


def get_context_builder():
    return ConversationContextBuilder()