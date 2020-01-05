#!/usr/bin/env python3

import re
import time
import logging

import asyncio
import aiofiles

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

from event_collect_recorder import EventCollectRecorder

class W1_DS18S20:
    def __init__(self, w1_id, name = None):
        self.w1_id = w1_id
        self.path = '/sys/devices/w1_bus_master1/10-{0:012x}/w1_slave'.format(w1_id)
        self.name = name
        
    async def get_therm(self):
        async with aiofiles.open(self.path, mode='r') as f:
            contents = await f.read()
            f.close()
        one_line = re.sub("\n", "", contents)
        temp = re.sub("^.*t=", "", one_line)
        temp_int = int(temp)
        return temp_int / 1000.;
    
    def __str__(self):
        return "{}(name = {}, path = {})".format(self.__class__.__name__, self.name, self.path)
    
class W1_DS24S13:
    def __init__(self, w1_id, name=(None, None)):
        self.w1_id = w1_id
        self.path = '/sys/devices/w1_bus_master1/3a-{0:012x}/state'.format(w1_id)
        self.name = name
        
    async def get_state(self):
        async with aiofiles.open(self.path, mode='rb') as f:
            contents = await f.read()
            f.close()
        pioa = bool(contents[0] & 0x1)
        piob = bool(contents[0] & 0x4)
        return pioa, piob
        
    def __str__(self):
        return "{}(name = {}, path = {})".format(self.__class__.__name__, self.name, self.path)
    
class Bonnet_Display:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c)
        self.display.contrast(1)
        self.small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 14)
        self.image = Image.new('1', (self.display.width, self.display.height))
        self.draw = ImageDraw.Draw(self.image)
        self.display.image(self.image)
        self.display.show()
        
    def __del__(self):
        self.display.poweroff()
        
    def print_line1(self, text, update = True):
        self.draw.rectangle((0, 0, self.display.width, 15), outline=0, fill=0)
        self.draw.text((0,  0), text, font=self.small_font, fill=1)
        self.display.image(self.image)
        if update: self.display.show()
        
    def print_line2(self, text, update = True):
        self.draw.rectangle((0, 16, self.display.width, 31), outline=0, fill=0)
        self.draw.text((0, 16), text, font=self.small_font, fill=1)
        self.display.image(self.image)
        if update: self.display.show()
        
    def print_line3(self, text, update = True):
        self.draw.rectangle((0, 32, self.display.width, 47), outline=0, fill=0)
        self.draw.text((0, 32), text, font=self.small_font, fill=1)
        self.display.image(self.image)
        if update: self.display.show()
        
    def underline(self, line, start, len, fnum, update = True):
        character_width = 8
        space_width = 8
        y0 = 15 + line * 16
        x0 = start * character_width + fnum * space_width
        x1 = x0 + len * character_width
        polygon = [x0, y0, x1, y0]
        self.draw.line(polygon, width = 1, fill = 1)
        if update: self.display.show()
        
class ButtonEvent:
    _NONE  =  0
    _UP    = -1
    _DOWN  = -2
    _LEFT  = -3
    _RIGHT = -4
    _OK    = -5
    _PLUS  = -6
    _MINUS = -7
    
    PIN_ID_MAP = {17 : (_UP,    "UP"), 
                  22 : (_DOWN,  "DOWN"), 
                  27 : (_LEFT,  "LEFT"), 
                  23 : (_RIGHT, "RIGHT"), 
                   4 : (_OK,    "OK"), 
                   6 : (_PLUS,  "PLUS"), 
                   5 : (_MINUS, "MINUS")}
    
    @classmethod
    def GetPinList(cls):
        return list(cls.PIN_ID_MAP)
    
    def __init__(self, pin):
        self.num, self.name = ButtonEvent.PIN_ID_MAP[pin]
        
    def __eq__(self, other):
        """Override the default Equals behavior"""
        if type(other) == type(self):
            return self.num == other.num
        else:
            return self.num == other
        
    def __hash__(self):
        return self.num

