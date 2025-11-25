# Protocolo

This is a **layered communication protocol** (similar to the OSI model) implemented for a university project (4th semester Computer Engineering at Insper). It provides reliable file and object transfer over serial ports using:

### Key Components

1. **`Codec` class** - Handles packet encoding/decoding with:
   - Start/end delimiters: `#StR#` and `#eNd#`
   - CRC-16 error detection
   - Header with metadata (type, packet ID, payload size, info field)
   - Support for multiple data types (int, bytes, string, Python objects via pickle)
   - Maximum payload size of 255 bytes

2. **`Enlace` class** - Link layer that manages:
   - Serial port communication (115200 baud rate)
   - Request/accept handshake mechanism
   - File transfer with automatic chunking
   - Object serialization and transmission
   - Automatic retransmission on errors
   - Asynchronous packet reading via threading
   - Logging of all transmissions

### Protocol Message Types

- **Type 0**: Request to send (object/file)
- **Type 1**: Accept request
- **Type 2**: Object data
- **Type 3**: Start of file data
- **Type 4**: File data chunk
- **Type 5**: Data confirmation/ACK
- **Type 6**: End of file data
- **Type 7**: Error message

### Features

- **Request-response pattern**: Sender requests permission, receiver accepts
- **Reliable delivery**: CRC checks, ACKs, automatic retransmission
- **File chunking**: Large files split into 255-byte packets
- **Flow control**: Sequential packet numbering with confirmations
- **Error handling**: CRC validation, timeout detection, packet reordering
- **Logging**: Comprehensive transmission logs with timestamps

This protocol implements a reliable data transfer mechanism suitable for educational purposes, demonstrating concepts like framing, error detection, flow control, and session management.