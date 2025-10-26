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
        b = Block(d["index"], d["timestamp"], d["data"], d["previous_hash"], d["proof"], d.get("nonce", 0))
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
        genesis = Block(index=1, timestamp=time(), data={"note": "Genesis Block"}, previous_hash="0", proof=0, nonce=0)
        genesis.hash = genesis.hash_block()
        self.chain = [genesis]

    def last_block(self) -> Block:
        return self.chain[-1]