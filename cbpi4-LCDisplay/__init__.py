# -*- coding: utf-8 -*-
import time
from time import gmtime, strftime
from datetime import datetime
import socket
import fcntl
import struct
import logging
import asyncio
import json
from .RPLCD.i2c import CharLCD
from time import strftime
from cbpi.api import *
from cbpi.api.config import ConfigType
from cbpi.controller.step_controller import StepController
from cbpi.api.dataclasses import Props, Step
from cbpi.api.dataclasses import Fermenter, Kettle, Props
from cbpi.api.step import StepState
from cbpi.api.base import CBPiBase
from aiohttp import web
import os, re

# LCDVERSION = '5.0.01'
#
# this plug in is made for CBPI4. Do not use it in CBPI3.
# The LCD-library and LCD-driver are taken from RPLCD Project version 1.0. The documentation:
# http://rplcd.readthedocs.io/en/stable/ very good and readable. Git is here: https://github.com/dbrgn/RPLCD.
# LCD_Address should be something like 0x27, 0x3f etc.
# See in Craftbeerpi-UI (webpage of CBPI4) settings .
# To determine address of LCD use command prompt in Raspi and type in:
# sudo i2cdetect -y 1 or sudo i2cdetect -y 0
#
# Assembled by JamFfm
# 02.04.2021


logger = logging.getLogger(__name__)
DEBUG = True  # turn True to show (much) more debug info in app.log
BLINK = False  # start value for blinking the beerglass during heating only for single mode
global lcd
# beerglass symbol
bierkrug = (
    0b11100,
    0b00000,
    0b11100,
    0b11111,
    0b11101,
    0b11101,
    0b11111,
    0b11100
)
# cooler symbol should look like snowflake but is instead a star. I use 3 of them like in refrigerators
cool = (
    0b00100,
    0b10101,
    0b01110,
    0b11111,
    0b01110,
    0b10101,
    0b00100,
    0b00000
)

class LCDisplay(CBPiExtension):
    def __init__(self, cbpi):
        self.cbpi = cbpi
        self.controller : StepController = cbpi.step
        self.kettle_controller : KettleController = cbpi.kettle
        self.fermenter_controller : FermentationController = cbpi.fermenter

        self._task = asyncio.create_task(self.run())

    async def run(self):
        plugin = await self.cbpi.plugin.load_plugin_list("cbpi4-LCDisplay")
        self.version=plugin[0].get("Version","0.0.0")

        self.LCDisplay_update = self.cbpi.config.get("LCDisplay_update", None)

        logger.info('LCDisplay - Starting background task')

        address1, charmap, refresh, mode, sensor_type, single_kettle_id = await self.set_lcd_settings()
        
        address = int(address1, 16)
        if DEBUG: logger.info('LCDisplay - LCD address %s %s' % (address, address1))

        if DEBUG: logger.info('LCDisplay - LCD charmap: %s' % charmap)
        global lcd
        try:
            lcd = CharLCD(i2c_expander='PCF8574', address=address, port=1, cols=20, rows=4, dotsize=8, charmap=charmap,
                      auto_linebreaks=True, backlight_enabled=True)
            lcd.create_char(0, bierkrug)    # u"\x00"  -->beerglass symbol
            lcd.create_char(1, cool)        # u"\x01"  -->Ice symbol
        except:
            if DEBUG: logger.info('LCDisplay - Error: LCD object not set, wrong LCD address: {}'.format(e))
        pass


        if DEBUG: logger.info('LCDisplay - LCD object set')

        if DEBUG: logger.info('LCDisplay - refresh %s' % refresh)

        if DEBUG: logger.info('LCDisplay - single_kettle_id %s' % single_kettle_id)

        counter = 0
        line_setting = 1

        while True:
            fermenters = await self.get_active_fermenter()
#            logger.info(fermenters)
            # this is the main code repeated constantly
            activity, name = await self.get_activity()
            if activity is None and len(fermenters) == 0:
                await self.show_standby()
            elif activity is None and len(fermenters) != 0:
                if counter > (len(fermenters)-1):
                        counter = 0
                        line_setting = -1*line_setting
                await self.show_fermenters(fermenters, counter, refresh, line_setting)
                counter +=1
            else:
#                logging.info(activity)
#                logging.info(name)
                await self.show_activity(activity, name)
