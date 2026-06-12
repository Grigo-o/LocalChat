MESSAGE_DELIMITER = "|"
ESCAPE_CHAR = "\\"
MESSAGE_TERMINATOR = "\n"

# Type-aware split limit: MSG has a free-text last field that may contain
# the delimiter, so we cap splits at 2 (type | msg_id | text).
_MAX_SPLITS = {
    "MSG": 2,
}


def _escape(value):
    return str(value).replace(ESCAPE_CHAR, ESCAPE_CHAR + ESCAPE_CHAR) \
                     .replace(MESSAGE_DELIMITER, ESCAPE_CHAR + MESSAGE_DELIMITER)


def _unescape(value):
    result = []
    i = 0
    while i < len(value):
        if value[i] == ESCAPE_CHAR and i + 1 < len(value):
            result.append(value[i + 1])
            i += 2
        else:
            result.append(value[i])
            i += 1
    return "".join(result)


def encode_message(msg_type, *fields):
    if not fields:
        return msg_type + MESSAGE_TERMINATOR

    token_fields = [str(f) for f in fields[:-1]]
    last_field = _escape(str(fields[-1]))

    parts = [msg_type] + token_fields + [last_field]
    return MESSAGE_DELIMITER.join(parts) + MESSAGE_TERMINATOR


def decode_message(raw):
    message = raw.strip()

    if not message:
        raise ValueError("Empty message")

    first_delim = message.find(MESSAGE_DELIMITER)
    if first_delim == -1:
        return [message]

    msg_type = message[:first_delim]
    maxsplit = _MAX_SPLITS.get(msg_type, len(message))

    parts = message.split(MESSAGE_DELIMITER, maxsplit)

    if not parts:
        raise ValueError("Malformed message")

    parts[-1] = _unescape(parts[-1])

    return parts


class MessageReader:
    def __init__(self, sock, buffer_size=1024, encoding="utf-8"):
        self._sock = sock
        self._buf = b""
        self._buffer_size = buffer_size
        self._encoding = encoding
        self._term = MESSAGE_TERMINATOR.encode(encoding)

    def read(self):
        while self._term not in self._buf:
            chunk = self._sock.recv(self._buffer_size)
            if not chunk:
                raise ConnectionError("Connection closed")
            self._buf += chunk

        line, self._buf = self._buf.split(self._term, 1)
        return line.decode(self._encoding)


VALID_MESSAGE_TYPES = {
    "DISCOVER",
    "HANDSHAKE",
    "HS_ACK",
    "MSG",
    "MSG_ACK",
    "CLOSE",
    "ERROR"
}