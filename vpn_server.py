"""
vpn_server.py - Custom Zero-Dependency VPN Server & Gateway.

Acts as the remote VPN tunnel exit node.
1. Handshakes with clients using DH-16 (Shor-vulnerable), DH-2048, or ML-KEM-768.
2. Decrypts tunnel streams using AES-256-GCM.
3. Forwards outbound traffic to real internet destinations (e.g. Netflix, websites).
4. Relays responses back through the encrypted tunnel to the client.
"""

import sys
import os
import socket
import threading
import argparse
import struct
import time
from typing import Dict

from vpn_crypto import (
    DiffieHellman,
    derive_session_keys,
    encrypt_payload,
    decrypt_payload,
    MLKEM768,
    DEMO_PRIME_16,
    DEMO_GEN_16,
    RFC3526_2048_PRIME,
    RFC3526_2048_GEN,
)
from vpn_protocol import (
    VPNPacket,
    send_packet,
    recv_packet,
    MSG_CLIENT_HELLO,
    MSG_SERVER_HELLO,
    MSG_HANDSHAKE_COMPLETE,
    MSG_TUNNEL_CONNECT,
    MSG_TUNNEL_CONNECTED,
    MSG_TUNNEL_DATA,
    MSG_TUNNEL_CLOSE,
    MSG_TUNNEL_FAILED,
    MODE_DH_16,
    MODE_DH_2048,
    MODE_MLKEM_768,
)


class ActiveTunnelStream:
    def __init__(self, stream_id: int, target_sock: socket.socket):
        self.stream_id = stream_id
        self.target_sock = target_sock
        self.active = True


