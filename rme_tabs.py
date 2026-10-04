#!/usr/bin/env python3
"""Tabbed host page for USB-connected RME configurators (macOS). Run: python3 rme_tabs.py"""
import asyncio, functools, re, socket, subprocess, webbrowser

IP_BOUND_IF = 25  # macOS socket option: send via this interface, so identical device IPs don't clash
ports = {}  # interface -> local port proxying to that device


def interfaces():
    found, name = [], None
    for line in subprocess.run(['ifconfig'], capture_output=True, text=True).stdout.splitlines():
        if not line[0].isspace():
            name = line.split(':')[0]
        elif 'inet 172.20.0.' in line:
            found.append(name)
    return found


async def connect(iface):
    s = socket.socket()
    s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(iface))
    s.setblocking(False)
    await asyncio.wait_for(asyncio.get_running_loop().sock_connect(s, ('172.20.0.1', 80)), 3)
    return await asyncio.open_connection(sock=s)


async def model(iface):
    body = '{"device":{"model_name":null}}'
    try:
        r, w = await connect(iface)
        w.write(f'POST /api/v2/self HTTP/1.1\r\nHost: 172.20.0.1\r\nConnection: close\r\n'
                f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}'.encode())
        reply = await asyncio.wait_for(r.read(), 3)
        w.close()
        return re.search(rb'"model_name":"([^"]+)"', reply)[1].decode()
    except (OSError, TypeError, asyncio.TimeoutError):
        return iface


async def pump(r, w):
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except OSError:
        pass
    w.close()


async def proxy(iface, r, w):
    try:
        dr, dw = await connect(iface)
    except (OSError, asyncio.TimeoutError):
        return w.close()
    await asyncio.gather(pump(r, dw), pump(dr, w))


async def page(r, w):
    await r.readuntil(b'\r\n\r\n')
    found = interfaces()
    for i in found:
        if i not in ports:
            ports[i] = 8001 + len(ports)
            await asyncio.start_server(functools.partial(proxy, i), '127.0.0.1', ports[i])
    names = await asyncio.gather(*map(model, found))
    tabs = ''.join(f'<button onclick="show({n})">{name}</button>' for n, name in enumerate(names))
    frames = ''.join(f'<iframe src="http://127.0.0.1:{ports[i]}/"></iframe>' for i in found)
    html = f'''<!doctype html><title>RME</title><style>
body{{margin:0;height:100vh;display:flex;flex-direction:column;font:14px system-ui}}
button{{padding:8px 16px;border:0;background:#ddd}} button.on{{background:#fff;font-weight:bold}}
iframe{{flex:1;border:0;display:none}} iframe.on{{display:block}}</style>
<nav>{tabs or 'No RME devices found on USB. Plug one in and reload.'}</nav>{frames}<script>
function show(n){{for(const s of ['button','iframe'])document.querySelectorAll(s).forEach((e,i)=>e.classList.toggle('on',i==n))}}
show(0)</script>'''.encode()
    w.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n'
            + f'Content-Length: {len(html)}\r\n\r\n'.encode() + html)
    await w.drain()
    w.close()


async def main():
    server = await asyncio.start_server(page, '127.0.0.1', 8000)
    webbrowser.open('http://127.0.0.1:8000')
    await server.serve_forever()


asyncio.run(main())
