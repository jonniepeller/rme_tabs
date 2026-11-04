# RME Tabs

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
its model name. Devices are found once, at startup: after plugging in, unplugging or replugging
a device, stop with Ctrl+C and run the tool again. Reloading the page is always safe.

Each device is also reachable directly, at `http://127.0.0.1:8001`, `:8002` and so on, in
order of interface name. The tool prints this list when it starts.

## Menu bar app

`RME Tabs.app` runs the same tool from the menu bar, with no Dock icon. Its **RME** menu has
**Open** (show the page), **Rescan Devices** (use after plugging, unplugging or replugging)
and **Quit**. To build it, install it in Applications and launch it, run:

```
./install.sh
```

Run it again after any change to rebuild and replace the installed app; a running copy is
quit first. The first run sets up `.venv` with rumps and PyInstaller. It is not signed with a
Developer ID, so open it the first time with right-click → Open. macOS then asks to let it
find devices on your local network: allow this, then choose **Rescan Devices** if the tabs
show interface names (`en14`) instead of model names.

## How it works

Each device appears to macOS as its own USB network interface. For every interface on the
`172.20.0.x` subnet found at startup, the tool:

1. opens a local port that forwards all traffic to `172.20.0.1` through that interface only;
2. asks the device for its model name via its JSON API (`POST /api/v2/self`);
3. adds a tab that frames the local port.
