import hashlib
import json
import os
from time import time
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse

try:
    import requests 
except Exception:
    requests = None


class Block:
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str, proof: int, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.proof = proof
        self.nonce = nonce
        self.hash = self.hash_block() 

    def hash_block(self) -> str:
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
        b.hash = d.get("hash", b.hash_block())
        return b


class Blockchain:

    def __init__(self, difficulty=3, storage_path: str = "chain_data.json"):
        self.chain: List[Block] = []
        self.current_data: List[Dict] = []
        self.nodes: Set[str] = set()
        self.difficulty = difficulty
        self.storage_path = storage_path

        if os.path.exists(self.storage_path) and os.path.getsize(self.storage_path) > 0:
            try:
                self.load_chain()
            except Exception:
                self.create_genesis_block()
                self.save_chain()
        else:
            self.create_genesis_block()
            self.save_chain()

    def create_genesis_block(self):
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

    def add_certificate(self, nama: str, nomor: str, lokasi: str, luas: str, file_hash: Optional[str] = None) -> int:
        entry = {
            "nama": nama,
            "nomor_sertifikat": nomor,
            "lokasi": lokasi,
            "luas": luas,
            "file_hash": file_hash 
        }
        self.current_data.append(entry)
        return self.last_block().index + 1

    def proof_of_work(self, last_proof: int) -> int:
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

    def new_block(self, proof: int, previous_hash: Optional[str] = None) -> Block:
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

        self.current_data = []
        self.chain.append(block)
        self.save_chain()
        return block

    def add_certificate_and_mine(self, nama: str, nomor: str, lokasi: str, luas: str, file_hash: Optional[str] = None) -> Tuple[Block, int]:
        self.add_certificate(nama, nomor, lokasi, luas, file_hash)
        last_block = self.last_block()
        last_proof = last_block.proof
        proof = self.proof_of_work(last_proof)
        new_block = self.new_block(proof, previous_hash=self.last_block().hash)
        return new_block, proof

    def is_chain_valid(self) -> Tuple[bool, str]:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.hash:
                return False, f"Previous hash mismatch at index {current.index}"

            if current.hash != current.hash_block():
                return False, f"Hash content mismatch at index {current.index}"

            guess = f"{previous.proof}{current.proof}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if not guess_hash.startswith('0' * self.difficulty):
                return False, f"Proof of Work invalid at index {current.index}"

        return True, "Chain valid"
    
    def save_chain(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2, ensure_ascii=False)

    def load_chain(self):
        with open(self.storage_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.chain = [Block.from_dict(d) for d in raw]

    def register_node(self, address: str):
        parsed = urlparse(address)
        if parsed.netloc:
            self.nodes.add(parsed.netloc)
        elif parsed.path:
            self.nodes.add(parsed.path)
        else:
            raise ValueError("Invalid node address")

    def valid_chain_from_nodes(self, chain_data: List[Dict]) -> Tuple[bool, List[Block]]:
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

    @staticmethod
    def file_sha256(filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
