# Local Network Chat Protocol

A custom application-layer chat protocol for local network communication, built from scratch without any third-party dependencies.

## How it works

The protocol operates in four stages:

1. **Discovery** — the Initiator broadcasts a UDP message to the local network containing the target nickname, a deadline, a TCP port, and a UUID
2. **Connection** — if a Recipient recognizes its nickname, it opens a TCP connection back to the Initiator
3. **Handshake** — the Recipient sends the UUID for validation; the Initiator accepts or rejects based on UUID correctness and deadline expiry
4. **Chat** — messages are exchanged in turn-based (half-duplex) mode over TCP; each message must be acknowledged before the next can be sent

## Requirements

- Python 3.6 or higher
- No third-party packages — uses only the Python standard library (`socket`, `threading`, `uuid`, `time`)

To check your Python version:

```bash
python3 --version
```

## Running

Open two terminals on machines connected to the same local network (or two terminals on the same machine for local testing).

### Terminal 1 — start the Recipient first

```bash
python3 recipient.py
```

You will be prompted to enter your nickname. The Recipient listens for UDP broadcasts on port `37020`.

### Terminal 2 — start the Initiator

```bash
python3 initiator.py
```

You will be prompted for:

- **Recipient nickname** — must match exactly what the Recipient entered
- **TCP port** — any available port between 1024 and 65535 (e.g. `5001`)
- **Deadline** — seconds to wait for a response before timing out (e.g. `30`)

Once the handshake succeeds, both sides can type messages. The Initiator sends first. Type `exit` on either side to close the connection.

## Protocol message reference

| Message | Format | Direction |
|---|---|---|
| Discovery | `DISCOVER\|nickname\|deadline\|port\|uuid` | Initiator → broadcast |
| Handshake | `HANDSHAKE\|uuid` | Recipient → Initiator |
| Handshake response | `HS_ACK\|ACCEPT` or `HS_ACK\|REJECT\|reason` | Initiator → Recipient |
| Text message | `MSG\|msg_id\|text` | Either direction |
| Acknowledgment | `MSG_ACK\|msg_id` | Either direction |
| Error | `ERROR\|error_code\|description` | Either direction |
| Close | `CLOSE` | Either direction |

All messages are UTF-8 encoded, newline-terminated, and use `|` as the field delimiter. Pipe characters in message text are automatically escaped.

## File structure

```
.
├── initiator.py   — Initiator application
├── recipient.py   — Recipient application
├── protocol.py    — Message encoding, decoding, and framing
├── config.py      — Shared constants (port, buffer size, encoding)
├── utils.py       — UUID generation and timestamp helpers
└── README.md
```

## Limitations

- No encryption or authentication
- Single active session at a time
- Local network only (UDP broadcast does not cross routers)
- Console interface only; no message history is saved