#            await asyncio.sleep(refresh)
        pass

    async def get_activity(self):
        active_step = None
        name = ""
        data=self.controller.get_state()
        try:
            name = data['basic']['name']
            steps=data['steps']
            for step in steps:
                if step['status'] == "A":
                    active_step=step
        except:
           pass 

        return active_step,name
        await asyncio.sleep(1)

    async def show_standby(self):
        ip = await self.set_ip()
        cbpi_version = self.cbpi.version
        try:
            versionlength=len(cbpi_version)
        except:
            versionlength=5
        breweryname = await self.get_breweryname()
        line1="CBPi".ljust(20-versionlength)+cbpi_version
        lcd._set_cursor_mode('hide')
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line1.ljust(20))
        lcd.cursor_pos = (1, 0)
        lcd.write_string(("%s" % breweryname).ljust(20))
        lcd.cursor_pos = (2, 0)
        lcd.write_string(("IP: %s" % ip).ljust(20))
        lcd.cursor_pos = (3, 0)
        lcd.write_string((strftime("%Y-%m-%d %H:%M:%S", time.localtime())).ljust(20))
#        logging.info("Show Standby")
        await asyncio.sleep(1)

    async def show_fermenters(self,fermenters, index, refresh, line_setting):
        fermenter = fermenters[index]
        lines = ["","","",""]
        status = fermenter['status']
        lcd_unit = self.cbpi.config.get("TEMP_UNIT", "C")
        lines[0] = (fermenter['name']).ljust(20)[:20]
        lines[1] = (fermenter['BrewName']).ljust(20)[:20]
        stepname=fermenter['step_name'] if fermenter['step_name'] is not None else "Step"
        length_summary=len(fermenter['step_summary'])
        length_summary = 8 if length_summary > 8 else length_summary
        lines[2] = ((stepname[:11]+"|").ljust(20-length_summary)+fermenter['step_summary']).ljust(20)[:20]
        target_temp = fermenter['target_temp']
        sensor_value = fermenter['sensor_value']
        if sensor_value == None:
            lines[3] = ("Set/Act:%5.1f/ N/A%s%s" % (float(target_temp), u"°", lcd_unit))[:20]
        else:
            lines[3] = ("Set/Act:%5.1f/%4.1f%s%s" % (float(target_temp), float(sensor_value), u"°", lcd_unit))[:20]
        if line_setting == -1:
            if fermenter['sensor2_value'] is not None and fermenter['sensor2_value'] != 0: 
                line_value = float(fermenter['sensor2_value'])
                line_unit = fermenter['sensor2_units']
                if line_unit == "SG":
                    lines[3]=("Spindle: %1.3f%s" % (line_value,line_unit)).ljust(20)[:20]
                else:
                    lines[3]=("Spindle: %2.1f%s" % (line_value, line_unit)).ljust(20)[:20]
            else:
                lines[3]=("Spindle: Waiting").ljust(20)[:20]
#        logging.info(lines)
        await self.write_lines(lines, status)
#        logging.info("Show Fermenter Activity")
        await asyncio.sleep(refresh) 

        

    async def show_activity(self, activity, name):
        lines = ["","","",""]
        lcd_unit = self.cbpi.config.get("TEMP_UNIT", "C")
        active_step_props=activity['props']
        try:
            target_temp = float(active_step_props['Temp'])
        except:
            target_temp = 0
        try:
            kettle_ID = active_step_props['Kettle']
        except:
            kettle_ID = None
        try:
            sensor_ID = active_step_props['Sensor']
        except:
            sensor_ID = None
        try:
            kettle = self.cbpi.kettle.find_by_id(kettle_ID)
            heater = self.cbpi.actor.find_by_id(kettle.heater)
            heater_state = heater.instance.state
        except:
            kettle = None
            heater = None
            heater_state = False

        step_state = str(activity['state_text'])
        try:
            if (sensor_ID is not None) and sensor_ID != "":
                sensor_value = self.cbpi.sensor.get_sensor_value(sensor_ID).get('value')
            else:
                sensor_value = 0
        except:
            sensor_value = 0
        if kettle is not None:
            kettle_name = str(kettle.name)
        else:
            kettle_name = "N/A"

        step_name = str(activity['name'])
        boil_check = step_name.lower()
        if boil_check.find("boil") != -1: # Boil Step
            try:
                time_left = sum(x * int(t) for x, t in zip([3600, 60, 1], step_state.split(":"))) 
            except:
                time_left = None
            next_hop_alert = None
            if time_left is not None:
                next_hop_alert = await self.get_next_hop_timer(active_step_props, time_left)

            lines[0] = ("%s" % step_name).ljust(20)
            lines[1] = ("%s %s" % (kettle_name.ljust(12)[:11], step_state)).ljust(20)[:20]
            lines[2] = ("Set|Act:%4.0f°%5.1f%s%s" % (float(target_temp), float(sensor_value), "°", lcd_unit))[:20] 
            if next_hop_alert is not None:
                lines[3] = ("Add Hop in: %s" % next_hop_alert)[:20]
            else:
                lines[3] = ("                    ")[:20]

        else:
            lines[0] = ("%s" % step_name).ljust(20)
            lines[1] = ("%s %s" % (kettle_name.ljust(12)[:11], step_state)).ljust(20)[:20]
            lines[2] = ("Targ. Temp:%6.2f%s%s" % (float(target_temp), "°", lcd_unit)).ljust(20)[:20]
            try:
                lines[3] = ("Curr. Temp:%6.2f%s%s" % (float(sensor_value), "°", lcd_unit)).ljust(20)[:20]
            except:
                logger.info(
                    "LCDDisplay  - single mode current sensor_value exception %s" % sensor_value)
                lines[3] = ("Curr. Temp: %s" % "No Data")[:20]
        status = 1 if heater_state == True else 0
