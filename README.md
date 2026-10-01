# Quantum-Safe VPN vs. Shor's Algorithm Attack Testbed

A complete, zero-dependency custom VPN implementation built from first principles (no WireGuard, no OpenVPN, no third-party tunneling suites).

This project demonstrates:
1. **Classical VPN Vulnerability**: How classical Diffie-Hellman handshakes (16-bit to 2048-bit) are fundamentally vulnerable to **Shor's Algorithm** via Quantum Fourier Transform (QFT) period finding.
2. **Real-Time Traffic Interception**: A passive eavesdropper sniffs the handshake, runs Shor's algorithm, recovers the private key, reconstructs the AES-256 session key, and **decrypts live VPN traffic** (e.g., Netflix requests, HTTP/TLS headers).
3. **Quantum-Safe Defense**: Migration to **NIST FIPS 203 ML-KEM (Kyber-768)** lattice-based key encapsulation, proving mathematical immunity against Shor's algorithm.
4. **Zero-Dependency Traffic Tunnel**: A high-performance multiplexed SOCKS5 proxy interface (`127.0.0.1:1080`) that routes real browser traffic (Netflix, YouTube, web browsing) through the custom encrypted tunnel.

---

## Project Structure

```
v:\QUANTUM\
├── README.md                 # System architecture, math breakdown, and usage guide
├── start_gui.bat             # 1-Click launcher for Desktop GUI app
├── quantum_vpn_gui.py        # Desktop Application (16-bit/ML-KEM toggle, attack demo, auto-proxy)
├── cloud_server.py           # Multi-device Cloud Gateway (Web Portal, PAC Auto-Proxy, WSS Tunnel)
├── vpn_crypto.py             # Classical DH (16/2048-bit), HKDF-SHA256, AES-256-GCM, NIST ML-KEM-768
├── vpn_protocol.py           # Custom binary packet framing and serialization
├── vpn_server.py             # Remote VPN server gateway / internet exit node
├── vpn_client.py             # Local VPN client with built-in SOCKS5 proxy (127.0.0.1:1080)
├── shor_engine.py            # Quantum circuit simulator, QFT period-finding solver, and resource estimator
├── quantum_eavesdropper.py   # Sniffer and live quantum attack engine
└── test_pipeline.py          # Automated verification script demonstrating attack and defense
```

---

## 🚀 1-Click Desktop App (For You & Friends on Laptops)

You can launch the full graphical interface simply by double-clicking:

```bash
start_gui.bat
```
*(or running `python quantum_vpn_gui.py`)*

