import os
import sys
import threading
import time
import io
import urllib.request
import socket
import urllib.error

sys.path.insert(0, os.getcwd())

import main
from board import board_to_dict, new_board, Item


def start_server():
    main.run('127.0.0.1', 9001)


def main_script():
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    for _ in range(20):
        try:
            s = socket.create_connection(('127.0.0.1', 9001), timeout=1)
            s.close()
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise SystemExit('server failed to start')

    b = new_board()
    b.items.append(Item(id='item_1', label='Demo', tier_id=b.tiers[0].id, image_url='data:image/png;base64,AAA='))
    archive = main.build_tier_archive(board_to_dict(b))
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = io.BytesIO()
    body.write(f'--{boundary}\r\n'.encode('utf-8'))
    body.write(b'Content-Disposition: form-data; name="file"; filename="test.tier"\r\n')
    body.write(b'Content-Type: application/octet-stream\r\n\r\n')
    body.write(archive)
    body.write(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    body_bytes = body.getvalue()

    req = urllib.request.Request('http://127.0.0.1:9001/api/import_tier', data=body_bytes, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('Content-Length', str(len(body_bytes)))

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print('status', resp.status)
        print(resp.read().decode('utf-8', errors='replace'))
    except urllib.error.HTTPError as e:
        print('http error', e.code, e.reason)
        print(e.read().decode('utf-8', errors='replace'))
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == '__main__':
    main_script()
