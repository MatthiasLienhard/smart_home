from machine import Pin
import time
from machine import I2C, UART
#from bme280 import BME280
import dfplayer
from components import Light, Player, Button,MQTT_client, Sensor
import uasyncio as asyncio

mqtt=MQTT_client('frida')

bme = Sensor(mqtt=mqtt, topic='sensor')

led = Light(13, mqtt=mqtt, topic='lights', id=1)

light_switch1=Button(Pin(12, pull=Pin.PULL_UP))
light_switch1.release_func(led.toggle)

light_switch2=Button(Pin(27, pull=Pin.PULL_UP))
light_switch2.release_func(led.toggle)

uart=UART(2, 9600, tx=17, rx=16)
uart.init(9600, bits=8, parity=None, stop=1)
player=Player(uart=uart, busy_pin=Pin(15), volume=0.5 , mqtt=mqtt, topic='audio')

door_bell=Button(Pin(14, pull=Pin.PULL_UP))
door_bell.press_func(player.ring)

print('up and running')

loop = asyncio.get_event_loop()
loop.run_forever()