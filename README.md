# RME Configurator Switcher

Use the web configurators of several USB-connected RME devices at once, as tabs on one page.

RME devices such as the M-1610 Pro and M-1620 Pro serve their configurator over USB at
`http://172.20.0.1`. Every device uses that same address, so a browser can only reach one of
them. This tool gives each connected device its own local address and shows them side by side.

## Requirements

- macOS
- Python 3.8 or later (no extra packages)

## Usage

```
python3 rme_tabs.py
```

Your browser opens `http://127.0.0.1:8000` with one tab per connected device, labelled with
its model name. Reload the page after plugging in another device. Stop with Ctrl+C.

Each device is also reachable directly, at `http://127.0.0.1:8001`, `:8002` and so on.

## How it works

Each device appears to macOS as its own USB network interface. For every interface on the
`172.20.0.x` subnet, the tool:

1. opens a local port that forwards all traffic to `172.20.0.1` through that interface only;
2. asks the device for its model name via its JSON API (`POST /api/v2/self`);
3. adds a tab that frames the local port.
