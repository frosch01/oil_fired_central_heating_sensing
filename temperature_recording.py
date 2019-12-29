#!/usr/bin/env python3

import re
import array
import time

import asyncio
import aiofiles

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

class W1_DS18S20:
    def __init__(self, w1_id):
        self.w1_id = w1_id
        self.path = '/sys/devices/w1_bus_master1/10-{0:012x}/w1_slave'.format(w1_id)
        
    async def get_therm(self):
        try:
            async with aiofiles.open(self.path, mode='r') as f:
                contents = await f.read()
                f.close()
            one_line = re.sub("\n", "", contents)
            temp = re.sub("^.*t=", "", one_line)
            temp_int = int(temp)
        except:
            temp_int = 99900
            await asyncio.sleep(0.75)
        return temp_int / 1000.;
    
class W1_DS24S13:
    def __init__(self, w1_id):
        self.w1_id = w1_id
        self.path = '/sys/devices/w1_bus_master1/3a-{0:012x}/state'.format(w1_id)
        
    async def get_state(self):
        async with aiofiles.open(self.path, mode='rb') as f:
            contents = await f.read()
            f.close()
        pioa = bool(contents[0] & 0x1)
        piob = bool(contents[0] & 0x4)
        return pioa, piob
        
class SSD1306_Display:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c)
        self.small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 14)
        self.display.fill(0)
        self.display.show()
        self.image = Image.new('1', (self.display.width, self.display.height))
        self.draw = ImageDraw.Draw(self.image)
        self.display.image(self.image)
        self.display.show()
        
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
    def __init__(self, display, loop):
        self.display = display
        self.current = 0
        self.active = False
        self.temp_list = [-1, -1]
        self.buttons = BonnetButtons(loop)
        self.handler = { ButtonEvent.UP    : self.up,
                         ButtonEvent.DOWN  : self.down,
                         ButtonEvent.LEFT  : self.left, 
                         ButtonEvent.RIGHT : self.right,
                         ButtonEvent.OK    : self.ok,
                         ButtonEvent.PLUS  : self.plus,
                         ButtonEvent.MINUS : self.minus}
        self.print()
        
    async def EventDispatcher(self):
        event = await self.buttons.GetEvent()
        self.handler[event]()
        self.print()
        
    def print(self):
        text = ""
        for value in self.temp_list:
            if value >= 0:
                text += "{:2} ".format(value)
            else:
                text += "-- "
                
        if self.active:
            self.display.print_line3(text, False)
            self.display.underline(2, self.current * 2, 2, self.current)
        else:
            self.display.print_line3(text)
        
    def up(self):
        pass
    
    def down(self):
        pass
    
    def left(self):
        if self.active:
            self.temp_list[self.current] = -1
            self.current -= 1
            if self.current < 0: self.current = len(self.temp_list) - 1
    
    def right(self):
        if self.active:
            self.temp_list[self.current] = -1
            self.current += 1
            if self.current >= len(self.temp_list):
                self.current = 0
    
    def ok(self):
        self.temp_list[self.current] = -1
        self.active = not self.active 
    
    def plus(self):
        if self.active:
            if self.temp_list[self.current] != -1:
                self.temp_list[self.current] += 1
            else:
                self.temp_list[self.current] = 30
    
    def minus(self):
        if self.active:
            if self.temp_list[self.current] != -1:
                self.temp_list[self.current] -= 1
                if self.temp_list[self.current] < 30:
                    self.temp_list[self.current] = -1
                    
class FlameDetector:
    def __init__(self, display):
        self.display = display
        self.active = False
        self.dio = W1_DS24S13(0x45ee2e)
        self.text = ""
        self.count = 0
            
    async def read_output_value(self):
        try:
            (fotosens, dummy) = await self.dio.get_state()
            if (fotosens): 
                text = "aus"
            else: 
                text =" an"
        except:
            text = "error"
            
        if True or self.text != text:
            self.text = text
            self.display.print_line2(progess[self.count % 4] + " " + text)
        self.count += 1
        
class ThermSensors:
    def __init__(self, display):
        self.display = display
        self.therm_sensors = [W1_DS18S20(0x803633136),
                              W1_DS18S20(0x803638c68),
                              W1_DS18S20(0x80373db9b)]
        self.count = 0
        self.therm_task_list = []
        self.print_task = None
        self.therm_value_list = []
    
    async def read_output_values(self):
        therm_value_list_new = []
        for task in self.therm_task_list:
            therm_value_list_new.append(await task)
        self.therm_task_list = []
        for sens in self.therm_sensors:
            self.therm_task_list.append(asyncio.create_task(sens.get_therm()))
        if self.print_task: await(self.print_task)
        self.therm_value_list = therm_value_list_new        
        asyncio.create_task(self.print_therm())
                
    async def print_therm(self):
        text = progess[self.count % 4] + " "
        for value in self.therm_value_list:
            text += "{:4.1f} ".format(value)
        self.display.print_line1(text)
        self.count += 1
    
async def output_detector(display):
    flame_detector = FlameDetector(display)
    while True:
        await flame_detector.read_output_value()
        await asyncio.sleep(1./4.)
        
async def input_manual(display):
    temp_input=ManualThermInput(display, asyncio.get_event_loop())
    while True:
        await temp_input.EventDispatcher()

async def output_therm(display):
    therm_sensors = ThermSensors(display)
    while True:
        await therm_sensors.read_output_values()
        
async def main():
    loop = asyncio.get_event_loop()
    display = SSD1306_Display()
    input_task = loop.create_task(input_manual(display))
    detector_task = loop.create_task(output_detector(display))
    therm_task = loop.create_task(output_therm(display))
    await(input_task)
    await(detector_task)
    await(therm_task)

if__name__== "__main__
    asyncio.run(main())
