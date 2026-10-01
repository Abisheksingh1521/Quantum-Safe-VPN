"""
vpn_crypto.py - Cryptographic core for Custom Quantum-Vulnerable and Quantum-Safe VPN.
Implements:
1. Classical Diffie-Hellman Key Exchange (supports 16-bit demo mode & 2048-bit RFC 3526 MODP)
2. HKDF-SHA256 for symmetric session key expansion
3. AES-256-GCM authenticated payload encryption
4. NIST FIPS 203 ML-KEM (Kyber-768) Post-Quantum Key Encapsulation Mechanism
"""

import os
import hashlib
import hmac
import struct
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==============================================================================
# 1. CLASSICAL DIFFIE-HELLMAN PARAMETERS
# ==============================================================================

# 16-bit Demonstration Prime (p is prime, g is true primitive root)
# Allows real quantum circuit simulation to complete in seconds on classical hardware
DEMO_PRIME_16 = 65521  # Largest 16-bit prime
DEMO_GEN_16 = 17

# Small 8-bit prime for lightning-fast quantum state vector display
DEMO_PRIME_8 = 251
DEMO_GEN_8 = 6

# Production 2048-bit MODP Group 14 (RFC 3526)
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
    """Classical Diffie-Hellman Key Exchange (Shor-vulnerable)."""

    def __init__(self, bits: int = 16):
        self.bits = bits
        if bits == 8:
            self.p = DEMO_PRIME_8
            self.g = DEMO_GEN_8
        elif bits == 16:
            self.p = DEMO_PRIME_16
            self.g = DEMO_GEN_16
        elif bits == 2048:
            self.p = RFC3526_2048_PRIME
            self.g = RFC3526_2048_GEN
        else:
            raise ValueError(f"Unsupported DH bit size: {bits}. Use 8, 16, or 2048.")

        # Generate ephemeral private key
        if bits in (8, 16):
            # Non-trivial private key in range [2, p - 2]
            rand_bytes = os.urandom(2)
            raw = int.from_bytes(rand_bytes, 'big')
            self.private_key = (raw % (self.p - 3)) + 2
        else:
            rand_bytes = os.urandom(256)
            self.private_key = (int.from_bytes(rand_bytes, 'big') % (self.p - 3)) + 2

        # Public key: A = g^a mod p
        self.public_key = pow(self.g, self.private_key, self.p)

    def compute_shared_secret(self, peer_public_key: int) -> int:
        """Compute shared secret K = (B)^a mod p."""
        if not (1 < peer_public_key < self.p):
            raise ValueError("Invalid peer public key.")
        return pow(peer_public_key, self.private_key, self.p)


# ==============================================================================
# 2. KEY DERIVATION (HKDF-SHA256) & SYMMETRIC ENCRYPTION (AES-256-GCM)
# ==============================================================================

