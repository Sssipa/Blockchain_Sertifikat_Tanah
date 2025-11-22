import hashlib
import json
import os
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests


class Blockchain:
    def __init__(self, port, difficulty=3):
        self.difficulty = difficulty
        self.nodes = set()
        self.port = port

        # Load chain & mempool
        self.chain = []
        self.current_transactions = []

        self.chain_file = f"chain_{port}.json"
        self.mempool_file = f"mempool_{port}.json"

        self.load_chain()
        self.load_mempool()

        # Jika chain kosong buat genesis block
        if len(self.chain) == 0:
            self.new_block(previous_hash="1", proof=100)

    # ============================================
    #       TRANSAKSI (MEMPOOL)
    # ============================================
    def new_transaction(self, nama, nomor, lokasi, luas, file_hash):
        tx = {
            'txid': uuid4().hex,              # ID transaksi unik
            'nama': nama,
            'nomor_sertifikat': nomor,
            'lokasi': lokasi,
            'luas': luas,
            'file_hash': file_hash,
            'timestamp': time()
        }

        self.current_transactions.append(tx)
        self.save_mempool()

        return tx

    # ============================================
    #       BLOCK BARU
    # ============================================
    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions.copy(),
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []
        self.chain.append(block)

        self.save_chain()
        self.save_mempool()

        return block

    # ============================================
    #   MINING (POW)
    # ============================================
    def mine(self):
        last_block = self.chain[-1]
        last_proof = last_block['proof']

        proof = self.proof_of_work(last_proof)
        block = self.new_block(proof)

        return block

    # ============================================
    #     PROOF OF WORK
    # ============================================
    def proof_of_work(self, last_proof):
        proof = 0
        while True:
            guess = f"{last_proof}{proof}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()

            if guess_hash[:self.difficulty] == "0" * self.difficulty:
                return proof
            proof += 1

    # ============================================
    #       HASH BLOK
    # ============================================
    @staticmethod
    def hash(block):
        encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    # ============================================
    #    REGISTER NODE DALAM NETWORK
    # ============================================
    def register_node(self, address):
        parsed = urlparse(address)
        self.nodes.add(parsed.netloc)

    # ============================================
    #     VALIDASI CHAIN
    # ============================================
    def valid_chain(self, chain):
        last_block = chain[0]

        for block in chain[1:]:
            # Validasi hash
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Validasi POW
            guess = f"{last_block['proof']}{block['proof']}".encode()
            if hashlib.sha256(guess).hexdigest()[:self.difficulty] != ("0" * self.difficulty):
                return False

            last_block = block

        return True

    # ============================================
    #   SINKRONISASI CHAIN (Longest Chain Rule)
    # ============================================
    def sync_chain(self):
        longest_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            try:
                resp = requests.get(f"http://{node}/chain", timeout=3)
                data = resp.json()

                length = data['length']
                remote_chain = data['chain']

                if length > max_length and self.valid_chain(remote_chain):
                    max_length = length
                    longest_chain = remote_chain

            except:
                pass  # Node offline, skip

        if longest_chain:
            self.chain = longest_chain
            self.save_chain()
            return True

        return False

    # ============================================
    #   SINKRONISASI MEMPOOL
    # ============================================
    def sync_mempool(self):
        all_tx = {tx['txid']: tx for tx in self.current_transactions}

        for node in self.nodes:
            try:
                resp = requests.get(f"http://{node}/mempool", timeout=3)
                txs = resp.json()

                for tx in txs:
                    all_tx[tx['txid']] = tx  # gabungkan & hilangkan duplikasi

            except:
                pass

        self.current_transactions = list(all_tx.values())
        self.save_mempool()

    # ============================================
    #     SIMPAN / LOAD FILE
    # ============================================
    def save_chain(self):
        with open(self.chain_file, "w") as f:
            json.dump(self.chain, f, indent=4)

    def load_chain(self):
        if os.path.exists(self.chain_file):
            with open(self.chain_file, "r") as f:
                self.chain = json.load(f)

    def save_mempool(self):
        with open(self.mempool_file, "w") as f:
            json.dump(self.current_transactions, f, indent=4)

    def load_mempool(self):
        if os.path.exists(self.mempool_file):
            with open(self.mempool_file, "r") as f:
                self.current_transactions = json.load(f)
