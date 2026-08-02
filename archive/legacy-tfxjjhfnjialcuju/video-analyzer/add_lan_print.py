with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', encoding='utf-8') as f:
    content = f.read()

# Add LAN access URL printing before app.run()
old_text = '    app.run(host=args.host, port=args.port, debug=False, threaded=True)'

new_text = '''    # Print LAN access URL
    if args.host == '0.0.0.0':
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
            print(f'  LAN access: http://{ip}:{args.port}')
        except Exception:
            pass
        finally:
            s.close() if 's' in dir() else None
    
    app.run(host=args.host, port=args.port, debug=False, threaded=True)'''

if old_text in content:
    content = content.replace(old_text, new_text, 1)
    print('[OK] Added LAN access URL printing')
else:
    print('[FAIL] Could not find app.run() call')
    # Search for it
    idx = content.find('app.run(')
    if idx > 0:
        print('Found app.run at position', idx)
        print('Context:', content[idx-100:idx+50])

with open(r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\transcribe_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