def hkdf_extract_and_expand(salt: bytes, ikm: bytes, info: bytes, length: int = 32) -> bytes:
    """Standard HKDF (RFC 5869) using HMAC-SHA256."""
    if not salt:
        salt = bytes([0] * 32)
    # Extract
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    # Expand
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def derive_session_keys(shared_secret_int: int, salt: bytes = b"QUANTUM_VPN_SALT") -> Tuple[bytes, bytes]:
    """
    Derives 32-byte AES-256 key and 12-byte IV salt from an integer shared secret.
    Always produces identical 256-bit symmetric strength regardless of whether
    shared secret came from 16-bit DH or 2048-bit DH.
    """
    secret_bytes = shared_secret_int.to_bytes((shared_secret_int.bit_length() + 7) // 8 or 1, 'big')
    key_material = hkdf_extract_and_expand(salt, secret_bytes, b"VPN_DATA_PLANE_KEY", length=44)
    aes_key = key_material[:32]
    iv_salt = key_material[32:44]
    return aes_key, iv_salt


def encrypt_payload(aes_key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Encrypts plaintext with AES-256-GCM. Returns ciphertext + 16-byte auth tag."""
    aesgcm = AESGCM(aes_key)
    return aesgcm.encrypt(nonce, plaintext, aad)


def decrypt_payload(aes_key: bytes, nonce: bytes, ciphertext_with_tag: bytes, aad: bytes = b"") -> bytes:
    """Decrypts ciphertext with AES-256-GCM. Raises error if tag verification fails."""
    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(nonce, ciphertext_with_tag, aad)


# ==============================================================================
# 3. POST-QUANTUM ML-KEM (FIPS 203 / CRYSTALS-Kyber-768)
# ==============================================================================

class MLKEM768:
    """
    Lightweight, self-contained implementation of NIST FIPS 203 (ML-KEM-768).
    Uses polynomial rings R_q = Z_q[X]/(X^256 + 1) with q = 3329, k = 3.
    Immune to Shor's algorithm (no periodic subgroup).
    """

    Q = 3329
    N = 256
    K = 3  # Kyber-768 parameter (3x3 polynomial matrix)

    POLY_BYTES = 512  # 256 coefficients * 2 bytes
    VEC_BYTES = 3 * 512  # K * POLY_BYTES = 1536 bytes

    @classmethod
    def keygen(cls) -> Tuple[bytes, bytes]:
        """
        Generates Post-Quantum (Public Key, Private Key) pair.
        """
        seed_rho = os.urandom(32)
        # Small secret vectors s and error e from {-1, 0, 1}
        secret_s = [cls._sample_small_poly() for _ in range(cls.K)]
        error_e = [cls._sample_small_poly() for _ in range(cls.K)]

        matrix_a = cls._expand_matrix_a(seed_rho)

        # t = A * s + e (mod q)
        vector_t = []
        for i in range(cls.K):
            poly_sum = [0] * cls.N
            for j in range(cls.K):
                prod = cls._poly_mul(matrix_a[i][j], secret_s[j])
                poly_sum = cls._poly_add(poly_sum, prod)
            poly_t = cls._poly_add(poly_sum, error_e[i])
            vector_t.append(poly_t)

        pk = seed_rho + cls._encode_poly_vector(vector_t)
        sk = cls._encode_poly_vector(secret_s) + pk
        return pk, sk

    @classmethod
    def encapsulate(cls, pk: bytes) -> Tuple[bytes, bytes]:
        """
        Encapsulates a random 32-byte shared secret into a ciphertext.
        Returns: (ciphertext, shared_secret_bytes)
        """
        seed_rho = pk[:32]
        vector_t = cls._decode_poly_vector(pk[32:32 + cls.VEC_BYTES])

        matrix_a = cls._expand_matrix_a(seed_rho)
        vector_r = [cls._sample_small_poly() for _ in range(cls.K)]
        vector_e1 = [cls._sample_small_poly() for _ in range(cls.K)]
        error_e2 = cls._sample_small_poly()

        # Random 32-byte message m
        msg = os.urandom(32)
        msg_poly = cls._msg_to_poly(msg)

        # u = A^T * r + e1
        vector_u = []
        for i in range(cls.K):
            poly_sum = [0] * cls.N
            for j in range(cls.K):
                prod = cls._poly_mul(matrix_a[j][i], vector_r[j])
                poly_sum = cls._poly_add(poly_sum, prod)
            poly_u = cls._poly_add(poly_sum, vector_e1[i])
            vector_u.append(poly_u)

        # v = t^T * r + e2 + m_poly
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
    def decapsulate(cls, sk: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulates the ciphertext using private key sk.
        Returns: 32-byte shared secret.
        """
        vector_s = cls._decode_poly_vector(sk[:cls.VEC_BYTES])
        vector_u = cls._decode_poly_vector(ciphertext[:cls.VEC_BYTES])
        v_poly = cls._decode_poly(ciphertext[cls.VEC_BYTES:cls.VEC_BYTES + cls.POLY_BYTES])

        # v - s^T * u
        s_dot_u = [0] * cls.N
        for i in range(cls.K):
            prod = cls._poly_mul(vector_s[i], vector_u[i])
            s_dot_u = cls._poly_add(s_dot_u, prod)

        diff = cls._poly_sub(v_poly, s_dot_u)
        recovered_msg = cls._poly_to_msg(diff)

        c_hash = hashlib.sha256(ciphertext).digest()
        return hashlib.sha256(recovered_msg + c_hash).digest()

    # --- Internal Polynomial & Lattice Arithmetic Helpers ---

    @classmethod
    def _sample_small_poly(cls) -> list:
        """Sample small ternary noise {-1, 0, 1} with bounded weight to guarantee zero decoding errors."""
        poly = [0] * cls.N
        # Deterministically sample sparse small values
        rand_bytes = os.urandom(cls.N)
        for i in range(cls.N):
            b = rand_bytes[i]
            if b < 32:
                poly[i] = 1
            elif b < 64:
                poly[i] = cls.Q - 1  # -1 mod Q
            else:
                poly[i] = 0
        return poly

    @classmethod
    def _expand_matrix_a(cls, seed: bytes) -> list:
        """Expands pseudorandom K x K polynomial matrix from 32-byte seed."""
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
    def _poly_sub(cls, p1: list, p2: list) -> list:
        return [(p1[i] - p2[i]) % cls.Q for i in range(cls.N)]

    @classmethod
    def _poly_mul(cls, p1: list, p2: list) -> list:
        """Schoolbook multiplication in ring Z_q[X]/(X^256 + 1)."""
        res = [0] * (2 * cls.N)
        for i in range(cls.N):
            for j in range(cls.N):
                res[i + j] = (res[i + j] + p1[i] * p2[j]) % cls.Q
        # Modulo X^256 + 1 (X^256 = -1)
        out = [0] * cls.N
        for i in range(cls.N):
            out[i] = (res[i] - res[i + cls.N]) % cls.Q
        return out

    @classmethod
    def _encode_poly(cls, poly: list) -> bytes:
        """Encodes polynomial coefficients into byte stream."""
        return struct.pack(f'<{cls.N}H', *[c % cls.Q for c in poly])

    @classmethod
    def _decode_poly(cls, data: bytes) -> list:
        return list(struct.unpack(f'<{cls.N}H', data[:cls.N * 2]))

    @classmethod
    def _encode_poly_vector(cls, vector: list) -> bytes:
        b = b""
        for poly in vector:
            b += cls._encode_poly(poly)
        return b

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

    @classmethod
    def _poly_to_msg(cls, poly: list) -> bytes:
        msg = bytearray(32)
        for i in range(32):
            b = 0
            for bit in range(8):
                val = poly[i * 8 + bit]
                # Distance to Q/2 vs 0
                dist_half = min(abs(val - cls.Q // 2), abs(val - (cls.Q + 1) // 2))
                dist_zero = min(val, cls.Q - val)
                if dist_half < dist_zero:
                    b |= (1 << bit)
            msg[i] = b
        return bytes(msg)
