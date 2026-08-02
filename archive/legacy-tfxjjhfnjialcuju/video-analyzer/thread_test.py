"""极简 Flask 服务器，测试 daemon 线程的 os.write 是否能输出"""
from flask import Flask, jsonify
import threading, time, os, sys

app = Flask(__name__)
LOG = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\thread_test.log'

@app.route('/test')
def test():
    def bg():
        os.write(2, b"[BG] thread started\n")
        for i in range(3):
            time.sleep(0.3)
            os.write(2, f"[BG] tick {i}\n".encode())
        os.write(2, b"[BG] done\n")

    t = threading.Thread(target=bg, daemon=True)
    t.start()
    return jsonify({'msg': 'started'})

if __name__ == '__main__':
    os.write(2, b"[MAIN] starting Flask\n")
    app.run(host='127.0.0.1', port=9999, debug=False, threaded=True)
