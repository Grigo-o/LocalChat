import socket
import threading
import time
import uuid

from protocol import encode_message, decode_message, MessageReader
from utils import generate_uuid, deadline_timestamp, current_time
from config import UDP_BROADCAST_PORT, BUFFER_SIZE, ENCODING

waiting_for_ack = False
my_turn = True

active_requests = {}


def receive_messages(reader, conn):
    global waiting_for_ack
    global my_turn

    while True:
        try:
            message = reader.read()

            try:
                parts = decode_message(message)

            except Exception:
                print("\nMalformed message received.")
                continue

            msg_type = parts[0]

            if msg_type == "MSG":

                if len(parts) < 3:

                    error_msg = encode_message(
                        "ERROR",
                        "BAD_FORMAT",
                        "Invalid MSG format"
                    )

                    conn.send(error_msg.encode(ENCODING))
                    continue

                msg_id = parts[1]
                text = parts[2]

                print(f"\n[Recipient]: {text}")

                ack = encode_message("MSG_ACK", msg_id)

                conn.send(ack.encode(ENCODING))

                my_turn = True

            elif msg_type == "MSG_ACK":

                waiting_for_ack = False
                print("\n[Message acknowledged]")

            elif msg_type == "ERROR":

                print(f"\n[ERROR]: {' | '.join(parts[1:])}")

            elif msg_type == "CLOSE":

                print("\nRecipient closed the connection.")
                conn.close()
                break

            else:

                error_msg = encode_message(
                    "ERROR",
                    "UNKNOWN_MESSAGE_TYPE",
                    "Unsupported message type"
                )

                conn.send(error_msg.encode(ENCODING))

        except Exception as e:
            print("\nConnection lost:", e)
            break


def main():
    global waiting_for_ack
    global my_turn

    recipient_nickname = input("Enter recipient nickname: ").strip()

    if not recipient_nickname:
        print("Nickname cannot be empty.")
        return

    try:
        tcp_port = int(input("Enter TCP port to listen on: "))

        if tcp_port < 1024 or tcp_port > 65535:
            raise ValueError

    except ValueError:
        print("Invalid TCP port.")
        return

    try:
        deadline_seconds = int(input("Enter deadline in seconds: "))

        if deadline_seconds <= 0:
            raise ValueError

    except ValueError:
        print("Invalid deadline.")
        return

    request_uuid = generate_uuid()

    expiry_time = deadline_timestamp(deadline_seconds)

    active_requests[request_uuid] = expiry_time

    discovery_message = encode_message(
        "DISCOVER",
        recipient_nickname,
        expiry_time,
        tcp_port,
        request_uuid
    )

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:

        udp_socket.sendto(
            discovery_message.encode(ENCODING),
            ("255.255.255.255", UDP_BROADCAST_PORT)
        )

    except Exception as e:
        print("Broadcast failed:", e)
        return

    print("\nBroadcast discovery message sent.")

    udp_socket.settimeout(2)

    try:

        while True:

            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

            response = data.decode(ENCODING)

            try:
                parts = decode_message(response)

            except Exception:
                continue

            if parts[0] == "ERROR":

                if len(parts) >= 3:

                    print(
                        f"\n[Discovery Error from {addr[0]}]: "
                        f"{parts[1]} - {parts[2]}"
                    )

    except socket.timeout:
        pass

    print("Waiting for TCP connection...\n")

    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        tcp_server.bind(("", tcp_port))

    except Exception as e:
        print("Failed to bind TCP server:", e)
        return

    tcp_server.listen(1)

    tcp_server.settimeout(deadline_seconds)

    try:

        conn, addr = tcp_server.accept()

    except socket.timeout:
        print("No recipient responded before deadline.")

        tcp_server.close()
        return

    print(f"TCP connection established with {addr}")

    reader = MessageReader(conn, buffer_size=BUFFER_SIZE, encoding=ENCODING)

    try:

        handshake_data = reader.read()

        handshake_parts = decode_message(handshake_data)

    except Exception:
        print("Malformed handshake received.")
        conn.close()
        return

    if len(handshake_parts) < 2:

        conn.send(
            encode_message(
                "HS_ACK",
                "REJECT",
                "INVALID_HANDSHAKE"
            ).encode(ENCODING)
        )

        conn.close()
        return

    if handshake_parts[0] != "HANDSHAKE":

        conn.send(
            encode_message(
                "HS_ACK",
                "REJECT",
                "INVALID_HANDSHAKE"
            ).encode(ENCODING)
        )

        conn.close()
        return

    received_uuid = handshake_parts[1]

    if received_uuid not in active_requests:

        conn.send(
            encode_message(
                "HS_ACK",
                "REJECT",
                "INVALID_UUID"
            ).encode(ENCODING)
        )

        conn.close()
        return

    if current_time() > active_requests[received_uuid]:

        conn.send(
            encode_message(
                "HS_ACK",
                "REJECT",
                "DEADLINE_EXPIRED"
            ).encode(ENCODING)
        )

        del active_requests[received_uuid]

        conn.close()
        return

    conn.send(
        encode_message(
            "HS_ACK",
            "ACCEPT"
        ).encode(ENCODING)
    )

    print("Handshake successful.")
    print("Chat started.\n")

    receiver_thread = threading.Thread(
        target=receive_messages,
        args=(reader, conn),
        daemon=True
    )

    receiver_thread.start()

    while True:

        if waiting_for_ack:
            time.sleep(0.1)
            continue

        if not my_turn:
            time.sleep(0.1)
            continue

        message = input("You: ").strip()

        if not message:
            print("Empty messages are not allowed.")
            continue

        if message.lower() == "exit":

            close_msg = encode_message("CLOSE")

            conn.send(close_msg.encode(ENCODING))

            conn.close()
            break

        msg_id = str(uuid.uuid4())[:8]

        msg = encode_message(
            "MSG",
            msg_id,
            message
        )

        try:

            conn.send(msg.encode(ENCODING))

        except Exception as e:
            print("Failed to send message:", e)
            break

        waiting_for_ack = True
        my_turn = False

    try:
        conn.close()
        tcp_server.close()
        udp_socket.close()

    except Exception:
        pass


if __name__ == "__main__":
    main()