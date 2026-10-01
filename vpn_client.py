"""
vpn_client.py - Custom Zero-Dependency VPN Client with built-in SOCKS5 Proxy.
Supports both Direct Raw TCP and Native Codespaces HTTPS / WebSocket reverse proxies.

1. Connects to remote VPN Server (supports *.app.github.dev over HTTPS/WSS port 443).
2. Performs Handshake (DH-16 for Shor demo, DH-2048, or ML-KEM-768 for Quantum-Safe).
3. Spawns local SOCKS5 Proxy on 127.0.0.1:1080.
4. Encrypts all browser traffic (Netflix, web) through the VPN tunnel to the server.
"""

import sys
import os
import socket
import ssl
import base64
import threading
import argparse
import struct
import time
from typing import Dict, Tuple

from vpn_crypto import (
    DiffieHellman,
    derive_session_keys,
    encrypt_payload,
    decrypt_payload,
    MLKEM768,
)
from vpn_protocol import (
    VPNPacket,
    send_packet,
    recv_packet,
    MSG_CLIENT_HELLO,
    MSG_SERVER_HELLO,
    MSG_TUNNEL_CONNECT,
    MSG_TUNNEL_CONNECTED,
    MSG_TUNNEL_DATA,
    MSG_TUNNEL_CLOSE,
    MSG_TUNNEL_FAILED,
    MODE_DH_16,
    MODE_DH_2048,
    MODE_MLKEM_768,
)



