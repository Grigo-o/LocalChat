import uuid
import time


def generate_uuid():
    return str(uuid.uuid4())


def current_time():
    return int(time.time())


def deadline_timestamp(seconds):
    return current_time() + seconds