import socket
import threading
import time
import uuid

from protocol import encode_message, decode_message, MessageReader
from config import UDP_BROADCAST_PORT, BUFFER_SIZE, ENCODING

waiting_for_ack = False
my_turn = False


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

                print(f"\n[Initiator]: {text}")

                ack = encode_message("MSG_ACK", msg_id)

                conn.send(ack.encode(ENCODING))

                my_turn = True

            elif msg_type == "MSG_ACK":

                waiting_for_ack = False
                print("\n[Message acknowledged]")

            elif msg_type == "ERROR":

                print(f"\n[ERROR]: {' | '.join(parts[1:])}")

            elif msg_type == "CLOSE":

                print("\nInitiator closed the connection.")
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

    my_nickname = input("Enter your nickname: ").strip()

    if not my_nickname:
        print("Nickname cannot be empty.")
        return

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        udp_socket.bind(("", UDP_BROADCAST_PORT))

    except Exception as e:
        print("Failed to bind UDP socket:", e)
        return

    print("\nListening for discovery broadcasts...\n")

    while True:

        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)

        except Exception as e:
            print("UDP receive error:", e)
            continue

        message = data.decode(ENCODING)

        try:
            parts = decode_message(message)

        except Exception:
            print("Malformed discovery message.")
            continue

        if parts[0] != "DISCOVER":
            continue

        if len(parts) != 5:

            error_msg = encode_message(
                "ERROR",
                "BAD_DISCOVER_FORMAT",
                "Invalid discovery message"
            )

            udp_socket.sendto(error_msg.encode(ENCODING), addr)

            continue

        target_nickname = parts[1]

        try:
            expiry_time = int(parts[2])
            tcp_port = int(parts[3])

        except ValueError:
            continue

        request_uuid = parts[4]

        if target_nickname != my_nickname:

            error_msg = encode_message(
                "ERROR",
                "UNKNOWN_RECIPIENT",
                "Nickname does not match"
            )

            udp_socket.sendto(error_msg.encode(ENCODING), addr)

            continue

        print(f"Discovery request received from {addr[0]}")

        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:

            tcp_client.connect((addr[0], tcp_port))

        except Exception as e:
            print("Failed to connect:", e)
            continue

        handshake_message = encode_message(
            "HANDSHAKE",
            request_uuid
        )

        try:

            tcp_client.send(handshake_message.encode(ENCODING))

        except Exception as e:
            print("Failed to send handshake:", e)

            tcp_client.close()
            continue

        reader = MessageReader(tcp_client, buffer_size=BUFFER_SIZE, encoding=ENCODING)

        try:

            response = reader.read()

            response_parts = decode_message(response)

        except Exception:
            print("Invalid handshake response.")

            tcp_client.close()
            continue

        if response_parts[0] != "HS_ACK":

            print("Invalid handshake response.")

            tcp_client.close()
            continue

        if response_parts[1] != "ACCEPT":

            reason = "UNKNOWN"

            if len(response_parts) > 2:
                reason = response_parts[2]

            print(f"Handshake rejected: {reason}")

            tcp_client.close()
            continue

        print("Handshake accepted.")
        print("Chat started.\n")

        receiver_thread = threading.Thread(
            target=receive_messages,
            args=(reader, tcp_client),
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

                tcp_client.send(close_msg.encode(ENCODING))

                tcp_client.close()
                return

            msg_id = str(uuid.uuid4())[:8]

            msg = encode_message(
                "MSG",
                msg_id,
                message
            )

            try:

                tcp_client.send(msg.encode(ENCODING))

            except Exception as e:
                print("Failed to send message:", e)
                break

            waiting_for_ack = True
            my_turn = False

        try:
            tcp_client.close()

        except Exception:
            pass


if __name__ == "__main__":
    main()