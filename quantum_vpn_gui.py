"""
quantum_vpn_gui.py - Modern Desktop GUI for Quantum-Safe VPN & Shor's Algorithm Testbed.
Features:
1. Mode Toggle: 16-bit (Shor Vulnerable), NIST ML-KEM-768 (Quantum-Safe), and 2048-bit (Production).
2. 1-Click Connect with Automatic Windows System Proxy Routing.
3. Interactive Live Quantum Attack & Decryption Demo with Real-Time Cryptanalysis Visualization.
4. Live Activity Log and Traffic Stats.
"""

import sys
import os
import time
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Import core modules from local project
from vpn_crypto import (
    DiffieHellman,
    derive_session_keys,
    encrypt_payload,
    decrypt_payload,
    MLKEM768,
    DEMO_PRIME_16,
    DEMO_GEN_16,
)
from shor_engine import ShorDiscreteLogEngine
from vpn_client import VPNClient, set_windows_system_proxy
from vpn_protocol import (
    VPNPacket,
    MSG_CLIENT_HELLO,
    MSG_SERVER_HELLO,
    MODE_DH_16,
    MODE_DH_2048,
    MODE_MLKEM_768,
)


class QuantumVPNGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Quantum-Safe VPN vs. Shor's Algorithm Testbed")
        self.root.geometry("980x840")
        self.root.minsize(880, 720)
        self.root.configure(bg="#0d1117")

        # Application State
        self.client: VPNClient = None
        self.is_connected = False
        self.is_attack_running = False
        self.auto_proxy_enabled = tk.BooleanVar(value=True)
        self.mode_var = tk.StringVar(value="dh16")  # "dh16", "mlkem", "dh2048"

        # Theme Colors
        self.c_bg = "#0d1117"
        self.c_card = "#161b22"
        self.c_card_border = "#30363d"
        self.c_text = "#f0f6fc"
        self.c_muted = "#8b949e"
        self.c_cyan = "#38bdf8"
        self.c_blue = "#58a6ff"
        self.c_green = "#238636"
        self.c_green_bright = "#3fb950"
        self.c_red = "#da3633"
        self.c_red_bright = "#f85149"
        self.c_amber = "#d29922"
        self.c_terminal_bg = "#030712"

        self._setup_styles()
        self._build_ui()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.c_bg)
        style.configure("Card.TFrame", background=self.c_card, relief="flat")
        style.configure("TLabel", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=self.c_card, foreground=self.c_text, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.c_bg, foreground=self.c_cyan, font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=self.c_bg, foreground=self.c_muted, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=self.c_card, foreground=self.c_cyan, font=("Segoe UI", 12, "bold"))
        style.configure("Status.TLabel", background=self.c_card, foreground=self.c_muted, font=("Segoe UI", 11, "bold"))
        style.configure("TCheckbutton", background=self.c_card, foreground=self.c_text, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", self.c_card)], foreground=[("active", self.c_cyan)])

    def _build_ui(self):
        # Main container with scrolling or responsive packing
        main_frame = tk.Frame(self.root, bg=self.c_bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # ----------------------------------------------------------------------
        # Top Header Banner
        # ----------------------------------------------------------------------
        header_frame = tk.Frame(main_frame, bg=self.c_bg)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_lbl = tk.Label(
            header_frame,
            text="⚛️ QUANTUM-SAFE VPN APP",
            font=("Segoe UI", 18, "bold"),
            fg=self.c_cyan,
            bg=self.c_bg
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame,
            text="Zero-Dependency SOCKS5 Tunnel • Shor's Algorithm Attack Testbed • NIST FIPS 203 ML-KEM-768",
            font=("Segoe UI", 9),
            fg=self.c_muted,
            bg=self.c_bg
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # ----------------------------------------------------------------------
        # CARD 1: Connection & Mode Toggle Card
        # ----------------------------------------------------------------------
        card1 = tk.Frame(main_frame, bg=self.c_card, bd=1, relief="solid", highlightbackground=self.c_card_border)
        card1.pack(fill=tk.X, pady=(0, 15), ipady=10)

        c1_top = tk.Frame(card1, bg=self.c_card)
        c1_top.pack(fill=tk.X, padx=15, pady=(5, 10))

        tk.Label(c1_top, text="🌐 VPN TUNNEL CONFIGURATION & CRYPTOGRAPHIC MODE", font=("Segoe UI", 11, "bold"), fg=self.c_cyan, bg=self.c_card).pack(side=tk.LEFT)

        # Server input row
        server_row = tk.Frame(card1, bg=self.c_card)
        server_row.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(server_row, text="Server Endpoint:", font=("Segoe UI", 10), fg=self.c_text, bg=self.c_card).pack(side=tk.LEFT)
        self.server_entry = tk.Entry(server_row, font=("Consolas", 10), bg="#090d16", fg=self.c_text, insertbackground=self.c_text, bd=1, relief="solid")
        self.server_entry.insert(0, "glorious-engine-v6v59w4wjg773w9vv-8888.app.github.dev")
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))

        reset_btn = tk.Button(
            server_row, text="Localhost (8888)", font=("Segoe UI", 8),
            bg="#21262d", fg=self.c_muted, activebackground="#30363d", activeforeground=self.c_text,
            relief="flat", bd=0, padx=6, pady=2,
            command=lambda: self._set_server_preset("127.0.0.1:8888")
        )
        reset_btn.pack(side=tk.LEFT)

        cloud_btn = tk.Button(
            server_row, text="Codespaces Cloud", font=("Segoe UI", 8),
            bg="#21262d", fg=self.c_cyan, activebackground="#30363d", activeforeground=self.c_text,
            relief="flat", bd=0, padx=6, pady=2,
            command=lambda: self._set_server_preset("glorious-engine-v6v59w4wjg773w9vv-8888.app.github.dev")
        )
        cloud_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Mode Selection Row (Toggle)
        mode_frame = tk.Frame(card1, bg=self.c_card)
        mode_frame.pack(fill=tk.X, padx=15, pady=(5, 10))

        tk.Label(mode_frame, text="Security Mode:", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_card).pack(anchor="w", pady=(0, 5))

        opts_frame = tk.Frame(mode_frame, bg=self.c_card)
        opts_frame.pack(fill=tk.X)

        # Radio option 1: 16-bit
        r1 = tk.Radiobutton(
            opts_frame,
            text="🔴 16-Bit Classical DH  (Shor Vulnerable - Demo Mode)",
            variable=self.mode_var,
            value="dh16",
            font=("Segoe UI", 10, "bold"),
            fg=self.c_red_bright,
            bg=self.c_card,
            selectcolor="#21262d",
            activebackground=self.c_card,
            activeforeground=self.c_red_bright,
            command=self._on_mode_change
        )
        r1.pack(anchor="w", pady=2)

        # Radio option 2: ML-KEM-768
        r2 = tk.Radiobutton(
            opts_frame,
            text="🛡️ Post-Quantum ML-KEM-768  (NIST FIPS 203 Lattice - Immune)",
            variable=self.mode_var,
            value="mlkem",
            font=("Segoe UI", 10, "bold"),
            fg=self.c_green_bright,
            bg=self.c_card,
            selectcolor="#21262d",
            activebackground=self.c_card,
            activeforeground=self.c_green_bright,
            command=self._on_mode_change
        )
        r2.pack(anchor="w", pady=2)

        # Radio option 3: 2048-bit
        r3 = tk.Radiobutton(
            opts_frame,
            text="🔵 2048-Bit Classical DH  (RFC 3526 MODP - Production Standard)",
            variable=self.mode_var,
            value="dh2048",
            font=("Segoe UI", 10),
            fg=self.c_blue,
            bg=self.c_card,
            selectcolor="#21262d",
            activebackground=self.c_card,
            activeforeground=self.c_blue,
            command=self._on_mode_change
        )
        r3.pack(anchor="w", pady=2)

        # Action and status row
        action_row = tk.Frame(card1, bg=self.c_card)
        action_row.pack(fill=tk.X, padx=15, pady=(10, 5))

        self.connect_btn = tk.Button(
            action_row,
            text="⚡ CONNECT VPN TUNNEL",
            font=("Segoe UI", 11, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._toggle_connection
        )
        self.connect_btn.pack(side=tk.LEFT)

        # Windows Proxy Checkbox
        proxy_cb = tk.Checkbutton(
            action_row,
            text="Auto-route Windows System (Edge, Chrome, Netflix App)",
            variable=self.auto_proxy_enabled,
            font=("Segoe UI", 9),
            fg=self.c_text,
            bg=self.c_card,
            selectcolor="#21262d",
            activebackground=self.c_card,
            activeforeground=self.c_cyan
        )
        proxy_cb.pack(side=tk.LEFT, padx=(15, 0))

        # Status badge on right
        self.status_lbl = tk.Label(
            action_row,
            text="● DISCONNECTED",
            font=("Segoe UI", 10, "bold"),
            fg=self.c_muted,
            bg=self.c_card
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=5)

        # ----------------------------------------------------------------------
        # CARD 2: Interactive Quantum Shor Attack & Interception Demo
        # ----------------------------------------------------------------------
        card2 = tk.Frame(main_frame, bg=self.c_card, bd=1, relief="solid", highlightbackground=self.c_card_border)
        card2.pack(fill=tk.X, pady=(0, 15), ipady=8)

        c2_top = tk.Frame(card2, bg=self.c_card)
        c2_top.pack(fill=tk.X, padx=15, pady=(5, 5))

        tk.Label(c2_top, text="🎯 LIVE QUANTUM ATTACK & DECRYPTION DEMO", font=("Segoe UI", 11, "bold"), fg=self.c_cyan, bg=self.c_card).pack(side=tk.LEFT)

        self.demo_run_btn = tk.Button(
            c2_top,
            text="⚛️ RUN SHOR QUANTUM ATTACK",
            font=("Segoe UI", 10, "bold"),
            bg="#8957e5",
            fg="#ffffff",
            activebackground="#a371f7",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._trigger_demo_attack
        )
        self.demo_run_btn.pack(side=tk.RIGHT)

        demo_desc = tk.Label(
            card2,
            text="Simulates an eavesdropper equipped with a quantum computer executing Shor's 2D period-finding algorithm on the active tunnel mode.",
            font=("Segoe UI", 9),
            fg=self.c_muted,
            bg=self.c_card,
            wraplength=900,
            justify="left"
        )
        demo_desc.pack(anchor="w", padx=15, pady=(0, 8))

        # Visual attack results display box
        self.demo_box = scrolledtext.ScrolledText(
            card2,
            height=8,
            bg=self.c_terminal_bg,
            fg="#c9d1d9",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            bd=1,
            relief="solid",
            wrap="word"
        )
        self.demo_box.pack(fill=tk.X, padx=15, pady=(0, 5))
        self._init_demo_display()

        # ----------------------------------------------------------------------
        # CARD 3: Activity Log & Terminal
        # ----------------------------------------------------------------------
        card3 = tk.Frame(main_frame, bg=self.c_card, bd=1, relief="solid", highlightbackground=self.c_card_border)
        card3.pack(fill=tk.BOTH, expand=True, ipady=5)

        c3_top = tk.Frame(card3, bg=self.c_card)
        c3_top.pack(fill=tk.X, padx=15, pady=(5, 5))

        tk.Label(c3_top, text="📋 SYSTEM ACTIVITY & TUNNEL TELEMETRY", font=("Segoe UI", 11, "bold"), fg=self.c_cyan, bg=self.c_card).pack(side=tk.LEFT)

        clear_btn = tk.Button(
            c3_top, text="Clear Log", font=("Segoe UI", 8),
            bg="#21262d", fg=self.c_muted, activebackground="#30363d", activeforeground=self.c_text,
            relief="flat", bd=0, padx=6, pady=2,
            command=self._clear_log
        )
        clear_btn.pack(side=tk.RIGHT)

        self.log_box = scrolledtext.ScrolledText(
            card3,
            bg=self.c_terminal_bg,
            fg="#c9d1d9",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            bd=1,
            relief="solid"
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # Initial greeting in log
        self.log("[SYSTEM] Quantum-Safe VPN Interface Initialized.")
        self.log("[MODE] Selected: 16-Bit Classical DH (Shor Vulnerable Demonstration Mode)")
        self.log("[INFO] Ready to establish encrypted tunnel or run quantum attack simulation.")

    def _set_server_preset(self, host_port: str):
        self.server_entry.delete(0, tk.END)
        self.server_entry.insert(0, host_port)

    def _on_mode_change(self):
        m = self.mode_var.get()
        if m == "dh16":
            self.log("[MODE CHANGED] 🔴 Switched to 16-Bit Classical DH (Shor Vulnerable Demo)")
        elif m == "mlkem":
            self.log("[MODE CHANGED] 🛡️ Switched to NIST FIPS 203 ML-KEM-768 (Quantum-Safe Lattice)")
        elif m == "dh2048":
            self.log("[MODE CHANGED] 🔵 Switched to 2048-Bit Classical DH (RFC 3526 Production)")

    def log(self, text: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_box.see(tk.END)

    def _clear_log(self):
        self.log_box.delete("1.0", tk.END)

    def _init_demo_display(self):
        self.demo_box.delete("1.0", tk.END)
        self.demo_box.insert(tk.END, ">>> Quantum Attack Inspector Ready.\n")
        self.demo_box.insert(tk.END, ">>> Select a security mode above and click [RUN SHOR QUANTUM ATTACK] to simulate.\n")

    # --------------------------------------------------------------------------
    # VPN Tunnel Connection Logic
    # --------------------------------------------------------------------------
    def _toggle_connection(self):
        if not self.is_connected:
            self._connect_vpn()
        else:
            self._disconnect_vpn()

    def _connect_vpn(self):
        endpoint = self.server_entry.get().strip()
        if not endpoint:
            messagebox.showerror("Error", "Please enter a valid VPN Server endpoint.")
            return

        mode = self.mode_var.get()
        self.connect_btn.config(text="CONNECTING...", state="disabled", bg="#6e7681")
        self.status_lbl.config(text="● CONNECTING...", fg=self.c_amber)
        self.log(f"[*] Starting connection to {endpoint} with mode '{mode}'...")

        self.client = VPNClient(server_host=endpoint, mode=mode, socks_port=1080)
        self.client.log_callback = lambda msg: self.root.after(0, lambda: self.log(msg))

        def _on_success():
            self.root.after(0, self._handle_connected)

        def _on_error(err):
            self.root.after(0, lambda: self._handle_connect_failed(err))

        self.client.start_async(on_connected=_on_success, on_error=_on_error)

    def _handle_connected(self):
        self.is_connected = True
        self.connect_btn.config(text="⏹ DISCONNECT TUNNEL", state="normal", bg=self.c_red, activebackground="#f85149")
        self.status_lbl.config(text="● TUNNEL ACTIVE (AES-256)", fg=self.c_green_bright)
        self.log("[+] Tunnel online! Local SOCKS5 active on 127.0.0.1:1080.")

        if self.auto_proxy_enabled.get():
            ok = set_windows_system_proxy(True, host="127.0.0.1", port=1080)
            if ok:
                self.log("[+] Windows System Proxy enabled: Edge, Chrome, and Netflix automatically routed!")
            else:
                self.log("[-] Windows System Proxy could not be auto-configured. Set proxy manually in browser.")

    def _handle_connect_failed(self, err):
        self.is_connected = False
        self.connect_btn.config(text="⚡ CONNECT VPN TUNNEL", state="normal", bg="#1f6feb", activebackground="#388bfd")
        self.status_lbl.config(text="● FAILED", fg=self.c_red_bright)
        self.log(f"[-] Connection failed: {err}")
        messagebox.showerror("Connection Error", f"Failed to connect to VPN Server:\n{err}\n\nMake sure cloud_server.py is running on Codespaces or local server is active.")

    def _disconnect_vpn(self):
        self.log("[*] Disconnecting tunnel...")
        if self.auto_proxy_enabled.get():
            set_windows_system_proxy(False)
            self.log("[+] Windows System Proxy cleared.")

        if self.client:
            self.client.stop()
            self.client = None

        self.is_connected = False
        self.connect_btn.config(text="⚡ CONNECT VPN TUNNEL", state="normal", bg="#1f6feb", activebackground="#388bfd")
        self.status_lbl.config(text="● DISCONNECTED", fg=self.c_muted)
        self.log("[*] Tunnel disconnected.")

    # --------------------------------------------------------------------------
    # Interactive Quantum Attack Demo
    # --------------------------------------------------------------------------
    def _trigger_demo_attack(self):
        if self.is_attack_running:
            return

        self.is_attack_running = True
        self.demo_run_btn.config(state="disabled", text="ATTACKING...", bg="#6e7681")
        mode = self.mode_var.get()

        t = threading.Thread(target=self._run_attack_simulation, args=(mode,), daemon=True)
        t.start()

    def _run_attack_simulation(self, mode: str):
        def _append(msg: str):
            self.root.after(0, lambda: self._append_demo_text(msg))

        self.root.after(0, lambda: self.demo_box.delete("1.0", tk.END))

        if mode == "dh16":
            _append("=" * 70)
            _append(" [ATTACK SCENARIO: 16-BIT CLASSICAL DH HANDSHAKE INTERCEPTED]")
            _append("=" * 70)
            time.sleep(0.3)

            dh_client = DiffieHellman(bits=16)
            dh_server = DiffieHellman(bits=16)
            legit_secret = dh_client.compute_shared_secret(dh_server.public_key)
            legit_aes, _ = derive_session_keys(legit_secret)

            _append(f"[*] 1. Wiretap sniffs Public Keys: A = {dh_client.public_key}, B = {dh_server.public_key}")
            _append(f"[*]    Parameters: Modulus p = {dh_client.p}, Generator g = {dh_client.g}")
            _append(f"[*]    Secret Exponent a (HIDDEN): {dh_client.private_key}")
            time.sleep(0.4)

            _append("\n[*] 2. Initializing Shor's Quantum Period-Finding Engine...")
            _append("       - Constructing 2D Quantum Register |x1> |x2> in equal superposition")
            _append("       - Evaluating modular function f(x1, x2) = g^x1 * A^(-x2) mod p")
            _append("       - Applying 2D Inverse Quantum Fourier Transform (QFT dagger)...")
            time.sleep(0.5)

            recovered_a, stats = ShorDiscreteLogEngine.shor_solve_16bit(dh_client.p, dh_client.g, dh_client.public_key)

            _append(f"\n[!!!] QUANTUM STATE COLLAPSED: Measured Order r = {stats['group_order_r']}")
            _append(f"[!!!] DISCRETE LOGARITHM CRACKED: Recovered Private Exponent a = {recovered_a}")
            _append(f"      Execution time: {stats['elapsed_seconds'] * 1000:.2f} milliseconds!")
            time.sleep(0.4)

            cracked_secret = pow(dh_server.public_key, recovered_a, dh_client.p)
            cracked_aes, _ = derive_session_keys(cracked_secret)
            _append(f"\n[+] Derived AES-256 Session Key: {cracked_aes.hex()[:32]}...")
            _append(f"    Match Verified: {'100% IDENTICAL TO TUNNEL KEY!' if cracked_aes == legit_aes else 'MISMATCH'}")
            time.sleep(0.4)

            # Live intercepted simulated Netflix packet
            sample_netflix = b"CONNECT www.netflix.com:443 HTTP/1.1\r\nHost: www.netflix.com\r\nUser-Agent: Mozilla/5.0...\r\n\r\n"
            nonce = b"DEMO_NONCE12"
            wire_cipher = encrypt_payload(legit_aes, nonce, sample_netflix)
            decrypted = decrypt_payload(cracked_aes, nonce, wire_cipher)

            _append("\n[!!! LIVE DECRYPTED WIRE TRAFFIC BY ATTACKER !!!]")
            _append("----------------------------------------------------------------------")
            for line in decrypted.decode('utf-8', errors='ignore').strip().split('\r\n'):
                _append(f"  | {line}")
            _append("----------------------------------------------------------------------")
            _append(">>> 🚨 RESULT: TUNNEL BROKEN! Attacker sees all Netflix browsing in plaintext! <<<\n")

        elif mode == "mlkem":
            _append("=" * 70)
            _append(" [ATTACK SCENARIO: NIST FIPS 203 ML-KEM-768 (KYBER) INTERCEPTED]")
            _append("=" * 70)
            time.sleep(0.3)

            pk, sk = MLKEM768.keygen()
            ct, ss_srv = MLKEM768.encapsulate(pk)

            _append(f"[*] 1. Wiretap sniffs ML-KEM Lattice Public Key ({len(pk)} bytes)")
            _append(f"[*]    Wiretap sniffs Kyber Ciphertext ({len(ct)} bytes): {ct[:24].hex()}...")
            time.sleep(0.4)

            _append("\n[*] 2. Attacker attempts Shor's Quantum Period-Finding on Lattice Equations...")
            _append("       - Underlying Hardness: Module Learning With Errors (M-LWE)")
            _append("       - System: b = A*s + e mod 3329  over polynomial ring R_q")
            time.sleep(0.5)

            test_result = ShorDiscreteLogEngine.test_mlkem_immunity()
            _append(f"\n[!] Quantum Fourier Transform Spectrum Analysis:")
            _append(f"    - Periodic Structure:      NONE (Submerged by random error vector e)")
            _append(f"    - Fourier Peak-to-Average: {test_result['quantum_fourier_peak_to_average']} (Uniform White Noise)")
            _append(f"    - Constructive Peak:       {test_result['constructive_interference_achieved']}")
            _append(f"\n[+] {test_result['security_assessment']}")
            _append("\n>>> 🛡️ RESULT: ATTACK FAILED! Lattice noise completely blinded the quantum computer.")
            _append("    Traffic remains 100% impenetrable and quantum-safe! <<<\n")

        elif mode == "dh2048":
            _append("=" * 70)
            _append(" [ATTACK SCENARIO: 2048-BIT PRODUCTION DIFFIE-HELLMAN INTERCEPTED]")
            _append("=" * 70)
            time.sleep(0.3)

            res = ShorDiscreteLogEngine.quantum_resource_estimate(bits=2048)
            _append(f"[*] Production Parameter: RFC 3526 MODP 2048-bit Prime Group 14")
            _append(f"[*] Classical Computers: Immune (Solving takes > 10^12 years on supercomputers)")
            _append("\n[*] Quantum Resource Requirements to Execute Shor's Algorithm:")
            _append(f"    - Logical Qubits Needed:         {res['logical_qubits']:,} qubits")
            _append(f"    - Surface-Code Physical Qubits:   {res['physical_qubits_surface_code']:,} physical qubits")
            _append(f"    - Fault-Tolerant T-Gate Count:   {res['t_gate_count']:,} gates")
            _append(f"    - Quantum Circuit Depth:         {res['circuit_depth']:,} layers")
            _append(f"    - Estimated Quantum Runtime:     ~{res['estimated_quantum_runtime_hrs']:.2f} hours")
            _append("\n>>> ⚠️ RESULT: Currently secure against classical attacks, but VULNERABLE")
            _append("    to future large-scale quantum computers. Migration to ML-KEM recommended! <<<\n")

        self.root.after(0, self._finish_demo_attack)

    def _append_demo_text(self, text: str):
        self.demo_box.insert(tk.END, text + "\n")
        self.demo_box.see(tk.END)

    def _finish_demo_attack(self):
        self.is_attack_running = False
        self.demo_run_btn.config(state="normal", text="⚛️ RUN SHOR QUANTUM ATTACK", bg="#8957e5")

    def _on_close(self):
        if self.is_connected:
            if messagebox.askyesno("Exit VPN", "VPN Tunnel is currently connected. Disconnect and exit?"):
                self._disconnect_vpn()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = QuantumVPNGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