ButtonEvent.UP    = ButtonEvent(17)
ButtonEvent.DOWN  = ButtonEvent(22)
ButtonEvent.LEFT  = ButtonEvent(27)
ButtonEvent.RIGHT = ButtonEvent(23)
ButtonEvent.OK    = ButtonEvent(4)
ButtonEvent.PLUS  = ButtonEvent(6)
ButtonEvent.MINUS = ButtonEvent(5)
    
class BonnetButtons:
    def __init__(self, loop):
        self.loop = loop
        self.event_queue = asyncio.Queue(maxsize=10)
        pin_list = ButtonEvent.GetPinList()
        GPIO.setup(pin_list, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        for pin in pin_list:
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=self.button_press_gpio_cb, bouncetime=200)
        
    def button_press_gpio_cb(self, channel):
        self.loop.call_soon_threadsafe(self.button_press_event_cb, channel)
        
    def button_press_event_cb(self, channel):
        event = ButtonEvent(channel)
        try:
            self.event_queue.put_nowait(event)
        except:
            print("{}: Event queue overflow".format(self.__class__.__name__))
            
    async def GetEvent(self):
        return await self.event_queue.get()

progess='|/-\\'

class ManualThermInput:
    def __init__(self, display, recorder, loop):
        self.default = 99
        self.display = display
        self.recorder = recorder
        self.current = 0
        self.active = False
        self.name_tuple = ("ManFlow", "ManReturn")
        self.value_list = [self.default] * len(self.name_tuple)
        self.buttons = BonnetButtons(loop)
        self.handler = { ButtonEvent.UP    : self.up,
                         ButtonEvent.DOWN  : self.down,
                         ButtonEvent.LEFT  : self.left, 
                         ButtonEvent.RIGHT : self.right,
                         ButtonEvent.OK    : self.ok,
                         ButtonEvent.PLUS  : self.plus,
                         ButtonEvent.MINUS : self.minus}
        self.update_display()
        for num, name in enumerate(self.name_tuple):
            recorder.register_event_source(name, num + 5, str(self.default))
        self.value_time = time.time()
        
    async def EventDispatcher(self):
        event = await self.buttons.GetEvent()
        self.value_time = time.time()
        self.handler[event]()
        self.update_display()
        
    def update_display(self):
        text = ""
        for value in self.value_list:
            if value < self.default:
                text += "{:2} ".format(value)
            else:
                text += "-- "
                
        if self.active:
            self.display.print_line3(text, False)
            self.display.underline(2, self.current * 2, 2, self.current)
        else:
            self.display.print_line3(text)
            
    def update_value(self, num, value):
        self.value_list[num] = value
        self.recorder.create_event(self.name_tuple[num], self.value_time, str(self.value_list[num]))
        
    def up(self):
        pass
    
    def down(self):
        pass
    
    def left(self):
        if self.active:
            self.update_value(self.current, self.default)
            self.current -= 1
            if self.current < 0: self.current = len(self.value_list) - 1
    
    def right(self):
        if self.active:
            self.update_value(self.current, self.default)
            self.current += 1
            if self.current >= len(self.value_list):
                self.current = 0
    
    def ok(self):
        self.update_value(self.current, self.default)
        self.active = not self.active 
    
    def plus(self):
        if self.active:
            if self.value_list[self.current] != self.default:
                self.update_value(self.current, self.value_list[self.current]+1)
            else:
                self.update_value(self.current, 30)
    
    def minus(self):
        if self.active:
            if self.value_list[self.current] != self.default:
                self.update_value(self.current, self.value_list[self.current]-1)
                if self.value_list[self.current] < 30:
                    self.update_value(self.current, self.default)
                    
