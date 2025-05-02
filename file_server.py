from flask import Flask, send_from_directory, request, render_template, Response
import socket
import threading
import os
import qrcode
import io

app = Flask(__name__)
SHARED_FOLDER = './shared'
HTTP_PORT = 8000
BROADCAST_PORT = 9999

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect to non-routable IP
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

@app.route('/')
def home():
    files = os.listdir(SHARED_FOLDER)
    return render_template('index.html', files=files)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(SHARED_FOLDER, filename, as_attachment=True)

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk = request.files['chunk']
    filename = request.form['filename']
    chunk_index = int(request.form['chunk_index'])
    total_chunks = int(request.form['total_chunks'])

    chunk_folder = os.path.join(TEMP_CHUNK_FOLDER, filename)
    os.makedirs(chunk_folder, exist_ok=True)

    # Save chunk
    chunk_path = os.path.join(chunk_folder, f'part{chunk_index}')
    chunk.save(chunk_path)

    # If last chunk, reassemble
    if len(os.listdir(chunk_folder)) == total_chunks:
        with open(os.path.join(SHARED_FOLDER, filename), 'wb') as output:
            for i in range(total_chunks):
                part_path = os.path.join(chunk_folder, f'part{i}')
                with open(part_path, 'rb') as part_file:
                    output.write(part_file.read())

        # Clean up temp folder
        for part_file in os.listdir(chunk_folder):
            os.remove(os.path.join(chunk_folder, part_file))
        os.rmdir(chunk_folder)

    return 'OK'

@app.route('/qrcode')
def qrcode_view():
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{HTTP_PORT}/"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')

def broadcast_presence():
    msg = f"FILE_SERVER:{get_local_ip()}:{HTTP_PORT}".encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
        time.sleep(5)

if __name__ == '__main__':
    import time
    from threading import Thread
    os.makedirs(SHARED_FOLDER, exist_ok=True)
    Thread(target=broadcast_presence, daemon=True).start()
    app.run(host='0.0.0.0', port=HTTP_PORT)
