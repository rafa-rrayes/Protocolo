# Protocolo

A Python library for serial communication with packet encoding/decoding, CRC validation, and file transfer capabilities.

## Features

- **Packet Encoding/Decoding**: Encode and decode data packets with headers, payloads, and CRC checksums
- **CRC-16 Validation**: Built-in CRC-16 checksum calculation and verification
- **Multiple Data Types**: Support for strings, integers, bytes, and Python objects (via pickle)
- **File Transfer**: Send and receive files over serial communication
- **Object Transfer**: Send and receive Python objects
- **Logging**: Built-in logging for debugging communication

## Installation

```bash
pip install protocolo
```

Or install from source:

```bash
git clone https://github.com/rafa-rrayes/Protocolo.git
cd Protocolo
pip install .
```

## Quick Start

### Basic Communication

```python
from protocolo import Enlace

# Initialize connection
com = Enlace('/dev/ttyUSB0')
com.open()

# Send a file
com.send_file('image.jpeg', 'file')

# Close connection
com.close()
```

### Server Side

```python
from protocolo import Enlace
import time

# Initialize connection
com = Enlace('/dev/ttyUSB1')
com.open()

# Wait for incoming data
time.sleep(5)
com.accept('file')

com.close()
```

### Using the Codec

```python
from protocolo import Codec

codec = Codec()

# Create a packet
packet = codec.empacotar(tipo=4, info="test", payload=b"Hello, World!")

# Decode a packet
decoded = codec.desempacotar(packet)
print(decoded['payload'])  # b"Hello, World!"
```

## Packet Types

| Type | Description |
|------|-------------|
| 0 | Request |
| 1 | Accept |
| 2 | Object |
| 3 | Start of data |
| 4 | Data |
| 5 | Data confirmation |
| 6 | End of data |
| 7 | Error message |

## API Reference

### Codec Class

- `empacotar(tipo, info, payload)`: Create a packet
- `desempacotar(pacote)`: Decode a packet
- `crc16(data)`: Calculate CRC-16 checksum

### Enlace Class

- `open()`: Open serial connection
- `close()`: Close serial connection
- `send_file(file_path, request_name, save_name, data)`: Send a file
- `send_object(data, request_name)`: Send a Python object
- `accept(accept_name)`: Accept an incoming request
- `receive_packet(timeout)`: Receive a single packet

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

