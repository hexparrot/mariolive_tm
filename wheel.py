#!/usr/bin/env python3

# Author: William Dizon <wdchromium@gmail.com>

import asyncio
import logging

logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, "./joycontrol")

# switch controller imports
from joycontrol import logging_default as log, utils
from joycontrol.command_line_interface import ControllerCLI
from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState, button_push, button_press, button_release
from joycontrol.memory import FlashMemory
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server

# devices
from fcntl import ioctl
from evdev import InputDevice, categorize, ecodes
wheel_buttons = InputDevice('/dev/input/event1')
wheel_steering = open('/dev/input/js0', 'rb')

pedals_device = InputDevice('/dev/input/event2')

import array, struct

# Get the device name.
buf = array.array('B', [0] * 64)
ioctl(wheel_steering, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
js_name = buf.tobytes().rstrip(b'\x00').decode('utf-8')
print(('Device name: %s' % js_name))

async def buttons(device, controller_state, cli):
    async for ev in device.async_read_loop():
        #print(repr(ev))
        if ev.type == 1: # buttons
            if ev.code == 314:
                if ev.value: # left button push down 
                    await asyncio.create_task(button_press(controller_state, 'a'))
                elif not ev.value: # left button return up
                    await asyncio.create_task(button_release(controller_state, 'b'))
            if ev.code == 315:
                if ev.value: # right button push down 
                    await asyncio.create_task(button_press(controller_state, 'a'))
                elif not ev.value: # right button return up
                    await asyncio.create_task(button_release(controller_state, 'a'))
        elif ev.type == 3: # wheel
            await asyncio.create_task(cli.cmd_stick('l', 'horizontal', ev.value))

async def pedals(device, controller_state):
    async for ev in device.async_read_loop():
        #print(repr(ev))
        if ev.type == 3:
            if ev.code == 0:
                if ev.value: #any and all nonzero values > 0
                    await asyncio.create_task(button_press(controller_state, 'a'))
                else:
                    await asyncio.create_task(button_release(controller_state, 'a'))
            elif ev.code == 1:
                if ev.value: #any and all nonzero values > 0
                    await asyncio.create_task(button_press(controller_state, 'b'))
                else:
                    await asyncio.create_task(button_release(controller_state, 'b'))

async def _main():
    # Get controller name to emulate from arguments
    controller = Controller.from_arg('PRO_CONTROLLER')

    # prepare the the emulated controller
    factory = controller_protocol_factory(controller,
                                          spi_flash=FlashMemory(),
                                          reconnect = None)
    ctl_psm, itr_psm = 17, 19
    transport, protocol = await create_hid_server(factory,
                                                  reconnect_bt_addr="B8:8A:EC:FD:C7:F5",
                                                  ctl_psm=ctl_psm,
                                                  itr_psm=itr_psm,
                                                  device_id=None,
                                                  interactive=True)

    controller_state = protocol.get_controller_state()
    c_cli = ControllerCLI(controller_state)

    while True:
        await asyncio.gather(
            buttons(wheel_buttons, controller_state, c_cli),
            pedals(pedals_device, controller_state)
        )

if __name__ == '__main__':
    log.configure()
    loop = asyncio.get_event_loop()
    asyncio.run(_main())
