from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
from uuid import uuid4
from blockchain import Blockchain
import os
import hashlib

app = Flask(__name__)
CORS(app)

# ID unik node
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

# Folder untuk upload file sertifikat
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Ubah objek Block ke dict agar bisa dibaca Jinja2
    chain_data = [block.to_dict() for block in blockchain.chain]
    return render_template('index.html', chain=chain_data, length=len(chain_data))

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block()
    proof = blockchain.proof_of_work(last_block.proof)

    # Tambahkan transaksi dummy untuk node ini
    blockchain.new_transaction(
        id_tanah="MINING_REWARD",
        pemilik_lama="SYSTEM",
        pemilik_baru=node_identifier,
        lokasi="Server Node",
        file_hash=None,
        file_url=None
    )

    block = blockchain.new_block(proof)
    response = {
        'message': "🪙 Blok baru berhasil ditambang (Proof of Work)!",
        'index': block.index,
        'data': block.data,
        'proof': block.proof,
        'previous_hash': block.previous_hash,
        'hash': block.hash,
        'consensus': 'Proof of Work'
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json(silent=True) or {}

    # Jika dikirim dari form HTML
    if not values:
        values = {
            'id_tanah': request.form.get('id_tanah'),
            'pemilik_lama': request.form.get('pemilik_lama'),
            'pemilik_baru': request.form.get('pemilik_baru'),
            'lokasi': request.form.get('lokasi'),
            'file_hash': None,
            'file_url': None
        }

        # Jika ada file upload
        file = request.files.get('file')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            # Buat hash dari file sertifikat
            with open(filepath, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            values['file_hash'] = file_hash
            values['file_url'] = f"/uploads/{file.filename}"

    required = ['id_tanah', 'pemilik_lama', 'pemilik_baru', 'lokasi']
    if not all(k in values and values[k] for k in required):
        chain_data = [block.to_dict() for block in blockchain.chain]
        return render_template('index.html', chain=chain_data, error="❌ Data belum lengkap!")

    blockchain.new_transaction(
        values['id_tanah'],
        values['pemilik_lama'],
        values['pemilik_baru'],
        values['lokasi'],
        values.get('file_hash'),
        values.get('file_url')
    )

    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': [block.to_dict() for block in blockchain.chain],
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json(silent=True) or {}
    nodes = values.get('nodes')
    if not nodes:
        return jsonify({'error': 'Silakan berikan daftar node'}), 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': '✅ Node baru berhasil didaftarkan',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {'message': '✅ Chain telah diperbarui (konsensus)', 'new_chain': [b.to_dict() for b in blockchain.chain]}
    else:
        response = {'message': 'Chain sudah paling valid', 'chain': [b.to_dict() for b in blockchain.chain]}
    return jsonify(response), 200

if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)
