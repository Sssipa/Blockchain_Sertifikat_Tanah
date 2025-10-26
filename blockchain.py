import hashlib
import json
import os
from time import time
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse

try:
    import requests  # optional, digunakan untuk resolve_conflicts jika tersedia
except Exception:
    requests = None


class Block:
    """
    Representasi 1 blok dalam blockchain.

    Fields:
    - index: urutan blok (mulai 1 untuk genesis)
    - timestamp: waktu pembuatan (float seconds)
    - data: dict berisi informasi sertifikat (nama, nomor, lokasi, luas, file_hash bila ada)
    - previous_hash: hash dari blok sebelumnya (string)
    - proof: nilai proof yang ditemukan oleh PoW
    - nonce: nilai nonce (opsional, disiapkan bila mau loop lain)
    - hash: hash final blok (sha256 dari isi terurut)
    """

    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str, proof: int, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.proof = proof
        self.nonce = nonce
        self.hash = self.hash_block()  # compute saat inisialisasi

    def hash_block(self) -> str:
        # Pastikan penyusunan dict konsisten (sort_keys=True)
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "proof": self.proof,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "proof": self.proof,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(d: Dict) -> "Block":
        b = Block(
            d["index"],
            d["timestamp"],
            d["data"],
            d["previous_hash"],
            d["proof"],
            d.get("nonce", 0)
        )
        # gunakan hash yang tersimpan (agar load chain tetap sama)
        b.hash = d.get("hash", b.hash_block())
        return b


