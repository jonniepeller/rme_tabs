#!/usr/bin/env python3
"""Run rme_tabs from the macOS menu bar. See README.md."""
import asyncio, threading, webbrowser
import rumps
import rme_tabs


class RMETabs(rumps.App):
    def __init__(self):
        super().__init__('RME', quit_button='Quit')
        self.menu = ['Open', 'Rescan Devices']
        # The proxies run on their own event loop, since the menu bar needs the main thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.servers = []

    @rumps.clicked('Open')
    def open(self, _=None):
        webbrowser.open(rme_tabs.PAGE_URL)

    @rumps.clicked('Rescan Devices')
    def rescan(self, _=None):
        found = asyncio.run_coroutine_threadsafe(self.restart(), self.loop).result()
        if found:
            self.open()
        else:
            rumps.alert('No RME devices found on USB', 'Plug one in and choose Rescan Devices.')

    async def restart(self):
        for server in self.servers:
            server.close()
            server.close_clients()
        self.servers, _ = await rme_tabs.start()
        return bool(self.servers)


if __name__ == '__main__':
    app = RMETabs()
    app.rescan()
    app.run()