### Features in the App:
1. **Mode Toggle**:
   - 🔴 **16-Bit Classical DH**: *Demonstration mode (vulnerable to Shor's algorithm)*.
   - 🛡️ **Post-Quantum ML-KEM-768**: *NIST FIPS 203 lattice encryption (immune)*.
   - 🔵 **2048-Bit Classical DH**: *RFC 3526 MODP production classical standard*.
2. **1-Click Connect with Auto-Proxy**:
   - Checking *"Auto-route Windows System"* automatically configures Windows settings so **Edge, Chrome, and the Netflix App** route through the VPN immediately.
3. **Live Quantum Attack & Decryption Demo**:
   - Click **`[ ⚛️ RUN SHOR QUANTUM ATTACK ]`** anytime to simulate an eavesdropper sniffing the active tunnel mode, executing Shor's algorithm, and showing live decrypted traffic or proof of lattice immunity!

---

## 📱 Connecting from Phones (iPhone / Android) - Zero-Install

Friends on mobile devices do **not** need to install any app:
1. Open the Codespace URL in their phone browser: `https://<YOUR-CODESPACE>-8888.app.github.dev/`
2. They will see the **Quantum VPN Mobile Web Portal** with the live attack demo.
3. Tap **"Copy"** on the Proxy link (`https://.../proxy.pac`).
4. **iPhone**: Go to `Settings -> Wi-Fi -> (i) -> Configure Proxy -> Automatic -> Paste Link`.
5. **Android**: Go to `Settings -> Wi-Fi -> Network Details -> Proxy -> Auto-config -> Paste Link`.
6. Done! All their phone traffic is encrypted and tunneled over port 443!

---

## Quick Start: Automated Verification

To run the complete automated test showing the classical break vs. quantum-safe defense in action:

```bash
python test_pipeline.py
```

This will:
* Simulate the 16-bit DH handshake on the wire.
* Launch Shor's algorithm to recover client secret exponent $a$ in $< 1$ millisecond.
* Reconstruct the AES-256 session key.
* Decrypt an intercepted live Netflix request in plaintext.
* Upgrade to NIST ML-KEM-768 and demonstrate how Shor's algorithm encounters uniform lattice noise and fails completely.

---

## Running the Live VPN & Quantum Eavesdropper

### Step 1: Start the VPN Server
Run this on your server (or on a cloud VPS to bypass local Wi-Fi blocks):
```bash
# Classical 16-bit mode (Shor Demonstration Mode)
python vpn_server.py --port 8888
```

### Step 2: Start the Quantum Eavesdropper (Tap / Interceptor)
The eavesdropper acts as a passive network tap between the client and server:
```bash
python quantum_eavesdropper.py --listen-port 8889 --server-host 127.0.0.1 --server-port 8888
```

### Step 3: Connect the VPN Client
Connect the client through the eavesdropper port (`8889`):
```bash
python vpn_client.py --server 127.0.0.1 --port 8889 --mode dh16 --socks-port 1080
```

### Step 4: Route Real Traffic (Netflix / Web Browsing)
The client automatically starts a local SOCKS5 proxy on `127.0.0.1:1080`.
You can now route any browser or application traffic through it:

* **In Command Line (Curl)**:
  ```bash
  curl --socks5 127.0.0.1:1080 https://www.netflix.com
  ```
* **In Firefox / Chrome / Edge**:
  1. Open Network Settings -> Proxy Settings.
  2. Select **Manual Proxy Configuration**.
  3. Set **SOCKS Host** to `127.0.0.1` and Port to `1080` (Check "Proxy DNS when using SOCKS v5").
  4. Browse to `https://www.netflix.com`.

### Step 5: Observe the Breach in the Eavesdropper Terminal
Watch the `quantum_eavesdropper.py` terminal:
1. It intercepts the client public key $A$ and server public key $B$.
2. It runs Shor's 2D period-finding algorithm and outputs:
   ```
   [!!!] QUANTUM BREAKTHROUGH: Recovered Client Private Key a = 55355
   [+] Reconstructed AES-256 Session Key: 26aa2041e509b90ce2fd7d38f3fabe26...
   ```
3. As you browse Netflix in your browser, the attacker terminal live-decrypts the traffic:
   ```
   [!!! EXPOSED BY QUANTUM ATTACK !!!] Client -> Server | Stream #1001
       TARGET DESTINATION:  netflix.com:443
       >>> [ALERT] TARGET DETECTED: USER IS STREAMING NETFLIX! <<<
   ```

---

## Switching to Quantum-Safe Mode (NIST FIPS 203 ML-KEM)

Restart the client with `--mode mlkem`:
```bash
python vpn_client.py --server 127.0.0.1 --port 8889 --mode mlkem --socks-port 1080
```

* The VPN will now negotiate keys using **Module Learning With Errors (M-LWE)** over polynomial rings $R_q = \mathbb{Z}_{3329}[X]/(X^{256} + 1)$.
* The Quantum Eavesdropper attempts Shor's period-finding and outputs:
  ```
  [!] RESULT: IMMUNE: Shor's algorithm provides zero speedup over lattice reduction.
  [!] STATUS: Attacker is BLIND. Traffic remains 100% encrypted and quantum-safe!
  ```

---

## Hosting the VPN Server on Cloud Free Tier (To Unblock Netflix)

To bypass Wi-Fi filters completely, deploy `vpn_server.py` on any cloud free tier:

1. **AWS EC2 (Free Tier)** / **Oracle Cloud (Always Free)**:
   * Launch an Ubuntu / Debian instance.
   * Open inbound port `8888` in your Cloud Security Group / Firewall.
   * Clone/copy `v:\QUANTUM` files to the instance.
   * Run:
     ```bash
     python3 vpn_server.py --port 8888
     ```
2. **On your local machine**:
   * Run:
     ```bash
     python vpn_client.py --server <YOUR_CLOUD_PUBLIC_IP> --port 8888 --mode dh16
     ```
   * Set your browser SOCKS5 proxy to `127.0.0.1:1080`.
   * All Netflix traffic is now encrypted past your local Wi-Fi filter and exits freely from your cloud server!

---

## Mathematical Breakdown of the Quantum Break

### Why Classical DH is Vulnerable:
Diffie-Hellman relies on the **Discrete Logarithm Problem (DLP)**:
$$A \equiv g^a \pmod p$$
Shor's algorithm defines the 2-dimensional periodic function:
$$f(x_1, x_2) = g^{x_1} A^{-x_2} \equiv g^{x_1 - a \cdot x_2} \pmod p$$
Applying the 2D Quantum Fourier Transform ($\text{QFT}^\dagger$) to input registers in superposition concentrates amplitude on frequencies $(y_1, y_2)$ satisfying:
$$y_1 \cdot a + y_2 \equiv 0 \pmod r$$
Solving the modular linear congruence yields the private key:
$$a \equiv -y_2 \cdot y_1^{-1} \pmod r$$

### Why ML-KEM is Quantum-Safe:
ML-KEM uses lattice vectors with random binomial error $\mathbf{e}$:
$$\mathbf{b} = \mathbf{A} \cdot \mathbf{s} + \mathbf{e} \pmod q$$
Because of the error vector $\mathbf{e}$, there is **no periodic group structure**. The QFT produces uniform random noise, yielding zero constructive interference and neutralizing Shor's algorithm completely.