class VPNServerSession:
    def __init__(self, client_sock: socket.socket, client_addr: tuple, forced_mode: str = "dh16"):
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.forced_mode = forced_mode
        self.aes_key: bytes = b""
        self.iv_salt: bytes = b""
        self.seq_num: int = 0
        self.streams: Dict[int, ActiveTunnelStream] = {}
        self.lock = threading.Lock()
        self.running = True

    def _next_nonce(self) -> bytes:
        self.seq_num += 1
        return self.iv_salt[:8] + struct.pack("!I", self.seq_num)

    def handle(self):
        print(f"[*] New incoming connection from {self.client_addr[0]}:{self.client_addr[1]}")
        try:
            # 1. Handshake
            if not self._do_handshake():
                print(f"[-] Handshake failed with {self.client_addr}")
                return

            print(f"[+] Encrypted Tunnel Established with {self.client_addr}! AES-256-GCM session active.")

            # 2. Main packet dispatch loop
            while self.running:
                pkt = recv_packet(self.client_sock)
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

    def _do_handshake(self) -> bool:
        hello_pkt = recv_packet(self.client_sock)
        if not hello_pkt or hello_pkt.msg_type != MSG_CLIENT_HELLO:
            return False

        mode = hello_pkt.stream_id

        if mode == MODE_DH_16:
            print("[*] Handshake Mode: Classical 16-bit Diffie-Hellman (Shor Vulnerable)")
            client_pub = int.from_bytes(hello_pkt.payload, 'big')
            dh_server = DiffieHellman(bits=16)
            shared_secret = dh_server.compute_shared_secret(client_pub)
            self.aes_key, self.iv_salt = derive_session_keys(shared_secret)

            server_pub_bytes = dh_server.public_key.to_bytes(2, 'big')
            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), server_pub_bytes)
            send_packet(self.client_sock, resp)
            return True

        elif mode == MODE_DH_2048:
            print("[*] Handshake Mode: Production 2048-bit Diffie-Hellman")
            client_pub = int.from_bytes(hello_pkt.payload, 'big')
            dh_server = DiffieHellman(bits=2048)
            shared_secret = dh_server.compute_shared_secret(client_pub)
            self.aes_key, self.iv_salt = derive_session_keys(shared_secret)

            server_pub_bytes = dh_server.public_key.to_bytes(256, 'big')
            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), server_pub_bytes)
            send_packet(self.client_sock, resp)
            return True

        elif mode == MODE_MLKEM_768:
            print("[*] Handshake Mode: Post-Quantum NIST FIPS 203 (ML-KEM-768 / Kyber)")
            client_pk = hello_pkt.payload
            ciphertext, shared_secret = MLKEM768.encapsulate(client_pk)
            # Derive session keys directly from Kyber shared secret
            self.aes_key, self.iv_salt = derive_session_keys(int.from_bytes(shared_secret, 'big'))

            resp = VPNPacket(MSG_SERVER_HELLO, mode, bytes(12), ciphertext)
            send_packet(self.client_sock, resp)
            return True

        return False

    def _handle_connect(self, pkt: VPNPacket):
        """Decrypts connect request and opens outgoing connection to target host:port."""
        try:
            plain = decrypt_payload(self.aes_key, pkt.nonce, pkt.payload)
            # Format: [2 bytes host_len][host string][2 bytes port]
            host_len = struct.unpack_from("!H", plain, 0)[0]
            host = plain[2:2 + host_len].decode('utf-8', errors='ignore')
            port = struct.unpack_from("!H", plain, 2 + host_len)[0]

            print(f"[>] Tunnel Request: Connect to {host}:{port} (Stream #{pkt.stream_id})")

            # Outbound connect
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.settimeout(10.0)
            target_sock.connect((host, port))
            target_sock.settimeout(None)

            stream = ActiveTunnelStream(pkt.stream_id, target_sock)
            with self.lock:
                self.streams[pkt.stream_id] = stream

            # Reply connected
            nonce = self._next_nonce()
            ack_ct = encrypt_payload(self.aes_key, nonce, b"OK")
            ack_pkt = VPNPacket(MSG_TUNNEL_CONNECTED, pkt.stream_id, nonce, ack_ct)
            with self.lock:
                send_packet(self.client_sock, ack_pkt)

            # Spawn reader thread from target back to client
            t = threading.Thread(target=self._forward_target_to_client, args=(stream,), daemon=True)
            t.start()

        except Exception as e:
            print(f"[-] Connect error to target: {e}")
            nonce = self._next_nonce()
            err_ct = encrypt_payload(self.aes_key, nonce, str(e).encode())
            fail_pkt = VPNPacket(MSG_TUNNEL_FAILED, pkt.stream_id, nonce, err_ct)
            with self.lock:
                send_packet(self.client_sock, fail_pkt)

    def _handle_data(self, pkt: VPNPacket):
        """Decrypts inbound data from client and forwards to target socket."""
        with self.lock:
            stream = self.streams.get(pkt.stream_id)

        if not stream or not stream.active:
            return

        try:
            plain = decrypt_payload(self.aes_key, pkt.nonce, pkt.payload)
            stream.target_sock.sendall(plain)
        except Exception as e:
            self._close_stream(pkt.stream_id)

    def _forward_target_to_client(self, stream: ActiveTunnelStream):
        """Reads plaintext from destination, encrypts with AES-256-GCM, and sends across VPN tunnel."""
        try:
            while stream.active and self.running:
                chunk = stream.target_sock.recv(16384)
                if not chunk:
                    break

                with self.lock:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, chunk)
                    pkt = VPNPacket(MSG_TUNNEL_DATA, stream.stream_id, nonce, ct)
                    send_packet(self.client_sock, pkt)
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
                # Notify client
                try:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, b"CLOSE")
                    pkt = VPNPacket(MSG_TUNNEL_CLOSE, stream_id, nonce, ct)
                    send_packet(self.client_sock, pkt)
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
        print(f"[*] Closed session with {self.client_addr}")


def start_server(host: str = "0.0.0.0", port: int = 8888):
    import signal
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(128)
    server_sock.settimeout(0.5)  # Enables immediate Ctrl+C response on Windows

    print("=" * 70)
    print("        QUANTUM SAFE / VULNERABLE VPN SERVER GATEWAY")
    print("=" * 70)
    print(f"[*] Listening for VPN clients on {host}:{port}")
    print("[*] Ready to accept DH-16 (Demo), DH-2048 (Prod), or ML-KEM-768 connections.")
    print("=" * 70)

    try:
        while True:
            try:
                client_sock, client_addr = server_sock.accept()
            except (socket.timeout, TimeoutError):
                continue
            client_sock.settimeout(None)  # Crucial: reset timeout inherited from server_sock
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            session = VPNServerSession(client_sock, client_addr)
            t = threading.Thread(target=session.handle, daemon=True)
            t.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Shutting down VPN Server.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Custom Quantum-Vulnerable / Quantum-Safe VPN Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default: 8888)")
    args = parser.parse_args()

    start_server(args.host, args.port)