class FlameDetector:
    def __init__(self, display, recorder):
        self.display = display
        self.recorder = recorder
        self.state = "False"
        self.dio = W1_DS24S13(0x45ee2e, ("Flame", None))
        recorder.register_event_source(self.dio.name, 4, "init")
        self.text = ""
        self.count = 0
        self.value_time = time.time()
        
    async def read_output_value(self):
        try:
            self.value_time = time.time()
            (flame_state, dummy) = await self.dio.get_state()
            if flame_state: 
                text = "aus"
                self.state = "off"
            else: 
                text =" an"
                self.state = "on"
        except FileNotFoundError:
            self.state = "device_error"
            text = "sens"
        except PermissionError:
            self.state = "permission_error"
            text = "perm"
            
        self.recorder.create_event(self.dio.name, self.value_time, self.state)
            
        self.display.print_line2(progess[self.count % 4] + " " + text)
        if self.text != text:
            self.text = text
        self.count += 1
        
class ThermSensors:
    def __init__(self, display, recorder):
        sensor_id_name_tuple = ((0x803633136, "Flow"),
                                (0x803638c68, "Return"),
                                (0x80373db9b, "Outside"))
        self.display = display
        self.recorder = recorder
        self.sampling_time = time.time()
        self.value_time = self.sampling_time
        self.count = 0
        self.task_list = []
        self.print_task = None
        self.value_list = [None] * len(sensor_id_name_tuple)
        self.sensor_list=[]
        for num, id_name in enumerate(sensor_id_name_tuple):
            id, name = id_name
            self.sensor_list.append(W1_DS18S20(id, name))
            recorder.register_event_source(name, num + 1, "99.999")
    
    async def terminate(self):
        for task in self.task_list:
            try:
                await task
            except:
                pass
        if self.print_task: 
            try:
                await self.print_task
            except:
                pass
            
    async def read_output_values(self):
        therm_value_list_new = []
        therm_value_time_new = self.sampling_time
        for task, sens in zip(self.task_list, self.sensor_list):
            try:
                therm_value = await(task)
                therm_value_list_new.append(therm_value)
            except (FileNotFoundError, PermissionError) as handled_exp:
                therm_value = "99.999"
                therm_value_list_new.append(handled_exp)
            self.recorder.create_event(sens.name, therm_value_time_new, str(therm_value))
        self.task_list = []
        for sens in self.sensor_list:
            self.task_list.append(asyncio.create_task(sens.get_therm()))
        self.sampling_time = time.time()
        if self.print_task: await self.print_task
        self.value_list = therm_value_list_new
        self.value_time = therm_value_time_new
        self.print_task = asyncio.create_task(self.print_therm())
                    
    async def print_therm(self):
        text = progess[self.count % 4] + " "
        for value in self.value_list:
            if isinstance(value, float):
                text += "{:4.1f} ".format(value)
            elif isinstance(value, FileNotFoundError):
                text += "sens "
            elif isinstance(value, PermissionError):
                text += "perm"
            else:
                text += " err "
        self.display.print_line1(text)
        self.count += 1
    
async def output_detector(display, recorder):
    flame_detector = FlameDetector(display, recorder)
    try:
        while True:
            await flame_detector.read_output_value()
            await asyncio.sleep(1./4.)
    except asyncio.CancelledError:
        pass
        
async def input_manual(display, recorder):
    therm_input=ManualThermInput(display, recorder, asyncio.get_event_loop())
    try:
        while True:
            await therm_input.EventDispatcher()
    except asyncio.CancelledError:
        pass

async def output_therm(display, recorder):
    therm_sensor_list = ThermSensors(display, recorder)
    try:
        while True:
            await therm_sensor_list.read_output_values()
    except asyncio.CancelledError:
        await therm_sensor_list.terminate()
        
async def main():
    loop = asyncio.get_event_loop()
    display = Bonnet_Display()
    recorder = EventCollectRecorder("./heating.log")
    input_task = loop.create_task(input_manual(display, recorder))
    detector_task = loop.create_task(output_detector(display, recorder))
    therm_task = loop.create_task(output_therm(display, recorder))
    try:
        await asyncio.gather(input_task, detector_task, therm_task)
    except asyncio.CancelledError:
        pass
    
if __name__== "__main__":
    #logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGracefully terminated on user request")
