#!/usr/bin/env python3
"""Show every USB-connected RME configurator as a tab on one page. See README.md."""
import asyncio, functools, html, re, socket, subprocess, sys, webbrowser

DEVICE = ('172.20.0.1', 80)
HOST_SUBNET = 'inet 172.20.0.'
PAGE_PORT = 8000
IP_BOUND_IF = 25  # macOS socket option: route this socket through one specific interface
# macOS TCP keepalive options (level IPPROTO_TCP) and values: probe after 30 s idle, every
# 10 s, give up after 3 misses, so a connection to a vanished device is dropped in about a minute
KEEPALIVE = ((0x10, 30), (0x101, 10), (0x102, 3))  # TCP_KEEPALIVE, TCP_KEEPINTVL, TCP_KEEPCNT
TIMEOUT = 3
NAME_ATTEMPTS = 3

PAGE = '''<!doctype html><meta charset="utf-8"><title>RME</title><style>
body{margin:0;height:100vh;display:flex;flex-direction:column;font:14px system-ui}
nav{display:flex;gap:4px;padding:8px 8px 0;background:#2b2b2b;color:#ccc;border-bottom:3px solid #fff}
button{padding:8px 20px;border:0;border-radius:8px 8px 0 0;background:#444;color:#ccc;font:inherit;cursor:pointer}
button:hover{background:#555} button.on{background:#fff;color:#000;font-weight:600}
iframe{flex:1;border:0;display:none} iframe.on{display:block}
</style><nav>%s</nav>%s<script>
function show(n){
  for(const tag of ['button','iframe'])
    document.querySelectorAll(tag).forEach((el,i)=>el.classList.toggle('on',i==n))
}
show(0)
</script>'''


def rme_interfaces():
    found = []
    for line in subprocess.run(['ifconfig'], capture_output=True, text=True).stdout.splitlines():
        if not line[0].isspace():
            name = line.split(':')[0]
        elif HOST_SUBNET in line:
            found.append(name)
    return sorted(found)


async def connect(interface):
    sock = socket.socket()
    try:
        sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(interface))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        for option, value in KEEPALIVE:
            sock.setsockopt(socket.IPPROTO_TCP, option, value)
        sock.setblocking(False)
        await asyncio.wait_for(asyncio.get_running_loop().sock_connect(sock, DEVICE), TIMEOUT)
        return await asyncio.open_connection(sock=sock)
    except BaseException:
        sock.close()
        raise


async def model_name(interface):
    query = '{"device":{"model_name":null}}'
    request = (f'POST /api/v2/self HTTP/1.1\r\nHost: {DEVICE[0]}\r\nConnection: close\r\n'
               f'Content-Type: application/json\r\nContent-Length: {len(query)}\r\n\r\n{query}').encode()
    for _ in range(NAME_ATTEMPTS):
        try:
            reader, writer = await connect(interface)
        except (OSError, asyncio.TimeoutError):
            continue
        try:
            writer.write(request)
            reply = await asyncio.wait_for(reader.read(), TIMEOUT)
        except (OSError, asyncio.TimeoutError):
            continue
        finally:
            writer.close()
        match = re.search(rb'"model_name":"([^"]+)"', reply)
        if match:
            return match[1].decode()
    return interface


async def copy(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except OSError:
        pass
    writer.close()


async def forward_to_device(interface, browser_reader, browser_writer):
    try:
        device_reader, device_writer = await connect(interface)
    except (OSError, asyncio.TimeoutError):
        browser_writer.close()
        return
    # Closing either side ends the other copy too, so both connections are always released
    await asyncio.gather(copy(browser_reader, device_writer), copy(device_reader, browser_writer))


async def serve_page(page, reader, writer):
    try:
        request = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), TIMEOUT)
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        writer.close()
        return

    if request.split()[:2] == [b'GET', b'/']:
        status, body = '200 OK', page
    else:
        status, body = '404 Not Found', b'Not found'
    writer.write(f'HTTP/1.1 {status}\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n'
                 f'Content-Length: {len(body)}\r\n\r\n'.encode() + body)
    try:
        await writer.drain()
    except OSError:
        pass
    writer.close()


async def main():
    interfaces = rme_interfaces()
    if not interfaces:
        sys.exit('No RME devices found on USB. Plug one in and run again.')

    names = await asyncio.gather(*map(model_name, interfaces))
    tabs = frames = ''
    for n, (interface, name) in enumerate(zip(interfaces, names)):
        port = PAGE_PORT + 1 + n
        await asyncio.start_server(functools.partial(forward_to_device, interface), '127.0.0.1', port)
        tabs += f'<button onclick="show({n})">{html.escape(name)}</button>'
        frames += f'<iframe src="http://127.0.0.1:{port}/"></iframe>'
        print(f'{name} ({interface}): http://127.0.0.1:{port}')

    page = (PAGE % (tabs, frames)).encode()
    server = await asyncio.start_server(functools.partial(serve_page, page), '127.0.0.1', PAGE_PORT)
    webbrowser.open(f'http://127.0.0.1:{PAGE_PORT}')
    await server.serve_forever()


asyncio.run(main())
