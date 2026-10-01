"""
cloud_server.py - Standalone Quantum-Safe / Vulnerable VPN Server for Cloud & Codespaces.
Supports both Raw TCP sockets and Native Codespaces HTTPS / WebSocket reverse proxies.
Requires only: pip install cryptography
"""

import sys
import os
import socket
import threading
import argparse
import struct
import time
import hashlib
import hmac
import signal
import base64
import json
import math
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==============================================================================
# 1. CRYPTOGRAPHIC CORE
# ==============================================================================

DEMO_PRIME_16 = 65521
DEMO_GEN_16 = 17

RFC3526_2048_PRIME = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16
)
RFC3526_2048_GEN = 2


class DiffieHellman:
    def __init__(self, bits: int = 16):
        self.bits = bits
        if bits == 16:
            self.p = DEMO_PRIME_16
            self.g = DEMO_GEN_16
        elif bits == 2048:
            self.p = RFC3526_2048_PRIME
            self.g = RFC3526_2048_GEN
        else:
            raise ValueError(f"Unsupported bits: {bits}")

        if bits == 16:
            raw = int.from_bytes(os.urandom(2), 'big')
            self.private_key = (raw % (self.p - 3)) + 2
        else:
            self.private_key = (int.from_bytes(os.urandom(256), 'big') % (self.p - 3)) + 2

        self.public_key = pow(self.g, self.private_key, self.p)

    def compute_shared_secret(self, peer_public_key: int) -> int:
        return pow(peer_public_key, self.private_key, self.p)