def set_windows_system_proxy(enable: bool, host: str = "127.0.0.1", port: int = 1080) -> bool:
    """Configures or clears Windows Internet Settings system proxy."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        import ctypes
        internet_settings = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
            0, winreg.KEY_ALL_ACCESS
        )
        if enable:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, f'http={host}:{port};https={host}:{port};socks={host}:{port}')
        else:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(internet_settings)
        # 39 = INTERNET_OPTION_SETTINGS_CHANGED, 37 = INTERNET_OPTION_REFRESH
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        return True
    except Exception as e:
        print(f"[-] Failed to configure Windows system proxy: {e}")
        return False


class ClientStream:
    def __init__(self, stream_id: int, browser_sock: socket.socket):
        self.stream_id = stream_id
        self.browser_sock = browser_sock
        self.connected_event = threading.Event()
        self.connected_ok = False
        self.active = True


class VPNClient:
    def __init__(self, server_host: str, server_port: int = 8888, mode: str = "dh16", socks_port: int = 1080):
        # Clean host string (strip https:// or trailing /)
        host = server_host.replace("https://", "").replace("http://", "").strip("/")
        if ":" in host:
            parts = host.split(":")
            host = parts[0]
            server_port = int(parts[1])

        self.server_host = host
        self.server_port = server_port
        self.mode_str = mode.lower()
        self.socks_port = socks_port

        self.is_ws = False
        self.vpn_sock: socket.socket = None
        self.socks_sock: socket.socket = None
        self.aes_key: bytes = b""
        self.iv_salt: bytes = b""
        self.seq_num: int = 0
        self.stream_counter: int = 1000

        self.streams: Dict[int, ClientStream] = {}
        self.lock = threading.Lock()
        self.running = True
        self.is_connected = False

        self.log_callback = None
        self.status_callback = None
        self.bytes_sent = 0
        self.bytes_recv = 0

    def log(self, msg: str):
        print(msg)
        if self.log_callback:
            try:
                self.log_callback(msg)
            except Exception:
                pass

    def _next_nonce(self) -> bytes:
        self.seq_num += 1
        return self.iv_salt[:8] + struct.pack("!I", self.seq_num)

    def start_async(self, on_connected=None, on_error=None):
        def _runner():
            try:
                self.start(on_connected=on_connected)
            except Exception as e:
                self.log(f"[-] Connection failed: {e}")
                self.is_connected = False
                if self.status_callback:
                    self.status_callback(False)
                if on_error:
                    on_error(e)
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        return t

    def stop(self):
        self.running = False
        self.is_connected = False
        if self.status_callback:
            try:
                self.status_callback(False)
            except Exception:
                pass
        if self.socks_sock:
            try:
                self.socks_sock.close()
            except Exception:
                pass
        self._cleanup()
        self.log("[*] VPN Client stopped.")

    def start(self, on_connected=None):
        # 1. Connect to VPN Server
        is_github_dev = self.server_host.endswith(".github.dev")
        if is_github_dev and self.server_port == 8888:
            self.server_port = 443

        self.log(f"[*] Connecting to VPN Server at {self.server_host}:{self.server_port}...")
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        raw_sock.connect((self.server_host, self.server_port))

        # Check if connecting to GitHub Codespaces over HTTPS
        if is_github_dev or self.server_port == 443:
            self.log("[*] Detected Codespaces HTTPS endpoint. Establishing TLS & WebSocket tunnel...")
            context = ssl.create_default_context()
            self.vpn_sock = context.wrap_socket(raw_sock, server_hostname=self.server_host)
            
            # Send WebSocket upgrade request
            raw_key = os.urandom(16)
            ws_key = base64.b64encode(raw_key).decode('utf-8')
            req = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {self.server_host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode('utf-8')
            self.vpn_sock.sendall(req)

            resp_buf = b""
            while b"\r\n\r\n" not in resp_buf:
                chunk = self.vpn_sock.recv(512)
                if not chunk:
                    raise RuntimeError("Codespaces closed the connection during WebSocket upgrade.")
                resp_buf += chunk

            if b"101 Switching Protocols" not in resp_buf:
                raise RuntimeError(f"WebSocket upgrade rejected by Codespaces: {resp_buf[:200]}")

            self.is_ws = True
            self.log("[+] Successfully connected to Codespaces via HTTPS / WebSocket tunnel!")
        else:
            self.vpn_sock = raw_sock

        # 2. Perform Handshake
        self._do_handshake()
        self.is_connected = True
        self.log("[+] Encrypted Tunnel Established! All traffic protected by AES-256-GCM.")
        if on_connected:
            on_connected()
        if self.status_callback:
            self.status_callback(True)

        # 3. Start VPN reader thread (receiving decrypted data from server)
        reader_t = threading.Thread(target=self._vpn_tunnel_reader, daemon=True)
        reader_t.start()

        # 4. Start local SOCKS5 Proxy Server
        self._start_socks5_server()

    def _do_handshake(self):
        if self.mode_str == "dh16":
            print("[*] Handshake: Initiating 16-bit Diffie-Hellman (Classical - Shor Vulnerable)...")
            dh = DiffieHellman(bits=16)
            pub_bytes = dh.public_key.to_bytes(2, 'big')
            pkt = VPNPacket(MSG_CLIENT_HELLO, MODE_DH_16, bytes(12), pub_bytes)
            send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

            resp = recv_packet(self.vpn_sock, is_ws=self.is_ws)
            if resp is None:
                raise RuntimeError("VPN server closed connection during handshake. Check if cloud_server.py is running on Codespaces!")
            if resp.msg_type != MSG_SERVER_HELLO:
                raise RuntimeError(f"Unexpected packet type {resp.msg_type} from server (expected MSG_SERVER_HELLO).")

            server_pub = int.from_bytes(resp.payload, 'big')
            shared_secret = dh.compute_shared_secret(server_pub)
            self.aes_key, self.iv_salt = derive_session_keys(shared_secret)

            print(f"[+] Classical DH-16 Handshake Success!")
            print(f"    - Modulus p: {dh.p}, Generator g: {dh.g}")
            print(f"    - Client Private Key a: {dh.private_key}")
            print(f"    - Client Public Key A:  {dh.public_key}")
            print(f"    - Server Public Key B:  {server_pub}")
            print(f"    - Derived Shared Secret K: {shared_secret}")
            print(f"    - AES-256 Key: {self.aes_key.hex()[:16]}... (256-bit)")

        elif self.mode_str == "dh2048":
            print("[*] Handshake: Initiating 2048-bit Diffie-Hellman (Production Classical)...")
            dh = DiffieHellman(bits=2048)
            pub_bytes = dh.public_key.to_bytes(256, 'big')
            pkt = VPNPacket(MSG_CLIENT_HELLO, MODE_DH_2048, bytes(12), pub_bytes)
            send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

            resp = recv_packet(self.vpn_sock, is_ws=self.is_ws)
            if resp is None:
                raise RuntimeError("VPN server closed connection during handshake.")
            if resp.msg_type != MSG_SERVER_HELLO:
                raise RuntimeError("Invalid handshake response from VPN server.")

            server_pub = int.from_bytes(resp.payload, 'big')
            shared_secret = dh.compute_shared_secret(server_pub)
            self.aes_key, self.iv_salt = derive_session_keys(shared_secret)
            print(f"[+] Production DH-2048 Handshake Success!")
            print(f"    - Modulus p: 2048-bit RFC 3526")
            print(f"    - AES-256 Key: {self.aes_key.hex()[:16]}... (256-bit)")

        elif self.mode_str == "mlkem":
            print("[*] Handshake: Initiating NIST FIPS 203 ML-KEM-768 (Post-Quantum Lattice)...")
            pk, sk = MLKEM768.keygen()
            pkt = VPNPacket(MSG_CLIENT_HELLO, MODE_MLKEM_768, bytes(12), pk)
            send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

            resp = recv_packet(self.vpn_sock, is_ws=self.is_ws)
            if resp is None:
                raise RuntimeError("VPN server closed connection during handshake.")
            if resp.msg_type != MSG_SERVER_HELLO:
                raise RuntimeError("Invalid handshake response from VPN server.")

            ciphertext = resp.payload
            shared_secret = MLKEM768.decapsulate(sk, ciphertext)
            self.aes_key, self.iv_salt = derive_session_keys(int.from_bytes(shared_secret, 'big'))

            print(f"[+] Post-Quantum ML-KEM-768 Handshake Success!")
            print(f"    - Kyber Public Key Size: {len(pk)} bytes")
            print(f"    - Ciphertext Size: {len(ciphertext)} bytes")
            print(f"    - Post-Quantum Shared Secret: {shared_secret.hex()[:16]}...")
            print(f"    - AES-256 Key: {self.aes_key.hex()[:16]}... (256-bit)")

    def _vpn_tunnel_reader(self):
        """Reads incoming encrypted packets from the VPN server and dispatches them."""
        try:
            while self.running:
                pkt = recv_packet(self.vpn_sock, is_ws=self.is_ws)
                if not pkt:
                    break

                with self.lock:
                    stream = self.streams.get(pkt.stream_id)

                if not stream or not stream.active:
                    continue

                if pkt.msg_type == MSG_TUNNEL_CONNECTED:
                    stream.connected_ok = True
                    stream.connected_event.set()

                elif pkt.msg_type == MSG_TUNNEL_FAILED:
                    stream.connected_ok = False
                    stream.connected_event.set()

                elif pkt.msg_type == MSG_TUNNEL_DATA:
                    try:
                        plain = decrypt_payload(self.aes_key, pkt.nonce, pkt.payload)
                        stream.browser_sock.sendall(plain)
                    except Exception:
                        self._close_stream(pkt.stream_id)

                elif pkt.msg_type == MSG_TUNNEL_CLOSE:
                    self._close_stream(pkt.stream_id)

        except Exception as e:
            print(f"[-] VPN Tunnel reader terminated: {e}")
        finally:
            self.running = False

    def _start_socks5_server(self):
        """Spawns local SOCKS5 proxy server for browsers and applications."""
        try:
            if threading.current_thread() is threading.main_thread():
                import signal
                signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
        except Exception:
            pass

        socks_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socks_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socks_sock.bind(("127.0.0.1", self.socks_port))
        socks_sock.listen(128)
        socks_sock.settimeout(0.5)
        self.socks_sock = socks_sock

        self.log("=" * 75)
        self.log(f"  [+] LOCAL SOCKS5 PROXY ACTIVE ON: 127.0.0.1:{self.socks_port}")
        self.log("=" * 75)
        print("  HOW TO ROUTE NETFLIX / BROWSER TRAFFIC:")
        print(f"  1. In Firefox / Chrome / Edge: Set SOCKS Proxy to 127.0.0.1:{self.socks_port}")
        print("  2. In Terminal: curl --socks5 127.0.0.1:1080 https://www.netflix.com")
        print("  All web requests will be encrypted and tunneled through the VPN!")
        print("=" * 75)

        try:
            while self.running:
                try:
                    client_sock, client_addr = socks_sock.accept()
                except (socket.timeout, TimeoutError):
                    continue
                client_sock.settimeout(None)
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                t = threading.Thread(target=self._handle_socks5_client, args=(client_sock,), daemon=True)
                t.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n[*] Stopping VPN Client.")
        finally:
            socks_sock.close()
            self._cleanup()

    def _handle_socks5_client(self, client_sock: socket.socket):
        stream_id = None
        try:
            greeting = client_sock.recv(4096)
            if not greeting:
                client_sock.close()
                return

            is_http_connect = greeting.startswith(b"CONNECT ")
            is_http_plain = greeting.startswith(b"GET ") or greeting.startswith(b"POST ") or greeting.startswith(b"HEAD ")
            is_socks5 = (greeting[0] == 0x05)

            target_host = ""
            target_port = 80
            initial_data_to_fwd = None

            if is_http_connect:
                # HTTP CONNECT proxy request (e.g. from Brave / Chrome / Edge)
                while b"\r\n\r\n" not in greeting:
                    chunk = client_sock.recv(1024)
                    if not chunk:
                        client_sock.close()
                        return
                    greeting += chunk

                req_line = greeting.split(b"\r\n")[0].decode('utf-8', errors='ignore')
                parts = req_line.split()
                if len(parts) < 2:
                    client_sock.close()
                    return

                target = parts[1]
                if ":" in target:
                    target_host, port_str = target.split(":", 1)
                    target_port = int(port_str)
                else:
                    target_host = target
                    target_port = 443

                print(f"[HTTP Proxy] --> CONNECT {target_host}:{target_port}")

            elif is_http_plain:
                # Plain HTTP proxy request
                lines = greeting.split(b"\r\n")
                req_line = lines[0].decode('utf-8', errors='ignore')
                for line in lines[1:]:
                    if line.lower().startswith(b"host:"):
                        host_val = line.split(b":", 1)[1].strip().decode('utf-8', errors='ignore')
                        if ":" in host_val:
                            target_host, port_str = host_val.split(":", 1)
                            target_port = int(port_str)
                        else:
                            target_host = host_val
                            target_port = 80
                        break
                if not target_host:
                    client_sock.close()
                    return
                initial_data_to_fwd = greeting
                print(f"[HTTP Proxy] --> {req_line.split()[0]} {target_host}:{target_port}")

            elif is_socks5:
                # SOCKS5 Handshake
                client_sock.sendall(b"\x05\x00")
                req = client_sock.recv(4)
                if len(req) < 4 or req[0] != 0x05 or req[1] != 0x01:
                    client_sock.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                    client_sock.close()
                    return

                atyp = req[3]
                if atyp == 0x01:
                    addr_bytes = client_sock.recv(4)
                    target_host = socket.inet_ntoa(addr_bytes)
                elif atyp == 0x03:
                    domain_len = client_sock.recv(1)[0]
                    target_host = client_sock.recv(domain_len).decode('utf-8', errors='ignore')
                elif atyp == 0x04:
                    addr_bytes = client_sock.recv(16)
                    target_host = socket.inet_ntop(socket.AF_INET6, addr_bytes)
                else:
                    client_sock.close()
                    return

                port_bytes = client_sock.recv(2)
                target_port = struct.unpack("!H", port_bytes)[0]
                print(f"[SOCKS5] --> Connect to {target_host}:{target_port}")

            else:
                client_sock.close()
                return

            with self.lock:
                self.stream_counter += 1
                stream_id = self.stream_counter
                stream = ClientStream(stream_id, client_sock)
                self.streams[stream_id] = stream

            host_bytes = target_host.encode('utf-8')
            payload = struct.pack("!H", len(host_bytes)) + host_bytes + struct.pack("!H", target_port)

            nonce = self._next_nonce()
            ct = encrypt_payload(self.aes_key, nonce, payload)
            pkt = VPNPacket(MSG_TUNNEL_CONNECT, stream_id, nonce, ct)

            with self.lock:
                send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

            if not stream.connected_event.wait(timeout=10.0) or not stream.connected_ok:
                if is_http_connect or is_http_plain:
                    client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                else:
                    client_sock.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
                self._close_stream(stream_id)
                stream_id = None
                return

            if is_http_connect:
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            elif is_socks5:
                client_sock.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")

            if initial_data_to_fwd:
                with self.lock:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, initial_data_to_fwd)
                    pkt = VPNPacket(MSG_TUNNEL_DATA, stream_id, nonce, ct)
                    send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

            while stream.active and self.running:
                data = client_sock.recv(16384)
                if not data:
                    break

                with self.lock:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, data)
                    pkt = VPNPacket(MSG_TUNNEL_DATA, stream_id, nonce, ct)
                    send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)

        except Exception:
            pass
        finally:
            if stream_id is not None:
                self._close_stream(stream_id)
            else:
                try:
                    client_sock.close()
                except Exception:
                    pass

    def _close_stream(self, stream_id: int):
        with self.lock:
            stream = self.streams.pop(stream_id, None)
            if stream and stream.active:
                stream.active = False
                try:
                    stream.browser_sock.close()
                except Exception:
                    pass
                try:
                    nonce = self._next_nonce()
                    ct = encrypt_payload(self.aes_key, nonce, b"CLOSE")
                    pkt = VPNPacket(MSG_TUNNEL_CLOSE, stream_id, nonce, ct)
                    send_packet(self.vpn_sock, pkt, is_ws=self.is_ws, is_client=True)
                except Exception:
                    pass

    def _cleanup(self):
        self.running = False
        with self.lock:
            for s in list(self.streams.values()):
                s.active = False
                try:
                    s.browser_sock.close()
                except Exception:
                    pass
            self.streams.clear()
            if self.vpn_sock:
                try:
                    self.vpn_sock.close()
                except Exception:
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Custom Quantum-Vulnerable / Quantum-Safe VPN Client")
    parser.add_argument("--server", default="127.0.0.1", help="VPN Server host/URL (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8888, help="VPN Server port (default: 8888)")
    parser.add_argument("--mode", default="dh16", choices=["dh16", "dh2048", "mlkem"],
                        help="Key exchange mode: dh16 (Shor Demo), dh2048 (Prod), or mlkem (Quantum-Safe)")
    parser.add_argument("--socks-port", type=int, default=1080, help="Local SOCKS5 proxy port (default: 1080)")
    args = parser.parse_args()

    client = VPNClient(args.server, args.port, mode=args.mode, socks_port=args.socks_port)
    client.start()
