"""
vpn_protocol.py - Packet framing, message definitions, and binary serialization for Custom VPN.
Supports both Raw TCP sockets and WebSocket encapsulation (for Cloud / Codespaces HTTPS tunnels).
"""

import struct
import socket
import os
import hashlib
import base64
from typing import Tuple, Optional

# Message Type Constants
MSG_HEARTBEAT = 0x00
MSG_CLIENT_HELLO = 0x01
MSG_SERVER_HELLO = 0x02
MSG_HANDSHAKE_COMPLETE = 0x03

# Tunnel Data Plane Messages (Multiplexed stream-based)
MSG_TUNNEL_CONNECT = 0x10      # Client requests server to connect to target (host, port)
MSG_TUNNEL_CONNECTED = 0x11    # Server confirms connection established
MSG_TUNNEL_DATA = 0x12         # Encrypted stream payload
MSG_TUNNEL_CLOSE = 0x13        # Stream closed
MSG_TUNNEL_FAILED = 0x14       # Server failed to connect to target

# Key Exchange Modes
MODE_DH_16 = 0x01
MODE_DH_2048 = 0x02
MODE_MLKEM_768 = 0x03

HEADER_FORMAT = "!IBI12s"
HEADER_LEN = struct.calcsize(HEADER_FORMAT)  # 4 + 1 + 4 + 12 = 21 bytes


class VPNPacket:
    def __init__(self, msg_type: int, stream_id: int, nonce: bytes, payload: bytes):
        self.msg_type = msg_type
        self.stream_id = stream_id
        self.nonce = nonce if nonce else bytes(12)
        self.payload = payload

    def serialize(self) -> bytes:
        total_len = HEADER_LEN + len(self.payload)
        header = struct.pack(HEADER_FORMAT, total_len, self.msg_type, self.stream_id, self.nonce)
        return header + self.payload

    @classmethod
    def parse(cls, data: bytes) -> Optional["VPNPacket"]:
        if len(data) < HEADER_LEN:
            return None
        total_len, msg_type, stream_id, nonce = struct.unpack_from(HEADER_FORMAT, data, 0)
        payload = data[HEADER_LEN:total_len]
        return cls(msg_type, stream_id, nonce, payload)


# ==============================================================================
# WEBSOCKET FRAMING HELPERS (RFC 6455)
# ==============================================================================

def ws_encode_frame(payload: bytes, is_client: bool = True) -> bytes:
    length = len(payload)
    b1 = 0x82  # Binary frame, FIN = 1
    if is_client:
        mask = os.urandom(4)
        if length < 126:
            header = bytes([b1, length | 0x80]) + mask
        elif length < 65536:
            header = bytes([b1, 126 | 0x80]) + struct.pack("!H", length) + mask
        else:
            header = bytes([b1, 127 | 0x80]) + struct.pack("!Q", length) + mask
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return header + masked_payload
    else:
        if length < 126:
            header = bytes([b1, length])
        elif length < 65536:
            header = bytes([b1, 126]) + struct.pack("!H", length)
        else:
            header = bytes([b1, 127]) + struct.pack("!Q", length)
        return header + payload


def ws_decode_frame(sock: socket.socket) -> Optional[bytes]:
    try:
        h = recv_exact(sock, 2)
        b1, b2 = h[0], h[1]
        opcode = b1 & 0x0F
        if opcode == 0x08:  # Connection close
            return None
        is_masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", recv_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", recv_exact(sock, 8))[0]
        mask = recv_exact(sock, 4) if is_masked else None
        data = recv_exact(sock, length)
        if is_masked:
            return bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        return data
    except Exception:
        return None


def send_packet(sock: socket.socket, packet: VPNPacket, is_ws: bool = False, is_client: bool = True) -> None:
    raw = packet.serialize()
    if is_ws:
        sock.sendall(ws_encode_frame(raw, is_client=is_client))
    else:
        sock.sendall(raw)


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise EOFError("Socket closed during read.")
        buf.extend(chunk)
    return bytes(buf)


def recv_packet(sock: socket.socket, is_ws: bool = False) -> Optional[VPNPacket]:
    try:
        if is_ws:
            frame_data = ws_decode_frame(sock)
            if not frame_data:
                return None
            return VPNPacket.parse(frame_data)
        else:
            len_bytes = recv_exact(sock, 4)
            total_len = struct.unpack("!I", len_bytes)[0]
            rest = recv_exact(sock, total_len - 4)
            full_data = len_bytes + rest
            return VPNPacket.parse(full_data)
    except Exception:
        return None