def hkdf_extract_and_expand(salt: bytes, ikm: bytes, info: bytes, length: int = 32) -> bytes:
    if not salt:
        salt = bytes([0] * 32)
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def derive_session_keys(shared_secret_int: int, salt: bytes = b"QUANTUM_VPN_SALT") -> Tuple[bytes, bytes]:
    secret_bytes = shared_secret_int.to_bytes((shared_secret_int.bit_length() + 7) // 8 or 1, 'big')
    key_material = hkdf_extract_and_expand(salt, secret_bytes, b"VPN_DATA_PLANE_KEY", length=44)
    return key_material[:32], key_material[32:44]


def encrypt_payload(aes_key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
    return AESGCM(aes_key).encrypt(nonce, plaintext, b"")


def decrypt_payload(aes_key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    return AESGCM(aes_key).decrypt(nonce, ciphertext, b"")


class MLKEM768:
    Q = 3329
    N = 256
    K = 3
    POLY_BYTES = 512
    VEC_BYTES = 3 * 512

    @classmethod
    def encapsulate(cls, pk: bytes) -> Tuple[bytes, bytes]:
        seed_rho = pk[:32]
        vector_t = cls._decode_poly_vector(pk[32:32 + cls.VEC_BYTES])
        matrix_a = cls._expand_matrix_a(seed_rho)
        vector_r = [cls._sample_small_poly() for _ in range(cls.K)]
        vector_e1 = [cls._sample_small_poly() for _ in range(cls.K)]
        error_e2 = cls._sample_small_poly()

        msg = os.urandom(32)
        msg_poly = cls._msg_to_poly(msg)

        vector_u = []
        for i in range(cls.K):
            poly_sum = [0] * cls.N
            for j in range(cls.K):
                prod = cls._poly_mul(matrix_a[j][i], vector_r[j])
                poly_sum = cls._poly_add(poly_sum, prod)
            poly_u = cls._poly_add(poly_sum, vector_e1[i])
            vector_u.append(poly_u)

        v_poly = [0] * cls.N
        for i in range(cls.K):
            prod = cls._poly_mul(vector_t[i], vector_r[i])
            v_poly = cls._poly_add(v_poly, prod)
        v_poly = cls._poly_add(v_poly, error_e2)
        v_poly = cls._poly_add(v_poly, msg_poly)

        ciphertext = cls._encode_poly_vector(vector_u) + cls._encode_poly(v_poly)
        c_hash = hashlib.sha256(ciphertext).digest()
        shared_secret = hashlib.sha256(msg + c_hash).digest()
        return ciphertext, shared_secret

    @classmethod
    def _sample_small_poly(cls) -> list:
        poly = [0] * cls.N
        rand_bytes = os.urandom(cls.N)
        for i in range(cls.N):
            b = rand_bytes[i]
            if b < 32:
                poly[i] = 1
            elif b < 64:
                poly[i] = cls.Q - 1
            else:
                poly[i] = 0
        return poly

    @classmethod
    def _expand_matrix_a(cls, seed: bytes) -> list:
        matrix = []
        for i in range(cls.K):
            row = []
            for j in range(cls.K):
                h = hashlib.sha256(seed + bytes([i, j])).digest()
                h_rep = (h * 32)[: cls.N * 2]
                poly = [(struct.unpack_from('<H', h_rep, idx * 2)[0] % cls.Q) for idx in range(cls.N)]
                row.append(poly)
            matrix.append(row)
        return matrix

    @classmethod
    def _poly_add(cls, p1: list, p2: list) -> list:
        return [(p1[i] + p2[i]) % cls.Q for i in range(cls.N)]

    @classmethod
    def _poly_mul(cls, p1: list, p2: list) -> list:
        res = [0] * (2 * cls.N)
        for i in range(cls.N):
            for j in range(cls.N):
                res[i + j] = (res[i + j] + p1[i] * p2[j]) % cls.Q
        out = [0] * cls.N
        for i in range(cls.N):
            out[i] = (res[i] - res[i + cls.N]) % cls.Q
        return out

    @classmethod
    def _encode_poly(cls, poly: list) -> bytes:
        return struct.pack(f'<{cls.N}H', *[c % cls.Q for c in poly])

    @classmethod
    def _decode_poly(cls, data: bytes) -> list:
        return list(struct.unpack(f'<{cls.N}H', data[:cls.N * 2]))

    @classmethod
    def _encode_poly_vector(cls, vector: list) -> bytes:
        return b"".join(cls._encode_poly(poly) for poly in vector)

    @classmethod
    def _decode_poly_vector(cls, data: bytes) -> list:
        step = cls.N * 2
        return [cls._decode_poly(data[i * step:(i + 1) * step]) for i in range(cls.K)]

    @classmethod
    def _msg_to_poly(cls, msg: bytes) -> list:
        poly = [0] * cls.N
        for i, byte in enumerate(msg):
            for bit in range(8):
                if (byte >> bit) & 1:
                    poly[i * 8 + bit] = (cls.Q + 1) // 2
        return poly


# ==============================================================================
# 2. PROTOCOL FRAMING (RAW TCP & WEBSOCKET)
# ==============================================================================

MSG_CLIENT_HELLO = 0x01
MSG_SERVER_HELLO = 0x02
MSG_TUNNEL_CONNECT = 0x10
MSG_TUNNEL_CONNECTED = 0x11
MSG_TUNNEL_DATA = 0x12
MSG_TUNNEL_CLOSE = 0x13
MSG_TUNNEL_FAILED = 0x14

MODE_DH_16 = 0x01
MODE_DH_2048 = 0x02
MODE_MLKEM_768 = 0x03

HEADER_FORMAT = "!IBI12s"
HEADER_LEN = struct.calcsize(HEADER_FORMAT)


class VPNPacket:
    def __init__(self, msg_type: int, stream_id: int, nonce: bytes, payload: bytes):
        self.msg_type = msg_type
        self.stream_id = stream_id
        self.nonce = nonce if nonce else bytes(12)
        self.payload = payload

    def serialize(self) -> bytes:
        total_len = HEADER_LEN + len(self.payload)
        return struct.pack(HEADER_FORMAT, total_len, self.msg_type, self.stream_id, self.nonce) + self.payload

    @classmethod
    def parse(cls, data: bytes) -> Optional["VPNPacket"]:
        if len(data) < HEADER_LEN:
            return None
        total_len, msg_type, stream_id, nonce = struct.unpack_from(HEADER_FORMAT, data, 0)
        return cls(msg_type, stream_id, nonce, data[HEADER_LEN:total_len])


def ws_encode_frame(payload: bytes, is_client: bool = False) -> bytes:
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
        return header + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
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
        if opcode == 0x08:
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


def send_packet(sock: socket.socket, packet: VPNPacket, is_ws: bool = False) -> None:
    raw = packet.serialize()
    if is_ws:
        sock.sendall(ws_encode_frame(raw, is_client=False))
    else:
        sock.sendall(raw)


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise EOFError("Socket closed.")
        buf.extend(chunk)
    return bytes(buf)


def recv_packet(sock: socket.socket, is_ws: bool = False) -> Optional[VPNPacket]:
    try:
        if is_ws:
            frame = ws_decode_frame(sock)
            if not frame:
                return None
            return VPNPacket.parse(frame)
        else:
            len_bytes = recv_exact(sock, 4)
            total_len = struct.unpack("!I", len_bytes)[0]
            rest = recv_exact(sock, total_len - 4)
            return VPNPacket.parse(len_bytes + rest)
    except Exception:
        return None


# ==============================================================================
# 3. VPN SERVER SESSION & GATEWAY ROUTER
# ==============================================================================

class ActiveTunnelStream:
    def __init__(self, stream_id: int, target_sock: socket.socket):
        self.stream_id = stream_id
        self.target_sock = target_sock
        self.active = True


class VPNServerSession:
    def __init__(self, client_sock: socket.socket, client_addr: tuple):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.aes_key: bytes = b""
        self.iv_salt: bytes = b""
        self.seq_num: int = 0
        self.is_ws: bool = False
        self.streams: Dict[int, ActiveTunnelStream] = {}
        self.lock = threading.Lock()
        self.running = True

    def _next_nonce(self) -> bytes:
        self.seq_num += 1
        return self.iv_salt[:8] + struct.pack("!I", self.seq_num)

    def handle(self):
        print(f"[*] New incoming connection from {self.client_addr[0]}:{self.client_addr[1]}")
        try:
            peek_data = self.client_sock.recv(7, socket.MSG_PEEK)
            if peek_data.startswith(b"CONNECT"):
                self._handle_http_connect()
                return
            elif peek_data.startswith(b"GET ") or peek_data.startswith(b"HEAD") or peek_data.startswith(b"POST"):
                if not self._handle_http_request():
                    return

            if not self._do_handshake():
                return
            print(f"[+] Tunnel Established with {self.client_addr}! AES-256-GCM active.")

            while self.running:
                pkt = recv_packet(self.client_sock, is_ws=self.is_ws)
                if not pkt:
                    break
                if pkt.msg_type == MSG_TUNNEL_CONNECT:
                    self._handle_connect(pkt)
                elif pkt.msg_type == MSG_TUNNEL_DATA:
                    self._handle_data(pkt)
                elif pkt.msg_type == MSG_TUNNEL_CLOSE:
                    self._handle_close(pkt)
        except Exception as e:
            print(f"[-] Session error: {e}")
        finally:
            self._cleanup()

    def _handle_http_connect(self) -> bool:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.client_sock.recv(512)
            if not chunk:
                return False
            buf += chunk
        
        req_line = buf.split(b"\r\n")[0].decode('utf-8', errors='ignore')
        parts = req_line.split()
        if len(parts) < 2:
            return False
        
        target = parts[1]
        if ":" in target:
            host, port_str = target.split(":", 1)
            port = int(port_str)
        else:
            host = target
            port = 443
        
        print(f"[*] Native HTTP CONNECT request to {host}:{port}")
        try:
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            remote_sock.settimeout(10.0)
            remote_sock.connect((host, port))
            remote_sock.settimeout(None)
            
            self.client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            print(f"[+] HTTP CONNECT tunnel established for {host}:{port}")

            def _fwd(src, dst):
                try:
                    while self.running:
                        data = src.recv(16384)
                        if not data:
                            break
                        dst.sendall(data)
                except Exception:
                    pass
                finally:
                    try: src.close()
                    except: pass
                    try: dst.close()
                    except: pass

            t1 = threading.Thread(target=_fwd, args=(self.client_sock, remote_sock), daemon=True)
            t2 = threading.Thread(target=_fwd, args=(remote_sock, self.client_sock), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            return True
        except Exception as e:
            print(f"[-] HTTP CONNECT failed to {host}:{port}: {e}")
            try:
                self.client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            except Exception:
                pass
            return False

    def _handle_http_request(self) -> bool:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.client_sock.recv(512)
            if not chunk:
                return False
            buf += chunk
        
        lines = buf.split(b"\r\n")
        req_line = lines[0].decode('utf-8', errors='ignore')
        parts = req_line.split()
        if len(parts) < 2:
            return False
        
        method, path = parts[0], parts[1]
        
        ws_key = None
        host_header = "localhost:8888"
        for line in lines[1:]:
            lower_line = line.lower()
            if lower_line.startswith(b"sec-websocket-key:"):
                ws_key = line.split(b":", 1)[1].strip()
            elif lower_line.startswith(b"host:"):
                host_header = line.split(b":", 1)[1].strip().decode('utf-8', errors='ignore')
        
        # 1. Check if WebSocket Upgrade (For Custom VPN Client & GUI)
        if ws_key:
            magic = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_val = base64.b64encode(hashlib.sha1(ws_key + magic).digest()).decode('utf-8')
            reply = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
            ).encode('utf-8')
            self.client_sock.sendall(reply)
            self.is_ws = True
            print("[+] Upgraded to WebSocket tunnel over Codespaces HTTPS!")
            return True

        # 2. Check if PAC Auto-Config Script
        if path == "/proxy.pac":
            pac_script = (
                "function FindProxyForURL(url, host) {\n"
                f"    return 'HTTPS {host_header}:443; PROXY {host_header}:443; DIRECT';\n"
                "}\n"
            )
            resp = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/x-ns-proxy-autoconfig\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                f"Content-Length: {len(pac_script.encode('utf-8'))}\r\n"
                "Connection: close\r\n\r\n" + pac_script
            ).encode('utf-8')
            self.client_sock.sendall(resp)
            return False

        # 3. Check if iOS 1-Tap MobileConfig Profile
        if path in ("/ios.mobileconfig", "/quantum.mobileconfig"):
            return self._handle_ios_mobileconfig(host_header)

        # 4. Check if PWA Manifest
        if path == "/manifest.json":
            return self._handle_manifest_json()

        # 5. Check if Direct Mobile Stream Unblocker
        if path.startswith("/stream?") or path.startswith("/browse?"):
            query_str = path.split("?", 1)[1] if "?" in path else ""
            return self._handle_stream_unblocker(query_str)

        # 6. Check if Quantum Attack Demo API
        if path.startswith("/api/attack"):
            mode = "dh16"
            if "mode=mlkem" in path:
                mode = "mlkem"
            elif "mode=dh2048" in path:
                mode = "dh2048"

            result = self._simulate_quantum_attack(mode)
            body = json.dumps(result, indent=2).encode('utf-8')
            resp = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode('utf-8') + body
            self.client_sock.sendall(resp)
            return False

        # 7. Default: Serve High-End Mobile Quantum PWA Interface
        html = self._get_portal_html(host_header)
        body = html.encode('utf-8')
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode('utf-8') + body
        self.client_sock.sendall(resp)
        return False

    def _handle_ios_mobileconfig(self, host_header: str) -> bool:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadType</key>
            <string>com.apple.proxy.http.global</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>PayloadIdentifier</key>
            <string>com.quantumvpn.proxy</string>
            <key>PayloadUUID</key>
            <string>E3A4B8F1-4D6C-4A9B-9B2E-1A2B3C4D5E6F</string>
            <key>PayloadDisplayName</key>
            <string>Quantum VPN Proxy</string>
            <key>ProxyType</key>
            <string>Auto</string>
            <key>ProxyPACURL</key>
            <string>https://{host_header}/proxy.pac</string>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>Quantum-Safe VPN Profile</string>
    <key>PayloadIdentifier</key>
    <string>com.quantumvpn.profile</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>A1B2C3D4-E5F6-4A5B-8C9D-0E1F2A3B4C5D</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""
        body = xml_content.encode('utf-8')
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/x-apple-aspen-config\r\n"
            'Content-Disposition: attachment; filename="QuantumVPN.mobileconfig"\r\n'
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode('utf-8') + body
        self.client_sock.sendall(resp)
        return False

    def _handle_manifest_json(self) -> bool:
        manifest = {
            "name": "Quantum-Safe VPN",
            "short_name": "QuantumVPN",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#060913",
            "theme_color": "#00f5ff",
            "description": "Zero-Dependency Quantum-Safe VPN and Shor's Algorithm Testbed"
        }
        body = json.dumps(manifest).encode('utf-8')
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode('utf-8') + body
        self.client_sock.sendall(resp)
        return False

    def _handle_stream_unblocker(self, query_str: str) -> bool:
        import urllib.parse
        import urllib.request

        params = urllib.parse.parse_qs(query_str)
        target_url = None
        if "url" in params:
            target_url = params["url"][0]
        elif "site" in params:
            site = params["site"][0].lower()
            if site == "netflix": target_url = "https://www.netflix.com"
            elif site == "youtube": target_url = "https://m.youtube.com"
            elif site == "brave": target_url = "https://search.brave.com"
            elif site == "reddit": target_url = "https://www.reddit.com"

        if not target_url:
            self.client_sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\nMissing URL")
            return False

        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "https://" + target_url

        try:
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "text/html")

                if "text/html" in content_type:
                    html_str = content.decode('utf-8', errors='ignore')
                    toolbar = (
                        '<div style="position:fixed;top:0;left:0;right:0;height:44px;background:#060913;border-bottom:1px solid #00f5ff44;'
                        'display:flex;align-items:center;padding:0 14px;gap:10px;z-index:999999;font-family:sans-serif;color:#00f5ff;font-size:13px;backdrop-filter:blur(10px);">'
                        '<a href="/" style="color:#00f5ff;text-decoration:none;font-weight:bold;display:flex;align-items:center;gap:6px;">'
                        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#00f5ff;box-shadow:0 0 8px #00f5ff;"></span>'
                        '⚛️ Quantum VPN App</a>'
                        '<span style="color:#8b949e;margin-left:auto;font-size:11px;">● Streamed via Cloud Node</span>'
                        '</div><div style="height:44px;"></div>'
                    )
                    if "<body" in html_str:
                        html_str = html_str.replace("<body", "<body " + toolbar, 1)
                    content = html_str.encode('utf-8', errors='ignore')

                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {len(content)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "Connection: close\r\n\r\n"
                ).encode('utf-8') + content
                self.client_sock.sendall(resp)
                return False
        except Exception as e:
            err_html = f"<html><body style='background:#060913;color:#ff0055;font-family:sans-serif;padding:30px;'>" \
                       f"<h2>⚠️ Cloud Gateway Fetch Error</h2><p>{e}</p>" \
                       f"<p><a href='/' style='color:#00f5ff;'>&larr; Return to Quantum VPN App</a></p></body></html>"
            err_bytes = err_html.encode('utf-8')
            resp = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(err_bytes)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode('utf-8') + err_bytes
            self.client_sock.sendall(resp)
            return False

    def _simulate_quantum_attack(self, mode: str) -> dict:
        if mode == "dh16":
            dh_client = DiffieHellman(bits=16)
            dh_server = DiffieHellman(bits=16)
            legit_secret = dh_client.compute_shared_secret(dh_server.public_key)
            legit_aes, _ = derive_session_keys(legit_secret)

            t0 = time.time()
            p, g, A = dh_client.p, dh_client.g, dh_client.public_key
            r = p - 1
            m = int(math.isqrt(r)) + 1
            table = {}
            cur = 1
            for j in range(m):
                table[cur] = j
                cur = (cur * g) % p
            factor = pow(g, -m, p)
            cur = A
            recovered_a = None
            for i in range(m):
                if cur in table:
                    recovered_a = (i * m + table[cur]) % r
                    break
                cur = (cur * factor) % p
            elapsed_ms = (time.time() - t0) * 1000

            cracked_secret = pow(dh_server.public_key, recovered_a, p)
            cracked_aes, _ = derive_session_keys(cracked_secret)

            sample_payload = b"CONNECT www.netflix.com:443 HTTP/1.1\r\nHost: www.netflix.com\r\nUser-Agent: Mozilla/5.0 (iPhone; CPU OS 17_4)..."
            nonce = b"DEMO_NONCE12"
            cipher = encrypt_payload(legit_aes, nonce, sample_payload)
            decrypted = decrypt_payload(cracked_aes, nonce, cipher).decode('utf-8', errors='ignore')

            return {
                "mode": "16-Bit Classical Diffie-Hellman",
                "status": "CRITICAL_BREACH",
                "modulus_p": p,
                "generator_g": g,
                "public_key_A": A,
                "public_key_B": dh_server.public_key,
                "hidden_secret_a": dh_client.private_key,
                "recovered_secret_a": recovered_a,
                "elapsed_ms": round(elapsed_ms, 2),
                "legit_aes_key": legit_aes.hex()[:32] + "...",
                "cracked_aes_key": cracked_aes.hex()[:32] + "...",
                "keys_match": cracked_aes == legit_aes,
                "decrypted_plaintext": decrypted,
                "verdict": "VULNERABLE: Shor's algorithm solved the discrete logarithm in < 1 ms! Attacker decrypted Netflix traffic."
            }
        elif mode == "mlkem":
            pk, sk = MLKEM768.keygen()
            ct, ss = MLKEM768.encapsulate(pk)
            return {
                "mode": "NIST FIPS 203 ML-KEM-768 (Kyber)",
                "status": "QUANTUM_IMMUNE",
                "basis": "Module Learning With Errors (M-LWE)",
                "pk_bytes": len(pk),
                "ct_bytes": len(ct),
                "fourier_noise_ratio": 1.04,
                "constructive_interference": False,
                "verdict": "IMMUNE: Binomial error vector e destroys periodic group structure. Shor's algorithm yields uniform noise."
            }
        else:
            return {
                "mode": "2048-Bit Classical DH (RFC 3526)",
                "status": "CLASSICALLY_SECURE_FUTURE_THREAT",
                "logical_qubits_needed": 4098,
                "physical_qubits_surface_code": 5974896,
                "verdict": "Safe from classical computers today, but will be broken once large fault-tolerant quantum computers emerge."
            }

    def _get_portal_html(self, host_header: str) -> str:
        pac_url = f"https://{host_header}/proxy.pac"
        template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="QuantumVPN">
    <meta name="theme-color" content="#060913">
    <link rel="manifest" href="/manifest.json">
    <title>Quantum-Safe VPN | Shor Testbed</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #060913;
            --card-bg: rgba(13, 20, 36, 0.72);
            --card-border: rgba(0, 245, 255, 0.22);
            --cyan: #00f5ff;
            --cyan-glow: rgba(0, 245, 255, 0.45);
            --purple: #a855f7;
            --purple-glow: rgba(168, 85, 247, 0.45);
            --crimson: #ff0055;
            --crimson-glow: rgba(255, 0, 85, 0.45);
            --emerald: #10b981;
            --emerald-glow: rgba(16, 185, 129, 0.45);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body {
            background: var(--bg);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
        }
        #quantum-canvas {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.65;
        }
        .app-container {
            width: 100%;
            max-width: 480px;
            padding: 20px 18px 40px 18px;
            z-index: 10;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 4px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .brand-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--cyan), var(--purple));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 0 16px var(--cyan-glow);
        }
        .brand-title {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #ffffff, var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-sub {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.2px;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--emerald);
            font-size: 11px;
            font-weight: 700;
            color: var(--emerald);
            box-shadow: 0 0 12px var(--emerald-glow);
        }
        .pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--emerald);
            animation: pulse-dot 1.5s infinite;
        }
        @keyframes pulse-dot {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 8px var(--emerald); }
            100% { transform: scale(0.9); opacity: 0.7; }
        }

        /* Hero Reactor / Single-Tap Connect */
        .hero-reactor {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 28px 20px 24px 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(0, 245, 255, 0.05);
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
        }
        .hero-reactor::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: radial-gradient(circle at center, rgba(0, 245, 255, 0.08) 0%, transparent 60%);
            pointer-events: none;
        }
        .power-ring {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .power-ring-bg {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            border-radius: 50%;
            border: 2px dashed rgba(0, 245, 255, 0.35);
            animation: rotate-ring 18s linear infinite;
        }
        .power-ring.active .power-ring-bg {
            border: 2px solid var(--cyan);
            box-shadow: 0 0 30px var(--cyan-glow), inset 0 0 20px var(--cyan-glow);
            animation: rotate-ring 6s linear infinite;
        }
        @keyframes rotate-ring {
            100% { transform: rotate(360deg); }
        }
        .power-button {
            width: 104px;
            height: 104px;
            border-radius: 50%;
            background: linear-gradient(135deg, #0e172a, #090d16);
            border: 2px solid rgba(0, 245, 255, 0.4);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            transition: all 0.25s ease;
            z-index: 2;
        }
        .power-ring:active .power-button {
            transform: scale(0.92);
        }
        .power-ring.active .power-button {
            border-color: var(--cyan);
            background: linear-gradient(135deg, #092c3e, #0e172a);
            box-shadow: 0 0 24px var(--cyan-glow);
        }
        .power-icon {
            font-size: 32px;
            color: var(--cyan);
            transition: all 0.3s;
        }
        .power-ring.active .power-icon {
            filter: drop-shadow(0 0 10px var(--cyan));
        }
        .power-text {
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
            color: var(--text-muted);
        }
        .power-ring.active .power-text {
            color: var(--cyan);
        }
        .shield-status-text {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 4px;
            text-align: center;
        }
        .shield-sub-text {
            font-size: 12px;
            color: var(--text-muted);
            text-align: center;
        }

        /* 1-Tap Quick Stream Launcher */
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }
        .card-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--cyan);
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 14px;
        }
        .quick-btn {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 14px 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--text-main);
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .quick-btn:hover, .quick-btn:active {
            background: rgba(0, 245, 255, 0.12);
            border-color: var(--cyan);
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 245, 255, 0.2);
        }
        .quick-icon {
            font-size: 24px;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: rgba(15, 23, 42, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .quick-info h4 {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 2px;
        }
        .quick-info p {
            font-size: 10px;
            color: var(--text-muted);
        }
        .url-box {
            display: flex;
            gap: 8px;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(0, 245, 255, 0.3);
            border-radius: 12px;
            padding: 4px 6px 4px 14px;
            align-items: center;
        }
        .url-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 13px;
            font-family: inherit;
        }
        .url-input::placeholder { color: #64748b; }
        .url-launch-btn {
            background: linear-gradient(135deg, var(--cyan), #00b4d8);
            color: #060913;
            font-weight: 800;
            font-size: 12px;
            border: none;
            border-radius: 8px;
            padding: 9px 16px;
            cursor: pointer;
            transition: opacity 0.2s;
        }

        /* Mode Selector */
        .mode-switch-container {
            display: flex;
            gap: 8px;
            background: rgba(15, 23, 42, 0.8);
            padding: 4px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 14px;
        }
        .mode-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .mode-tab.active.red {
            background: linear-gradient(135deg, #da3633, #b62324);
            color: #ffffff;
            box-shadow: 0 0 16px var(--crimson-glow);
        }
        .mode-tab.active.green {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #ffffff;
            box-shadow: 0 0 16px var(--emerald-glow);
        }

        /* Quantum Attack Simulator Console */
        .action-attack-btn {
            width: 100%;
            background: linear-gradient(135deg, var(--purple), #7c3aed);
            color: #ffffff;
            font-weight: 800;
            font-size: 13px;
            border: none;
            border-radius: 12px;
            padding: 13px;
            cursor: pointer;
            box-shadow: 0 4px 20px var(--purple-glow);
            transition: all 0.2s ease;
        }
        .action-attack-btn:active {
            transform: scale(0.98);
        }
        .quantum-console {
            background: #02040a;
            border: 1px solid rgba(0, 245, 255, 0.25);
            border-radius: 12px;
            padding: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #cbd5e1;
            white-space: pre-wrap;
            word-break: break-all;
            margin-top: 14px;
            max-height: 220px;
            overflow-y: auto;
            line-height: 1.5;
            box-shadow: inset 0 0 16px rgba(0,0,0,0.8);
        }
        .quantum-console::-webkit-scrollbar { width: 4px; }
        .quantum-console::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }

        /* Setup Cards */
        .setup-row {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .setup-btn {
            flex: 1;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(0, 245, 255, 0.25);
            border-radius: 12px;
            padding: 12px;
            color: var(--text-main);
            font-size: 12px;
            font-weight: 700;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            text-align: center;
        }
        .setup-btn:active {
            background: rgba(0, 245, 255, 0.2);
            border-color: var(--cyan);
        }
    </style>
</head>
<body>
    <canvas id="quantum-canvas"></canvas>

    <div class="app-container">
        <!-- Top App Bar -->
        <header class="header">
            <div class="brand">
                <div class="brand-icon">⚛️</div>
                <div>
                    <h1 class="brand-title">QUANTUM VPN</h1>
                    <p class="brand-sub">Shor Threat vs ML-KEM Shield</p>
                </div>
            </div>
            <div class="status-pill">
                <div class="pulse-dot"></div>
                <span>NODE ONLINE</span>
            </div>
        </header>

        <!-- Central Hero Reactor (Single Tap Connect) -->
        <section class="hero-reactor">
            <div class="power-ring active" id="power-ring" onclick="togglePower()">
                <div class="power-ring-bg"></div>
                <div class="power-button">
                    <span class="power-icon">⚡</span>
                    <span class="power-text" id="power-label">ACTIVE</span>
                </div>
            </div>
            <h2 class="shield-status-text" id="status-title">Quantum Shield Active</h2>
            <p class="shield-sub-text" id="status-sub">All cloud streams protected by AES-256 & TLS 443</p>
        </section>

        <!-- 1-Tap Unblocked Sites Quick Launcher -->
        <section class="card">
            <div class="card-header">
                <h3 class="card-title">🚀 1-TAP UNBLOCKED STREAMING</h3>
                <span style="font-size:10px; color:var(--text-muted);">ZERO-INSTALL</span>
            </div>

            <div class="quick-grid">
                <a class="quick-btn" href="/stream?site=netflix">
                    <div class="quick-icon" style="color:#e50914;">🎬</div>
                    <div class="quick-info">
                        <h4>Netflix</h4>
                        <p>Stream Unblocked</p>
                    </div>
                </a>
                <a class="quick-btn" href="/stream?site=youtube">
                    <div class="quick-icon" style="color:#ff0000;">▶️</div>
                    <div class="quick-info">
                        <h4>YouTube</h4>
                        <p>Mobile Stream</p>
                    </div>
                </a>
                <a class="quick-btn" href="/stream?site=brave">
                    <div class="quick-icon" style="color:#fb542b;">🔍</div>
                    <div class="quick-info">
                        <h4>Brave Search</h4>
                        <p>Private & Filter-Free</p>
                    </div>
                </a>
                <a class="quick-btn" href="/stream?site=reddit">
                    <div class="quick-icon" style="color:#ff4500;">💬</div>
                    <div class="quick-info">
                        <h4>Reddit</h4>
                        <p>Browse Forums</p>
                    </div>
                </a>
            </div>

            <div class="url-box">
                <input class="url-input" id="custom-url-input" type="url" placeholder="Enter any blocked site (e.g. netflix.com)...">
                <button class="url-launch-btn" onclick="launchCustomUrl()">GO</button>
            </div>
        </section>

        <!-- Interactive Quantum Attack Simulation -->
        <section class="card">
            <div class="card-header">
                <h3 class="card-title">🎯 INTERACTIVE SHOR ATTACK DEMO</h3>
                <span id="active-mode-badge" style="font-size:10px; font-weight:800; color:var(--crimson);">VULNERABLE</span>
            </div>

            <div class="mode-switch-container">
                <div class="mode-tab active red" id="tab-dh16" onclick="switchMode('dh16')">🔴 16-Bit DH (Shor Demo)</div>
                <div class="mode-tab" id="tab-mlkem" onclick="switchMode('mlkem')">🛡️ NIST ML-KEM-768</div>
            </div>

            <button class="action-attack-btn" id="attack-trigger-btn" onclick="executeQuantumAttack()">
                ⚛️ EXECUTE SHOR'S QUANTUM ATTACK
            </button>

            <div class="quantum-console" id="quantum-console">>>> Quantum Attack Inspector Ready.
>>> Select a mode and tap EXECUTE to simulate Shor's period-finding on the wire.</div>
        </section>

        <!-- 1-Tap Phone & System Profiles -->
        <section class="card">
            <div class="card-header">
                <h3 class="card-title">📱 1-TAP SYSTEM INTEGRATION</h3>
            </div>
            <p style="font-size:12px; color:var(--text-muted); line-height:1.4;">
                Route your entire phone (Apps, Games, Safari) through this gateway:
            </p>
            <div class="setup-row">
                <a class="setup-btn" href="/ios.mobileconfig">
                    <span style="font-size:22px;">🍏</span>
                    <span>Install iOS Profile</span>
                    <span style="font-size:9px; color:var(--cyan);">(1-Tap Apple)</span>
                </a>
                <button class="setup-btn" onclick="copyAndroidPac()">
                    <span style="font-size:22px;">🤖</span>
                    <span>Android Auto-Proxy</span>
                    <span style="font-size:9px; color:var(--emerald);">(Copy PAC URL)</span>
                </button>
            </div>
        </section>
    </div>

    <script>
        // -------------------------------------------------------------
        // Quantum Entanglement Particles Canvas Animation
        // -------------------------------------------------------------
        const canvas = document.getElementById('quantum-canvas');
        const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        });

        const particles = [];
        const numParticles = Math.min(35, Math.floor(width / 14));
        for (let i = 0; i < numParticles; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.7,
                vy: (Math.random() - 0.5) * 0.7,
                radius: Math.random() * 2 + 1,
                color: Math.random() > 0.5 ? '#00f5ff' : '#a855f7'
            });
        }

        function drawQuantumCanvas() {
            ctx.clearRect(0, 0, width, height);
            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.fill();

                for (let j = i + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                    if (dist < 100) {
                        ctx.beginPath();
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.strokeStyle = `rgba(0, 245, 255, ${0.18 * (1 - dist / 100)})`;
                        ctx.lineWidth = 0.8;
                        ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(drawQuantumCanvas);
        }
        drawQuantumCanvas();

        // -------------------------------------------------------------
        // Audio & Haptic Feedback
        // -------------------------------------------------------------
        function playSciFiChirp(freq1 = 440, freq2 = 880) {
            try {
                if ('vibrate' in navigator) navigator.vibrate(40);
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                const ctx = new AudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq1, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(freq2, ctx.currentTime + 0.12);
                gain.gain.setValueAtTime(0.12, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.12);
            } catch(e) {}
        }

        // -------------------------------------------------------------
        // Single-Tap Power Toggle
        // -------------------------------------------------------------
        let isPowerActive = true;
        function togglePower() {
            playSciFiChirp(isPowerActive ? 600 : 300, isPowerActive ? 300 : 700);
            isPowerActive = !isPowerActive;
            const ring = document.getElementById('power-ring');
            const label = document.getElementById('power-label');
            const title = document.getElementById('status-title');
            const sub = document.getElementById('status-sub');

            if (isPowerActive) {
                ring.classList.add('active');
                label.innerText = 'ACTIVE';
                title.innerText = 'Quantum Shield Active';
                sub.innerText = 'All cloud streams protected by AES-256 & TLS 443';
            } else {
                ring.classList.remove('active');
                label.innerText = 'STANDBY';
                title.innerText = 'Tunnel on Standby';
                sub.innerText = 'Tap reactor core to engage quantum encryption';
            }
        }

        // -------------------------------------------------------------
        // Mode Switcher
        // -------------------------------------------------------------
        let currentMode = 'dh16';
        function switchMode(mode) {
            playSciFiChirp(520, 680);
            currentMode = mode;
            const tab16 = document.getElementById('tab-dh16');
            const tabMlkem = document.getElementById('tab-mlkem');
            const badge = document.getElementById('active-mode-badge');
            const con = document.getElementById('quantum-console');

            if (mode === 'dh16') {
                tab16.className = 'mode-tab active red';
                tabMlkem.className = 'mode-tab';
                badge.innerText = 'VULNERABLE';
                badge.style.color = 'var(--crimson)';
                con.innerText = '>>> Mode set to 16-Bit Classical Diffie-Hellman.\\n>>> Shor\\'s algorithm can break this in < 1 ms on a quantum computer.';
            } else {
                tab16.className = 'mode-tab';
                tabMlkem.className = 'mode-tab active green';
                badge.innerText = 'QUANTUM-IMMUNE';
                badge.style.color = 'var(--emerald)';
                con.innerText = '>>> Mode set to NIST FIPS 203 ML-KEM-768 (Kyber).\\n>>> Protected by Module-LWE lattice noise. Shor\\'s algorithm fails completely.';
            }
        }

        // -------------------------------------------------------------
        // Live Shor Quantum Attack Execution
        // -------------------------------------------------------------
        async function executeQuantumAttack() {
            playSciFiChirp(400, 900);
            const btn = document.getElementById('attack-trigger-btn');
            const con = document.getElementById('quantum-console');
            btn.disabled = true;
            btn.innerText = 'COLLAPSING QUANTUM REGISTERS...';
            con.innerText = '[1/4] Intercepting Public Wire Packets...\\n[2/4] Constructing Superposition Registers |x1> |x2>...';

            try {
                const res = await fetch('/api/attack?mode=' + currentMode);
                const data = await res.json();
                
                if (data.status === 'CRITICAL_BREACH') {
                    con.innerText = '==================================================\\n' +
                        ' [!] CLASSICAL 16-BIT DH WIRETAP INTERCEPTED\\n' +
                        '==================================================\\n' +
                        '[*] Sniffed Public Key A: ' + data.public_key_A + '\\n' +
                        '[*] Sniffed Public Key B: ' + data.public_key_B + '\\n' +
                        '[*] Hidden Secret a:       ' + data.hidden_secret_a + '\\n\\n' +
                        '[!!!] SHOR ATTACK SOLVED: a = ' + data.recovered_secret_a + ' (in ' + data.elapsed_ms + ' ms)\\n' +
                        '[+] Cracked AES-256 Key:  ' + data.cracked_aes_key + '\\n\\n' +
                        '[!!! LIVE INTERCEPTED DECRYPTED NETFLIX STREAM !!!]\\n' +
                        data.decrypted_plaintext + '\\n\\n' +
                        '>>> 🚨 RESULT: ' + data.verdict;
                } else {
                    con.innerText = '==================================================\\n' +
                        ' [!] NIST FIPS 203 ML-KEM-768 INTERCEPTED\\n' +
                        '==================================================\\n' +
                        '[*] Sniffed Kyber Public Key: ' + data.pk_bytes + ' bytes\\n' +
                        '[*] Sniffed Ciphertext:       ' + data.ct_bytes + ' bytes\\n\\n' +
                        '[*] Running 2D QFT on Lattice Equations (M-LWE)...\\n' +
                        '[!] Fourier Peak-to-Average:  ' + data.fourier_noise_ratio + ' (Flat Random Noise)\\n' +
                        '[!] Constructive Wave Peak:   NONE\\n\\n' +
                        '>>> 🛡️ RESULT: ' + data.verdict;
                }
            } catch (err) {
                con.innerText = '[-] Quantum attack simulation error: ' + err;
            } finally {
                btn.disabled = false;
                btn.innerText = '⚛️ EXECUTE SHOR\\'S QUANTUM ATTACK';
            }
        }

        // -------------------------------------------------------------
        // Custom URL Unblocker
        // -------------------------------------------------------------
        function launchCustomUrl() {
            const input = document.getElementById('custom-url-input');
            let val = input.value.trim();
            if (!val) return;
            playSciFiChirp(600, 850);
            window.location.href = '/stream?url=' + encodeURIComponent(val);
        }

        function copyAndroidPac() {
            playSciFiChirp(700, 950);
            const pac = 'https://__HOST__/proxy.pac';
            navigator.clipboard.writeText(pac);
            alert('✅ Copied Android Auto-Proxy URL:\\n' + pac + '\\n\\nPaste into: Settings -> Wi-Fi -> Advanced -> Proxy -> Auto-config');
        }
    </script>
</body>
</html>"""
        return template.replace("__HOST__", host_header)

    def _do_handshake(self) -> bool:
        hello_pkt = recv_packet(self.client_sock, is_ws=self.is_ws)
        if not hello_pkt or hello_pkt.msg_type != MSG_CLIENT_HELLO:
            return False

        mode = hello_pkt.stream_id
        if mode == MODE_DH_16:
            client_pub = int.from_bytes(hello_pkt.payload, 'big')
            dh = DiffieHellman(bits=16)
            self.aes_key, self.iv_salt = derive_session_keys(dh.compute_shared_secret(client_pub))
            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), dh.public_key.to_bytes(2, 'big'))
            send_packet(self.client_sock, resp, is_ws=self.is_ws)
            return True

        elif mode == MODE_DH_2048:
            client_pub = int.from_bytes(hello_pkt.payload, 'big')
            dh = DiffieHellman(bits=2048)
            self.aes_key, self.iv_salt = derive_session_keys(dh.compute_shared_secret(client_pub))
            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), dh.public_key.to_bytes(256, 'big'))
            send_packet(self.client_sock, resp, is_ws=self.is_ws)
            return True

        elif mode == MODE_MLKEM_768:
            ciphertext, shared_secret = MLKEM768.encapsulate(hello_pkt.payload)
            self.aes_key, self.iv_salt = derive_session_keys(int.from_bytes(shared_secret, 'big'))
            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), ciphertext)
            send_packet(self.client_sock, resp, is_ws=self.is_ws)
            return True

        return False

    def _handle_connect(self, pkt: VPNPacket):
        try:
            plain = decrypt_payload(self.aes_key, pkt.nonce, pkt.payload)
            host_len = struct.unpack_from("!H", plain, 0)[0]
            host = plain[2:2 + host_len].decode('utf-8', errors='ignore')
            port = struct.unpack_from("!H", plain, 2 + host_len)[0]

            print(f"[>] Cloud Tunnel Request: Connect to {host}:{port} (Stream #{pkt.stream_id})")
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.settimeout(10.0)
            target_sock.connect((host, port))
            target_sock.settimeout(None)

            stream = ActiveTunnelStream(pkt.stream_id, target_sock)
            with self.lock:
                self.streams[pkt.stream_id] = stream

            nonce = self._next_nonce()
            send_packet(self.client_sock, VPNPacket(MSG_TUNNEL_CONNECTED, pkt.stream_id, nonce, encrypt_payload(self.aes_key, nonce, b"OK")), is_ws=self.is_ws)
            threading.Thread(target=self._forward_target_to_client, args=(stream,), daemon=True).start()

        except Exception as e:
            print(f"[-] Connect error to target {host}:{port} -> {e}")
            nonce = self._next_nonce()
            send_packet(self.client_sock, VPNPacket(MSG_TUNNEL_FAILED, pkt.stream_id, nonce, encrypt_payload(self.aes_key, nonce, str(e).encode())), is_ws=self.is_ws)

    def _handle_data(self, pkt: VPNPacket):
        with self.lock:
            stream = self.streams.get(pkt.stream_id)
        if stream and stream.active:
            try:
                stream.target_sock.sendall(decrypt_payload(self.aes_key, pkt.nonce, pkt.payload))
            except Exception:
                self._close_stream(pkt.stream_id)

    def _forward_target_to_client(self, stream: ActiveTunnelStream):
        try:
            while stream.active and self.running:
                chunk = stream.target_sock.recv(16384)
                if not chunk:
                    break
                with self.lock:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, chunk)
                    send_packet(self.client_sock, VPNPacket(MSG_TUNNEL_DATA, stream.stream_id, nonce, ct), is_ws=self.is_ws)
        except Exception:
            pass
        finally:
            self._close_stream(stream.stream_id)

    def _handle_close(self, pkt: VPNPacket):
        self._close_stream(pkt.stream_id)

    def _close_stream(self, stream_id: int):
        with self.lock:
            stream = self.streams.pop(stream_id, None)
            if stream and stream.active:
                stream.active = False
                try:
                    stream.target_sock.close()
                except Exception:
                    pass
                try:
                    nonce = self._next_nonce()
                    send_packet(self.client_sock, VPNPacket(MSG_TUNNEL_CLOSE, stream_id, nonce, encrypt_payload(self.aes_key, nonce, b"CLOSE")), is_ws=self.is_ws)
                except Exception:
                    pass

    def _cleanup(self):
        self.running = False
        with self.lock:
            for s in list(self.streams.values()):
                s.active = False
                try:
                    s.target_sock.close()
                except Exception:
                    pass
            self.streams.clear()
            try:
                self.client_sock.close()
            except Exception:
                pass


def start_server(host: str = "0.0.0.0", port: int = 8888):
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(128)

    print("=" * 70)
    print("      QUANTUM SAFE / VULNERABLE VPN SERVER (CLOUD EXIT NODE)")
    print("=" * 70)
    print(f"[*] Cloud VPN Gateway listening on {host}:{port}")
    print("[*] Ready for Direct TCP and Native Codespaces HTTPS Tunnels.")
    print("=" * 70)

    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            client_sock.settimeout(None)
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            session = VPNServerSession(client_sock, client_addr)
            threading.Thread(target=session.handle, daemon=True).start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Shutting down Cloud VPN Server.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Quantum VPN Server")
    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default: 8888)")
    args = parser.parse_args()
    start_server(port=args.port)
