from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory, flash
from flask_cors import CORS
from uuid import uuid4
from blockchain import Blockchain
import os
import hashlib
from werkzeug.utils import secure_filename
import uuid

# -------------------------
# Inisialisasi Flask app
# -------------------------
app = Flask(__name__)
CORS(app)
app.secret_key = "supersecretkey"  # untuk flash message

# ID unik node
node_identifier = str(uuid4()).replace('-', '')

# Inisialisasi blockchain dengan difficulty 3
blockchain = Blockchain(difficulty=3)

# Folder untuk upload file sertifikat
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -------------------------
# ROUTES
# -------------------------

@app.route('/')
def index():
    chain_data = [block.to_dict() for block in blockchain.chain]
    pending = blockchain.current_data
    return render_template('index.html', chain=chain_data, pending=pending, length=len(chain_data))


@app.route('/mine', methods=['GET'])
def mine():
    """Menambang blok baru dari data sertifikat yang sudah ditambahkan"""
    last_block = blockchain.last_block()
    last_proof = last_block.proof

    proof = blockchain.proof_of_work(last_proof)
    new_block = blockchain.new_block(proof)

    flash("🪙 Blok baru berhasil ditambang!", "success")
    return redirect(url_for('index'))


@app.route('/certificate/new', methods=['POST'])
def new_certificate():
    """Tambah data sertifikat ke buffer (mempool) — tidak langsung menambang."""
    values = request.form.to_dict()

    nama = values.get('nama')
    nomor = values.get('nomor_sertifikat')
    lokasi = values.get('lokasi')
    luas = values.get('luas')

    if not all([nama, nomor, lokasi, luas]):
        flash("❌ Data sertifikat belum lengkap!", "danger")
        return redirect(url_for('index'))

    file = request.files.get('file')
    file_hash = None
    file_url = None
    if file and file.filename:
        # amanin nama file lalu simpan
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        file_hash = blockchain.file_sha256(filepath)
        file_url = url_for('uploaded_file', filename=filename)

    # HANYA tambahkan transaksi ke buffer (current_data)
    # jika kamu ingin menyimpan file_url juga, tambahkan parameter di add_certificate
    blockchain.add_certificate(nama=nama, nomor=nomor, lokasi=lokasi, luas=luas, file_hash=file_hash)

    flash("✅ Transaksi disimpan ke mempool. Klik 'Tambang Blok Baru' untuk menambang.", "success")
    return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Mengambil file yang sudah diupload"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/chain', methods=['GET'])
def full_chain():
    """Menampilkan seluruh isi blockchain"""
    response = {
        'chain': [block.to_dict() for block in blockchain.chain],
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """Mendaftarkan node baru untuk simulasi jaringan blockchain"""
    values = request.get_json(silent=True) or {}
    nodes = values.get('nodes')
    if not nodes:
        return jsonify({'error': 'Silakan kirim daftar node!'}), 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': '✅ Node baru berhasil didaftarkan',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """Menjalankan mekanisme konsensus antar node"""
    replaced, message = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': message,
            'new_chain': [b.to_dict() for b in blockchain.chain]
        }
    else:
        response = {
            'message': message,
            'chain': [b.to_dict() for b in blockchain.chain]
        }
    return jsonify(response), 200


# -------------------------
# MAIN ENTRY
# -------------------------
if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)