class Blockchain:
    """
    Blockchain class:
    - manage chain (list Block)
    - current_data: buffer data sertifikat yang akan dimasukkan pada blok berikutnya
    - nodes: set alamat node lain di jaringan (untuk simulasi 2 miner)
    - difficulty: jumlah nol di awal syarat PoW (target = '0'*difficulty)
    - storage_path: path file JSON untuk menyimpan chain (persistence)
    """

    def __init__(self, difficulty=3, storage_path: str = "chain_data.json"):
        self.chain: List[Block] = []
        self.current_data: List[Dict] = []
        self.nodes: Set[str] = set()
        self.difficulty = difficulty
        self.storage_path = storage_path

        # load chain jika ada, atau buat genesis
        if os.path.exists(self.storage_path) and os.path.getsize(self.storage_path) > 0:
            try:
                self.load_chain()
            except Exception:
                # jika file rusak, buat genesis baru (bersih)
                self.create_genesis_block()
                self.save_chain()
        else:
            self.create_genesis_block()
            self.save_chain()

    # -------------------------
    # Chain basic operations
    # -------------------------

    def create_genesis_block(self):
        """Membuat genesis block (blok pertama)."""
        genesis = Block(
            index=1,
            timestamp=time(),
            data={"note": "Genesis Block"},
            previous_hash="0",
            proof=0,
            nonce=0
        )
        genesis.hash = genesis.hash_block()
        self.chain = [genesis]

    def last_block(self) -> Block:
        return self.chain[-1]

    # -------------------------
    # Data / transaksi
    # -------------------------

    def add_certificate(self, nama: str, nomor: str, lokasi: str, luas: str, file_hash: Optional[str] = None) -> int:
        """
        Tambah data sertifikat ke buffer current_data.
        Kembalikan index blok dimana data akan ditempatkan (last_index + 1).
        Jika ingin langsung menambang blok, gunakan add_certificate_and_mine.
        """
        entry = {
            "nama": nama,
            "nomor_sertifikat": nomor,
            "lokasi": lokasi,
            "luas": luas,
            "file_hash": file_hash  # bisa None jika tidak ada scan
        }
        self.current_data.append(entry)
        return self.last_block().index + 1

    # -------------------------
    # Proof of Work (PoW)
    # -------------------------

    def proof_of_work(self, last_proof: int) -> int:
        """
        Mencari proof baru sedemikian sehingga hash(last_proof + proof)
        memenuhi difficulty (diawali '0'*difficulty).
        Untuk keperluan demo, gunakan difficulty rendah (2-4).
        """
        proof = 0
        target_prefix = '0' * self.difficulty
        while True:
            guess = f"{last_proof}{proof}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash.startswith(target_prefix):
                return proof
            proof += 1

    @staticmethod
    def valid_proof(last_proof: int, proof: int, difficulty: int) -> bool:
        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash.startswith('0' * difficulty)

    # -------------------------
    # Menambah blok (setelah mining)
    # -------------------------

    def new_block(self, proof: int, previous_hash: Optional[str] = None) -> Block:
        """
        Membuat blok baru dengan proof yang sudah ditemukan.
        Mengosongkan current_data. previous_hash diambil dari blok terakhir bila tidak diberikan.
        """
        prev_hash = previous_hash or self.last_block().hash
        block = Block(
            index=self.last_block().index + 1,
            timestamp=time(),
            data=self.current_data.copy(),
            previous_hash=prev_hash,
            proof=proof,
            nonce=0
        )
        block.hash = block.hash_block()

        # reset buffer data
        self.current_data = []
        self.chain.append(block)
        self.save_chain()
        return block

    def add_certificate_and_mine(self, nama: str, nomor: str, lokasi: str, luas: str, file_hash: Optional[str] = None) -> Tuple[Block, int]:
        """
        Tambah data sertifikat (ke buffer) lalu jalankan mining (PoW)
        berdasarkan last_proof, setelah itu buat dan kembalikan blok baru dan proof yang ditemukan.
        Mengembalikan tuple (block, proof)
        """
        self.add_certificate(nama, nomor, lokasi, luas, file_hash)
        last_block = self.last_block()
        last_proof = last_block.proof
        proof = self.proof_of_work(last_proof)
        new_block = self.new_block(proof, previous_hash=self.last_block().hash)
        return new_block, proof

    # -------------------------
    # Validasi chain
    # -------------------------

    def is_chain_valid(self) -> Tuple[bool, str]:
        """
        Validate seluruh rantai:
        - previous_hash cocok
        - hash blok sesuai isi
        - proof valid (kombinasi previous.proof + current.proof)
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # previous_hash check
            if current.previous_hash != previous.hash:
                return False, f"Previous hash mismatch at index {current.index}"

            # hash integrity check
            if current.hash != current.hash_block():
                return False, f"Hash content mismatch at index {current.index}"

            # proof validity
            guess = f"{previous.proof}{current.proof}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if not guess_hash.startswith('0' * self.difficulty):
                return False, f"Proof of Work invalid at index {current.index}"

        return True, "Chain valid"

    # -------------------------
    # Persistence: save/load to JSON
    # -------------------------

    def save_chain(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2, ensure_ascii=False)

    def load_chain(self):
        with open(self.storage_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.chain = [Block.from_dict(d) for d in raw]

    # -------------------------
    # Node / network helpers (untuk 2 miner simulasi)
    # -------------------------

    def register_node(self, address: str):
        """Register a node by URL, e.g. 'http://localhost:5001'"""
        parsed = urlparse(address)
        if parsed.netloc:
            self.nodes.add(parsed.netloc)
        elif parsed.path:
            # Accept formats like 'localhost:5001'
            self.nodes.add(parsed.path)
        else:
            raise ValueError("Invalid node address")

    def valid_chain_from_nodes(self, chain_data: List[Dict]) -> Tuple[bool, List[Block]]:
        """Given raw chain data (list of dicts), convert and validate."""
        try:
            candidate = [Block.from_dict(d) for d in chain_data]
        except Exception:
            return False, []

        for i in range(1, len(candidate)):
            curr = candidate[i]
            prev = candidate[i - 1]
            if curr.previous_hash != prev.hash:
                return False, []
            if curr.hash != curr.hash_block():
                return False, []
            guess = f"{prev.proof}{curr.proof}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if not guess_hash.startswith('0' * self.difficulty):
                return False, []

        return True, candidate

    def resolve_conflicts(self) -> Tuple[bool, str]:
        """
        Consensus algorithm:
        - Query all registered nodes for their chains (via /chain endpoint expected).
        - If a longer valid chain is found, replace local chain.
        Returns (True, "replaced") if replaced; (False, reason) otherwise.
        """
        if not requests:
            return False, "requests library not installed; cannot resolve conflicts"

        neighbours = self.nodes
        new_chain: Optional[List[Block]] = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                url = f"http://{node}/chain"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    length = data.get("length")
                    chain_data = data.get("chain")
                    if length is None or chain_data is None:
                        continue
                    if length > max_length:
                        valid, candidate = self.valid_chain_from_nodes(chain_data)
                        if valid and len(candidate) > max_length:
                            max_length = len(candidate)
                            new_chain = candidate
            except Exception:
                continue

        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True, "Chain replaced by longer valid chain"

        return False, "No longer valid chain found"

    # -------------------------
    # Helper: compute SHA256 hash for file (scan)
    # -------------------------

    @staticmethod
    def file_sha256(filepath: str) -> str:
        """Hitung SHA-256 dari file yang disediakan."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
