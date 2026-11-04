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
        self.proxy = rme_tabs.Proxy()

    @rumps.clicked('Open')
    def open(self, _=None):
        webbrowser.open(rme_tabs.PAGE_URL)

    @rumps.clicked('Rescan Devices')
    def rescan(self, _=None):
        try:
            devices = asyncio.run_coroutine_threadsafe(self.restart(), self.loop).result()
        except OSError as error:
            rumps.alert('RME Tabs could not start', f'{error}\n\nQuit anything else using it, then choose Rescan Devices.')
            return
        if not devices:
            rumps.alert('No RME devices found on USB', 'Plug one in and choose Rescan Devices.')
            return
        self.open()
        if any(device.name is None for device in devices):
            rumps.alert('Some devices did not reply',
                        'If macOS asked to let RME Tabs find devices on your local network, allow it, '
                        'then choose Rescan Devices.')

    async def restart(self):
        self.proxy.stop()
        return await self.proxy.start()


if __name__ == '__main__':
    app = RMETabs()
    app.rescan()
    app.run()
