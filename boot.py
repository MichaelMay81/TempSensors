# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import machine
import gc
import webrepl

led = machine.Pin(16, machine.Pin.OUT)
led.off()

webrepl.start()
gc.collect()

led.on()