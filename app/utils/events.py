import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("book_gen_events")

def log_event(event_type: str, book_id: str, message: str):
    """
    Simple event logger for Stage 1 milestones.
    Can be extended later to include webhooks, emails, or persistent DB logs.
    """
    log_msg = f"[EVENT: {event_type}] Book ID: {book_id} | {message}"
    logger.info(log_msg)
    # Could also write to a dedicated events table in Supabase if needed
