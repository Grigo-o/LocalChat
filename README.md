# Local Network Chat Protocol

## Description

This project implements a custom application-layer chat protocol using:

- UDP broadcast discovery
- TCP communication
- UUID-based handshaking
- Simplex message exchange

## Features

- Discovery via UDP broadcast
- TCP connection establishment
- UUID validation
- Deadline checking
- Message exchange
- Graceful connection termination

## Protocol Messages

### Discovery
DISCOVER|nickname|deadline|port|uuid

### Handshake
HANDSHAKE|uuid

### Handshake Response
HS_ACK|ACCEPT

or

HS_ACK|REJECT

### Text Message
MSG|text

### Close Connection
CLOSE

## Running the Program

Open two terminals.

### Start Recipient

```bash
python recipient.py