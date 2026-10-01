"""
quantum_eavesdropper.py - Quantum Attack & Real-Time Traffic Interceptor.

Demonstrates:
1. Passive interception of the VPN handshake on the wire.
2. Breaking classical 16-bit Diffie-Hellman via Shor's Algorithm (QFT period-finding).
3. Reconstructing the shared secret K and deriving the exact AES-256 session key.
4. Live-decrypting all passing tunnel traffic (including Netflix destinations, HTTP/TLS requests).
5. Demonstrating failure when the VPN runs in Post-Quantum ML-KEM mode.
"""

import sys
import os
import socket
import threading
import argparse
import struct
import time
from typing import Optional

from vpn_crypto import (
    derive_session_keys,
    decrypt_payload,
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
    MSG_TUNNEL_CONNECT,
    MSG_TUNNEL_CONNECTED,
    MSG_TUNNEL_DATA,
    MSG_TUNNEL_CLOSE,
    MODE_DH_16,
    MODE_DH_2048,
    MODE_MLKEM_768,
)
from shor_engine import ShorDiscreteLogEngine


class QuantumEavesdropper:
    def __init__(self, listen_port: int, target_server_host: str, target_server_port: int):
        self.listen_port = listen_port
        self.target_host = target_server_host
        self.target_port = target_server_port

        self.mode: Optional[int] = None
        self.client_pub: Optional[int] = None
        self.server_pub: Optional[int] = None
        self.recovered_private_key: Optional[int] = None
        self.recovered_aes_key: Optional[bytes] = None
        self.recovered_iv_salt: Optional[bytes] = None

    def start(self):
        import signal
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

        tap_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tap_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tap_sock.bind(("0.0.0.0", self.listen_port))
        tap_sock.listen(16)
        tap_sock.settimeout(0.5)  # Enables immediate Ctrl+C response on Windows

        print("=" * 80)
        print("     QUANTUM EAVESDROPPER & SHOR ATTACK DEMONSTRATION ENGINE")
        print("=" * 80)
        print(f"[*] Interceptor listening on 0.0.0.0:{self.listen_port}")
        print(f"[*] Forwarding traffic to genuine VPN Server at {self.target_host}:{self.target_port}")
        print("[*] Sniffing handshake packets and live tunnel payloads...")
        print("=" * 80)

        try:
            while True:
                try:
                    client_sock, client_addr = tap_sock.accept()
                except (socket.timeout, TimeoutError):
                    continue
                print(f"\n[+] Intercepted new connection from client {client_addr[0]}:{client_addr[1]}")
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock.connect((self.target_host, self.target_port))

                # Handle bidirectional sniffing
                t = threading.Thread(target=self._bridge_connection, args=(client_sock, server_sock), daemon=True)
                t.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n[*] Stopping Quantum Eavesdropper.")
        finally:
            tap_sock.close()

    def _bridge_connection(self, client_sock: socket.socket, server_sock: socket.socket):
        # 1. Intercept Client Hello
        client_hello = recv_packet(client_sock)
        if not client_hello:
            return
        send_packet(server_sock, client_hello)

        # 2. Intercept Server Hello
        server_hello = recv_packet(server_sock)
        if not server_hello:
            return
        send_packet(client_sock, server_hello)

        # 3. Analyze Handshake
        self._analyze_and_attack_handshake(client_hello, server_hello)

        # 4. Spawn traffic forwarders with live decryption inspector
        c2s = threading.Thread(target=self._forward_client_to_server, args=(client_sock, server_sock), daemon=True)
        s2c = threading.Thread(target=self._forward_server_to_client, args=(server_sock, client_sock), daemon=True)
        c2s.start()
        s2c.start()
        c2s.join()
        s2c.join()

    def _analyze_and_attack_handshake(self, c_pkt: VPNPacket, s_pkt: VPNPacket):
        self.mode = c_pkt.stream_id

        print("\n" + "#" * 80)
        print("  STEP 1 & 2: PASSIVE WIRE INTERCEPTION OF VPN HANDSHAKE")
        print("#" * 80)

        if self.mode == MODE_DH_16:
            self.client_pub = int.from_bytes(c_pkt.payload, 'big')
            self.server_pub = int.from_bytes(s_pkt.payload, 'big')
            p = DEMO_PRIME_16
            g = DEMO_GEN_16

            print(f"[!] INTERCEPTED 16-BIT DIFFIE-HELLMAN HANDSHAKE:")
            print(f"    - Modulus p: {p} (16-bit prime)")
            print(f"    - Generator g: {g}")
            print(f"    - Client Public Key A (g^a mod p): {self.client_pub}")
            print(f"    - Server Public Key B (g^b mod p): {self.server_pub}")
            print("-" * 80)

            print("  STEP 3: EXECUTING SHOR'S QUANTUM PERIOD-FINDING ATTACK")
            print("-" * 80)
            print("[*] Formulating 2D Periodic Quantum State: f(x1, x2) = g^x1 * A^-x2 mod p")
            print("[*] Initializing quantum superposition across 2 input registers...")
            print("[*] Executing quantum modular exponentiation circuit...")
            print("[*] Applying 2D Inverse Quantum Fourier Transform (QFT†)...")

            # Run Shor Solver
            rec_a, stats = ShorDiscreteLogEngine.shor_solve_16bit(p, g, self.client_pub)
            self.recovered_private_key = rec_a

            print(f"[*] Constructive Interference Peak Detected! Measured QFT frequencies: {stats['simulated_qft_frequencies']}")
            print(f"[*] Solving modular relation: a = -y2 * y1^-1 mod r...")
            print(f"[!!!] QUANTUM BREAKTHROUGH: Recovered Client Private Key a = {self.recovered_private_key} (in {stats['elapsed_seconds']:.4f}s)")

            # Reconstruct Shared Secret
            recovered_secret = pow(self.server_pub, self.recovered_private_key, p)
            print(f"[*] Reconstructing Shared Secret: K = B^a mod p = {self.server_pub}^{self.recovered_private_key} mod {p}")
            print(f"[+] Recovered Shared Secret K = {recovered_secret}")

            # Derive AES Keys
            self.recovered_aes_key, self.recovered_iv_salt = derive_session_keys(recovered_secret)
            print(f"[+] Reconstructed AES-256 Session Key: {self.recovered_aes_key.hex()[:32]}...")
            print(f"[+] Reconstructed IV Salt:            {self.recovered_iv_salt.hex()}")
            print("=" * 80)
            print("  STEP 4: LIVE TRAFFIC DECRYPTION ACTIVE (VPN IS COMPROMISED!)")
            print("=" * 80 + "\n")

        elif self.mode == MODE_DH_2048:
            print(f"[!] INTERCEPTED 2048-BIT DIFFIE-HELLMAN HANDSHAKE.")
            print("[*] Computing physical quantum hardware resource requirements for Shor's attack:")
            res = ShorDiscreteLogEngine.quantum_resource_estimate(2048)
            print(f"    - Logical Qubits Needed:             {res['logical_qubits']}")
            print(f"    - Physical Qubits (Surface Code):    {res['physical_qubits_surface_code']}")
            print(f"    - Quantum T-Gate Operations:         {res['t_gate_count']:,}")
            print(f"    - Quantum Circuit Depth:             {res['circuit_depth']:,}")
            print(f"    - Estimated Quantum Decryption Time: {res['estimated_quantum_runtime_hrs']:.2f} hours")
            print("[!] STATUS: 'Harvest Now, Decrypt Later' (HNDL) captured handshake stored for Q-Day.\n")

        elif self.mode == MODE_MLKEM_768:
            print(f"[!] INTERCEPTED NIST FIPS 203 (ML-KEM-768 / Kyber) HANDSHAKE.")
            print("[*] Attempting Shor's Algorithm against ML-KEM Ciphertext...")
            test_res = ShorDiscreteLogEngine.test_mlkem_immunity()
            print(f"    - Hardness Foundation: {test_res['lattice_hardness_basis']}")
            print(f"    - Period Detected:     {test_res['shor_period_detected']}")
            print(f"    - Peak-to-Average:     {test_res['quantum_fourier_peak_to_average']} (Uniform Random Noise)")
            print(f"[!] RESULT: {test_res['security_assessment']}")
            print("[!] STATUS: Attacker is BLIND. Traffic remains 100% encrypted and quantum-safe!\n")

    def _forward_client_to_server(self, client_sock: socket.socket, server_sock: socket.socket):
        try:
            while True:
                pkt = recv_packet(client_sock)
                if not pkt:
                    break

                # If we cracked the AES key, inspect the payload!
                if self.recovered_aes_key:
                    self._inspect_packet("Client -> Server", pkt)

                send_packet(server_sock, pkt)
        except Exception:
            pass

    def _forward_server_to_client(self, server_sock: socket.socket, client_sock: socket.socket):
        try:
            while True:
                pkt = recv_packet(server_sock)
                if not pkt:
                    break

                if self.recovered_aes_key:
                    self._inspect_packet("Server -> Client", pkt)

                send_packet(client_sock, pkt)
        except Exception:
            pass

    def _inspect_packet(self, direction: str, pkt: VPNPacket):
        try:
            plain = decrypt_payload(self.recovered_aes_key, pkt.nonce, pkt.payload)

            if pkt.msg_type == MSG_TUNNEL_CONNECT:
                host_len = struct.unpack_from("!H", plain, 0)[0]
                host = plain[2:2 + host_len].decode('utf-8', errors='ignore')
                port = struct.unpack_from("!H", plain, 2 + host_len)[0]
                print(f"\n[!!! EXPOSED BY QUANTUM ATTACK !!!] {direction} | Stream #{pkt.stream_id}")
                print(f"    TARGET DESTINATION:  {host}:{port}")
                if "netflix" in host.lower():
                    print("    >>> [ALERT] TARGET DETECTED: USER IS STREAMING NETFLIX! <<<")
                print("-" * 60)

            elif pkt.msg_type == MSG_TUNNEL_DATA:
                # Check for HTTP/TLS signatures
                preview = plain[:128]
                info = ""
                if b"HTTP" in preview or b"GET " in preview or b"POST " in preview or b"Host:" in preview:
                    lines = preview.split(b"\r\n")
                    first_line = lines[0].decode('utf-8', errors='ignore')
                    info = f"HTTP Request: {first_line}"
                elif b"netflix" in plain.lower():
                    info = "Netflix Encrypted Stream Metadata Intercepted!"
                elif len(preview) >= 3 and preview[0] == 0x16 and preview[1] == 0x03:
                    # TLS Client Hello / Server Hello
                    info = "TLS Handshake Packet (SNI / Cert exchange captured)"
                else:
                    info = f"Raw Data [{len(plain)} bytes]: {preview[:32].hex()}..."

                print(f"[LIVE DECRYPTED TRAFFIC] {direction} (Stream #{pkt.stream_id}): {info}")

        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Eavesdropper & Shor Attack Demonstrator")
    parser.add_argument("--listen-port", type=int, default=8889, help="Port to listen for client connections (default: 8889)")
    parser.add_argument("--server-host", default="127.0.0.1", help="Target VPN server host (default: 127.0.0.1)")
    parser.add_argument("--server-port", type=int, default=8888, help="Target VPN server port (default: 8888)")
    args = parser.parse_args()

    eavesdropper = QuantumEavesdropper(args.listen_port, args.server_host, args.server_port)
    eavesdropper.start()
