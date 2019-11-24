     
#import uasyncio as asyncio
import time
from machine import PWM, Pin, UART, I2C
from bme280 import BME280
import dfplayer
from utime import sleep_ms, ticks_ms, ticks_diff
from bme280 import BME280
from aswitch import Pushbutton
import  network


class MQTT_client():
    def __init__(self, topic,name='uPy_home_control', address='mqtt://192.168.178.65'):
        self.client = network.mqtt(name, address)        
        self.callback={}
        self.client.start()
        while self.client.status()[0]<2:
            time.sleep(.1)
        self.client.config(data_cb=lambda msg, fun=self._callback: fun(msg))
        self.topic=topic
        #self.client.config(self._callback)
        self.client.subscribe(topic+'/#')
        self.publish('status', 'booting')        
        
    def _callback(self, msg):
        print("[{}] Data arrived from topic: {}, Message:\n".format(msg[0], msg[1]), msg[2])
        if  msg[1] in self.callback:
            self.callback[msg[1]](msg[2])

    def add_callback(self, topic, callback):
        self.callback[self.topic+'/'+topic]=callback
        #self.client.subscribe(topic)
    
    def publish(self, topic, payload):
        self.client.publish(self.topic+'/'+topic, payload)

   
class Sensor(BME280):
    def __init__(self, i2c=None,mqtt=None, topic='sensor'):
        if i2c is None:
            i2c = I2C(sda=21, scl=22)
        super().__init__(i2c=i2c)
        self.mqtt=mqtt
        self.topic=topic
        if self.mqtt is not None:
            self.mqtt.add_callback(topic,self.mqtt_request)

    def mqtt_request(self, what):
        if self.mqtt is None:
            raise ValueError('mqtt not configured for this sensor')
        if what=='temperature':
            self.mqtt.publish(self.topic+'/temperature', str(self.read_temperature()/100))
        elif what=='humidity':
            self.mqtt.publish(self.topic+'/humidity', str(self.read_humidity()/1024))
        elif what=='pressure':
            self.mqtt.publish(self.topic+'/pressure', str(self.read_pressure()/25600))
        else: raise NotImplementedError('sensor has no {}'.format(what))



class Button(Pushbutton):#todo: add mqtt functionality
    pass


class Player(dfplayer.Player):
    #uart=UART(2, 9600, tx=17, rx=16)
    #uart.init(9600, bits=8, parity=None, stop=1)
    #player=dfplayer.Player(uart=uart, busy_pin=Pin(15) )
    #player.volume(0.5)
    #player.awaitvolume()
    #player.play(folderNum=1, trackNum=1)
    def __init__(self,uart, busy_pin, mqtt=None, topic=None, **kwargs):
        super().__init__(uart, busy_pin, **kwargs)
        self.mqtt=mqtt #currently not required, 
        self.topic=topic
        if self.mqtt is not None:
            self.mqtt.add_callback(topic+'/cmd',self.command)


    def command(self, cmd,par1=None, par2=None):
        if isinstance(cmd, str):
            cmd, par1, par2= [int(i,0) for i in cmd.split(',')]
        print('audio command {:02x} {:02x} {:02x}'.format(cmd, par1, par2))
        super().command(cmd, par1, par2)

    def ring(self, vol=1):
        print('ding dong')
        self.awaitconfig()
        self.playtime = ticks_ms()
        if self.playing():
            super().command(0x13, 0,251)
        else:
            super().command(0x12, 0,251)
    
    



class Light():
    def __init__(self,pin, mqtt=None, topic='lights', id=1):
        self.state=False
        if isinstance(pin, int):
            pin=Pin(pin)
        self.pwm = PWM(pin, duty=0)
        self.bri=100
        self.id=id
        self.mqtt=mqtt
        self.topic=topic
        if mqtt is not None:
            mqtt.add_callback('{}/{}'.format(self.topic,self.id) , self.set)

    def set(self,state=None, bri=None):
        if state is None:
            state=self.state
        if bri is None:
            bri=self.bri
        if isinstance(state, str):
            #parse mqtt cmd
            msg=state.split('/')
            state=msg[0]=='on'
            bri=int(msg[1])
        
        if state != self.state or bri != self.bri:
            print('light {} is now {}, bri {}'.format(self.id, ['off', 'on'][state], bri))
            self.state=state
            self.bri=bri            
            if state:
                self.pwm.duty(bri)
            else:
                self.pwm.duty(0)#off            
            if self.mqtt is not None:
                self.publish_status()
            

    def publish_status(self):
        self.mqtt.publish('{}/{}'.format(self.topic,self.id),'{}/{}'.format(['off', 'on'][self.state], self.bri))

    def toggle(self):
        self.set(state= not self.state)


    


