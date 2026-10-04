#!/usr/bin/env python3
"""Show every USB-connected RME configurator as a tab on one page. See README.md."""
import asyncio, functools, re, socket, subprocess, webbrowser

DEVICE = ('172.20.0.1', 80)
HOST_SUBNET = 'inet 172.20.0.'
PAGE_PORT = 8000
IP_BOUND_IF = 25  # macOS socket option: route this socket through one specific interface
TIMEOUT = 3

PAGE = '''<!doctype html><title>RME</title><style>
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

proxy_ports = {}  # interface name -> local port forwarding to the device on that interface


def rme_interfaces():
    found = []
    for line in subprocess.run(['ifconfig'], capture_output=True, text=True).stdout.splitlines():
        if not line[0].isspace():
            name = line.split(':')[0]
        elif HOST_SUBNET in line:
            found.append(name)
    return found


async def connect(interface):
    sock = socket.socket()
    sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(interface))
    sock.setblocking(False)
    await asyncio.wait_for(asyncio.get_running_loop().sock_connect(sock, DEVICE), TIMEOUT)
    return await asyncio.open_connection(sock=sock)


async def model_name(interface):
    query = '{"device":{"model_name":null}}'
    try:
        reader, writer = await connect(interface)
        writer.write(f'POST /api/v2/self HTTP/1.1\r\nHost: {DEVICE[0]}\r\nConnection: close\r\n'
                     f'Content-Type: application/json\r\nContent-Length: {len(query)}\r\n\r\n{query}'.encode())
        reply = await asyncio.wait_for(reader.read(), TIMEOUT)
        writer.close()
    except (OSError, asyncio.TimeoutError):
        return interface
    match = re.search(rb'"model_name":"([^"]+)"', reply)
    return match[1].decode() if match else interface


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
    await asyncio.gather(copy(browser_reader, device_writer), copy(device_reader, browser_writer))


async def serve_page(reader, writer):
    await reader.readuntil(b'\r\n\r\n')
    interfaces = rme_interfaces()
    for interface in interfaces:
        if interface not in proxy_ports:
            proxy_ports[interface] = PAGE_PORT + 1 + len(proxy_ports)
            handler = functools.partial(forward_to_device, interface)
            await asyncio.start_server(handler, '127.0.0.1', proxy_ports[interface])

    names = await asyncio.gather(*map(model_name, interfaces))
    tabs = ''.join(f'<button onclick="show({n})">{name}</button>' for n, name in enumerate(names))
    frames = ''.join(f'<iframe src="http://127.0.0.1:{proxy_ports[i]}/"></iframe>' for i in interfaces)
    html = (PAGE % (tabs or 'No RME devices found on USB. Plug one in and reload.', frames)).encode()

    writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n'
                 + f'Content-Length: {len(html)}\r\n\r\n'.encode() + html)
    await writer.drain()
    writer.close()


async def main():
    server = await asyncio.start_server(serve_page, '127.0.0.1', PAGE_PORT)
    webbrowser.open(f'http://127.0.0.1:{PAGE_PORT}')
    await server.serve_forever()


asyncio.run(main())
