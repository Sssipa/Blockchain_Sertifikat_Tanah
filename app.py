import hashlib
import json
import os
import sys
import threading
import time
from time import time
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse

from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory, flash
from flask_cors import CORS
import uuid
from uuid import uuid4
from blockchain import Blockchain
from werkzeug.utils import secure_filename

# -----------------------------------
#   FLASK APP INIT
# -----------------------------------
app = Flask(__name__)
CORS(app)
app.secret_key = "supersecretkey"

# Node unik
node_identifier = str(uuid.uuid4()).replace("-", "")

# -----------------------------------
#   SET PORT NODE INI
# -----------------------------------
port = 5000
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except:
        print("Port tidak valid, memakai default 5000")

print(f"[NODE] Blockchain node berjalan pada PORT {port}")

# -----------------------------------
#   INIT BLOCKCHAIN
# -----------------------------------
blockchain = Blockchain(port=port, difficulty=3)

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ======================================================================
#                           AUTO SYNC THREAD
# ======================================================================

def background_sync():
    """Loop sinkronisasi otomatis berjalan di background"""
    while True:
        try:
            print("[AUTO-SYNC] Menyinkronkan CHAIN...", flush=True)
            blockchain.sync_chain()

            print("[AUTO-SYNC] Menyinkronkan MEMPOOL...", flush=True)
            blockchain.sync_mempool()
        except Exception as e:
            print(f"[AUTO-SYNC] Error: {e}")

        time.sleep(5)   # sync setiap 5 detik


# Jalankan thread sinkronisasi otomatis
sync_thread = threading.Thread(target=background_sync, daemon=True)
sync_thread.start()


# ======================================================================
#                              FRONTEND
# ======================================================================

@app.route('/')
def index():
    chain_data = blockchain.chain
    return render_template(
        'index.html',
        chain=chain_data,
        length=len(chain_data),
        mempool=blockchain.current_transactions
    )


# ======================================================================
#                              MINE NEW BLOCK
# ======================================================================
@app.route('/mine')
def mine():
    if len(blockchain.current_transactions) == 0:
        flash("Mempool kosong, tidak ada transaksi untuk ditambang!", "warning")
        return redirect(url_for('index'))

    block = blockchain.mine()

    flash("Blok baru berhasil ditambang!", "success")
    return redirect(url_for('index'))


# ======================================================================
#                           NEW CERTIFICATE (TX)
# ======================================================================
@app.route('/certificate/new', methods=['POST'])
def new_certificate():
    data = request.form.to_dict()

    nama = data.get("nama")
    nomor = data.get("nomor_sertifikat")
    lokasi = data.get("lokasi")
    luas = data.get("luas")

    if not all([nama, nomor, lokasi, luas]):
        flash("Data sertifikat belum lengkap!", "danger")
        return redirect(url_for('index'))

    # Upload file sertifikat
    file = request.files.get("file")
    file_hash = None

    if file and file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

    blockchain.new_transaction(nama, nomor, lokasi, luas, file_hash)

    flash("Transaksi berhasil disimpan ke mempool!", "success")
    return redirect(url_for('index'))


# ======================================================================
#                               DOWNLOAD FILE
# ======================================================================
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ======================================================================
#                                  CHAIN
# ======================================================================
@app.route('/chain')
def full_chain():
    return jsonify({
        "chain": blockchain.chain,
        "length": len(blockchain.chain)
    })


# ======================================================================
#                                  MEMPOOL
# ======================================================================
@app.route('/mempool')
def mempool():
    return jsonify(blockchain.current_transactions)


# ======================================================================
#                                  REGISTER NODE
# ======================================================================
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json(silent=True) or {}
    nodes = values.get('nodes')

    if not nodes:
        return jsonify({"error": "Kirim daftar node!"}), 400

    for node in nodes:
        blockchain.register_node(node)

    return jsonify({
        "message": "Node berhasil diregister",
        "nodes": list(blockchain.nodes)
    })


# ======================================================================
#                              MANUAL SYNC (Optional)
# ======================================================================
@app.route('/nodes/sync/chain')
def sync_chain_manual():
    updated = blockchain.sync_chain()
    return jsonify({
        "updated": updated,
        "chain": blockchain.chain
    })


@app.route('/nodes/sync/mempool')
def sync_mempool_manual():
    blockchain.sync_mempool()
    return jsonify({
        "mempool": blockchain.current_transactions
    })


# ======================================================================
#                               RUN APP
# ======================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=True)