#        logging.info(lines)
        await self.write_lines(lines,status)
#        logging.info("Show Brewing Activity")
        await asyncio.sleep(1)

    async def write_lines(self,lines,status=0):
        lcd._set_cursor_mode('hide')
        lcd.cursor_pos = (0, 0)
        lcd.write_string(lines[0])
        if status == 1:
            lcd.cursor_pos = (0, 18)
            lcd.write_string(u" \x00")
        if status == 2:
            lcd.cursor_pos = (0, 18)
            lcd.write_string(u" \x01")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(lines[1])
        lcd.cursor_pos = (2, 0)
        lcd.write_string(lines[2])
        lcd.cursor_pos = (3, 0)
        lcd.write_string(lines[3])


    async def get_next_hop_timer(self, active_step, time_left):
        hop_timers = []
        for x in range(1, 6):
            try:
                hop = int((active_step['Hop_' + str(x)])) * 60
            except:
                hop = None
            if hop is not None:
                hop_left = time_left - hop
                if hop_left > 0:
                    hop_timers.append(hop_left)
#                    if DEBUG: logger.info("LCDDisplay  - get_next_hop_timer %s %s" % (x, str(hop_timers)))
                pass
            pass
        pass

        if len(hop_timers) != 0:
            next_hop_timer = time.strftime("%H:%M:%S", time.gmtime(min(hop_timers)))
        else:
            next_hop_timer = None
        return next_hop_timer
        pass


    async def set_ip(self):
        if await self.get_ip('wlan0') != 'Not connected':
            ip = await self.get_ip('wlan0')
        elif await self.get_ip('eth0') != 'Not connected':
            ip = await self.get_ip('eth0')
        elif await self.get_ip('enxb827eb488a6e') != 'Not connected':
            ip = await self.get_ip('enxb827eb488a6e')
        else:
            ip = 'Not connected'
        pass
        return ip

    async def get_ip(self, interface):
        ip_addr = 'Not connected'
        so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            ip_addr = socket.inet_ntoa(
                fcntl.ioctl(so.fileno(), 0x8915, struct.pack('256s', bytes(interface.encode())[:15]))[20:24])
        except:
            return ip_addr
        finally:
            return ip_addr

    async def get_breweryname(self):
        brewery = self.cbpi.config.get("BREWERY_NAME", None)
        if brewery is None:
            brewery = "no name"
        return brewery
        pass

    async def set_lcd_settings(self):
        # global lcd_address
        lcd_address = self.cbpi.config.get("LCD_address", None)
        lcd_charmap = self.cbpi.config.get("LCD_Charactermap", None)
        ref = self.cbpi.config.get('LCD_Refresh', None)
        mode = self.cbpi.config.get('LCD_Display_Mode', None)
        sensor_type = self.cbpi.config.get('LCD_Display_Sensortype', None)
        kettle_id = self.cbpi.config.get('LCD_Singledisplay_Kettle', None)

        if lcd_address is None:
            logger.info("LCD_Address added")
            try:
                await self.cbpi.config.add("LCD_address", '0x27', type=ConfigType.STRING,
                                           description="LCD address like 0x27 or 0x3f, CBPi reboot required",
                                           source='cbpi4-LCDisplay')
                lcd_address = self.cbpi.config.get("LCD_address", None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    await self.cbpi.config.add("LCD_address", lcd_address, type=ConfigType.STRING,
                                           description="LCD address like 0x27 or 0x3f, CBPi reboot required",
                                           source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass  

        if lcd_charmap is None:
            logger.info("LCD_Charactermap added")
            try:
                await self.cbpi.config.add("LCD_Charactermap", 'A00', type=ConfigType.SELECT, 
                                           description="LCD Charactermap like A00, A02, CBPi reboot required",
                                           options=[{"label": "A00", "value": "A00"}, {"label": "A02", "value": "A02"}],
                                           source='cbpi4-LCDisplay')
                lcd_charmap = self.cbpi.config.get("LCD_Charactermap", None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("------------------------------------------------------------------------------------")
                    await self.cbpi.config.add("LCD_Charactermap", lcd_charmap, type=ConfigType.SELECT, 
                                               description="LCD Charactermap like A00, A02, CBPi reboot required",
                                           options=[{"label": "A00", "value": "A00"}, {"label": "A02", "value": "A02"}],
                                           source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass

        if ref is None:
            logger.info("LCD_Refresh added")
            try:
                await self.cbpi.config.add('LCD_Refresh', 3, type=ConfigType.SELECT,
                                           description= 'Time to remain till next display in sec, NO! CBPi reboot required', 
                                           options=[{"label": "1s", "value": 1}, {"label": "2s", "value": 2},
                                                        {"label": "3s", "value": 3}, {"label": "4s", "value": 4},
                                                        {"label": "5s", "value": 5}, {"label": "6s", "value": 6}],
                                                        source='cbpi4-LCDisplay')
                ref = self.cbpi.config.get('LCD_Refresh', None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("**************************************************************************************")
                    await self.cbpi.config.add('LCD_Refresh', ref, type=ConfigType.SELECT,
                                           description= 'Time to remain till next display in sec, NO! CBPi reboot required', 
                                           options=[{"label": "1s", "value": 1}, {"label": "2s", "value": 2},
                                                        {"label": "3s", "value": 3}, {"label": "4s", "value": 4},
                                                        {"label": "5s", "value": 5}, {"label": "6s", "value": 6}],
                                                        source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass

        if mode is None:
            logger.info("LCD_Display_Mode added")
            try:
                await self.cbpi.config.add('LCD_Display_Mode', 'Multidisplay', type=ConfigType.SELECT,
                                           description='select the mode of the LCD Display, consult readme, NO! CBPi reboot required',
                                           options=[{"label": "Multidisplay", "value": 'Multidisplay'},
                                                        {"label": "Singledisplay", "value": 'Singledisplay'},
                                                        {"label": "Sensordisplay", "value": 'Sensordisplay'}],
                                                        source='cbpi4-LCDisplay')
                mode = self.cbpi.config.get('LCD_Display_Mode', None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                    await self.cbpi.config.add('LCD_Display_Mode', 'Multidisplay', type=ConfigType.SELECT,
                                           description='select the mode of the LCD Display, consult readme, NO! CBPi reboot required',
                                           options=[{"label": "Multidisplay", "value": 'Multidisplay'},
                                                        {"label": "Singledisplay", "value": 'Singledisplay'},
                                                        {"label": "Sensordisplay", "value": 'Sensordisplay'}],
                                                        source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass

        if sensor_type is None:
            logger.info("LCD_Display_Sensortype added")
            try:
                await self.cbpi.config.add('LCD_Display_Sensortype', 'ONE_WIRE_SENSOR', type=ConfigType.SELECT,
                                           description='select the type of sensors to be displayed in LCD, consult readme, '
                                           'NO! CBPi reboot required',
                                           options=[{"label": "ONE_WIRE_SENSOR", "value": 'ONE_WIRE_SENSOR'},
                                            {"label": "iSpindel", "value": 'iSpindel'},
                                            {"label": "MQTT_SENSOR", "value": 'MQTT_SENSOR'},
                                            {"label": "iSpindel", "value": 'iSpindel'},
                                            {"label": "eManometer", "value": 'eManometer'},
                                            {"label": "PHSensor", "value": 'PHSensor'},
                                            {"label": "Http_Sensor", "value": 'Http_Sensor'}],
                                            source='cbpi4-LCDisplay')
                sensor_type = self.cbpi.config.get('LCD_Display_Sensortype', None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("/////////////////////////////////////////////////////////////////////////////////////")
                    await self.cbpi.config.add('LCD_Display_Sensortype', 'ONE_WIRE_SENSOR', type=ConfigType.SELECT,
                                           description='select the type of sensors to be displayed in LCD, consult readme, '
                                           'NO! CBPi reboot required',
                                           options=[{"label": "ONE_WIRE_SENSOR", "value": 'ONE_WIRE_SENSOR'},
                                            {"label": "iSpindel", "value": 'iSpindel'},
                                            {"label": "MQTT_SENSOR", "value": 'MQTT_SENSOR'},
                                            {"label": "iSpindel", "value": 'iSpindel'},
                                            {"label": "eManometer", "value": 'eManometer'},
                                            {"label": "PHSensor", "value": 'PHSensor'},
                                            {"label": "Http_Sensor", "value": 'Http_Sensor'}],
                                            source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass                    

        if kettle_id is None:
            logger.info("LCD_Singledisplay_Kettle added")
            try:
                await self.cbpi.config.add('LCD_Singledisplay_Kettle', '', type=ConfigType.KETTLE,
                                           description='select the type of sensors to be displayed in LCD, consult readme, '
                                           'NO! CBPi reboot required',
                                           source='cbpi4-LCDisplay')
                kettle_id = self.cbpi.config.get('LCD_Singledisplay_Kettle', None)
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass
        else:
            if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
                try:
                    logging.error("#######################################################################################")
                    await self.cbpi.config.add('LCD_Singledisplay_Kettle', '', type=ConfigType.KETTLE,
                                           description='select the type of sensors to be displayed in LCD, consult readme, '
                                           'NO! CBPi reboot required',
                                           source='cbpi4-LCDisplay')
                except Exception as e:
                    logger.warning('Unable to update config')
                    logger.warning(e)
                pass
        
        if self.LCDisplay_update == None or self.LCDisplay_update != self.version:
            try:
                await self.cbpi.config.add("LCDisplay_update", self.version, type=ConfigType.STRING,
                                           description="LCD address version",
                                           source='hidden')
            except Exception as e:
                logger.warning('Unable to update config')
                logger.warning(e)
            pass

        return lcd_address, lcd_charmap, ref, mode, sensor_type, kettle_id


    async def get_active_fermenter(self):
        fermenters = []
        try:
            self.fermenter = self.fermenter_controller.get_state()
        except:
            self.fermenter = None
        if self.fermenter is not None:
            for id in self.fermenter['data']:
                    status = 0
                    fermenter_id=(id['id'])
                    self.fermenter=self.cbpi.fermenter._find_by_id(fermenter_id)
                    heater = self.cbpi.actor.find_by_id(self.fermenter.heater)
                    steps = self.fermenter.steps
                    step_name = None
                    step_summary = None
                    for step in steps:
                        if step.status == StepState.ACTIVE:
                            step_name = step.name
                            try:
                                step_summary = str(step.instance.summary).replace(" ","")
                                if step_summary.find("Waiting") != -1:
                                    step_summary="Waiting   "
                                if step_summary.find("Ramping") != -1:
                                    step_summary="Ramping   "
                            except:
                                pass
                    try:
                        heater_state = heater.instance.state
                    except:
                        heater_state= False

                    cooler = self.cbpi.actor.find_by_id(self.fermenter.cooler)

                    try:
                        cooler_state = cooler.instance.state
                    except:
                        cooler_state= False

                    try:
                        state = self.fermenter.instance.state
                    except:
                        state = False
                    if heater_state == True:
                        status = 1
                    elif cooler_state == True:
                        status = 2
                    name = id['name']
                    target_temp = id['target_temp']
                    sensor = id['sensor']
                    try:
                        BrewName = id['brewname']
                    except:
                        BrewName = "" 
                    try:
                        if (sensor is not None) and sensor != "":
                            sensor_value = self.cbpi.sensor.get_sensor_value(sensor).get('value')
                        else:
                            sensor_value = None
                    except:
                        sensor_value = None
                    try:
                        sensor2 = id['props']['sensor2']
                    except:
                        sensor2 = None
                    try:
                        if (sensor2 is not None) and sensor2 !="":
                            sensor2_value = self.cbpi.sensor.get_sensor_value(sensor2).get('value')
                            sensor2_props = self.cbpi.sensor.find_by_id(sensor2)
                            sensor2_units = sensor2_props.props['Units']
                        else:
                            sensor2_value = None
                            sensor2_units = None
                    except:
                        sensor2_value = None
                        sensor2_units = ""
                    if state != False:
                        fermenter_string={'name': name, 'BrewName':BrewName, 'step_name': step_name, 'step_summary': step_summary[0:-3], 'target_temp': target_temp, 'sensor_value': sensor_value, 'sensor2': sensor2, 'sensor2_value': sensor2_value, "status": status, "sensor2_units": sensor2_units}
                        fermenters.append(fermenter_string)
        #logging.info(fermenters)
        return fermenters


def setup(cbpi):
    cbpi.plugin.register("LCDisplay", LCDisplay)
