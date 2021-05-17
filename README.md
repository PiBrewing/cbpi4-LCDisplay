![](https://img.shields.io/badge/CBPi%204%20addin-functionable-green.svg)  ![](https://img.shields.io/github/license/JamFfm/craftbeerpiLCD.svg?style=flat) ![](https://img.shields.io/github/last-commit/JamFfm/craftbeerpiLCD.svg?style=flat) ![](https://img.shields.io/github/release-pre/JamFfm/craftbeerpiLCD.svg?style=flat)

# **LCD add-on for CraftBeerPi 4**

![](https://github.com/JamFfm/cbpi4-LCDisplay/blob/master/LCDPhoto.jpg "LCDDisplay Default Display")

With this add-on you can display your Brewing steps temperatures on a 20x4 i2c LCD Display.
In the future: In addition you can display the target-temperature and current-temperature of each fermenter.

This addon only works with I2C connected LCD Displays.

## Installation

**Wiring:**

Display|       PI
-------|--------------------
SDA    |  Pin 3 GPIO02(SDA1)
SCL    |  Pin 5 GPIO03(SDL1)
VCC    |  Pin 2 Power 5V
GND    |  Pin 6 GND

**I2C Configuration:**

Ensure to activate the I2C connection in Raspi configuration.

**Software installation:**

Download and install this plugin via the CraftBeerPi user interface. It is called LCDisplay.

A reboot is necessary.

## Configuration

At least configure your i2c address in the settings menu. Have a look at this documentation.


There are different modes:

**Default display**
--------------

If no brewing process is running the LCD Display will show

- CraftBeerPi-Version 
- Brewery-name
- Current IP adress 
- Current date/time

**Multidisplay mode**
-----------------

- The script will loop through your kettles and display the target and current temperature. 
- If heater is on, a beerglas symbol will appear in the first row on the right side (not flashing).
- Use refresh parameter in settings to slow don or speed up the kettle changes.
- When target-temperature is reached it displays the remaining time of the step (rest) too.
- **If the step name got the string "boil" in its name the remaining time to the next hop addition 
will be displayed.** Otherwise the display of a boil type step looks the same as all the other steps.
  


**Single mode**
-----------

- Only displays one kettle but reacts a little bit faster on temperature changes. 
- It displays the remaining time of the step (rest) when target temperature is reached.
- A small beerglas is flashing on/off in the first row on the right side to indicate that the heater is on.
- **If the step name got the string "boil" in its name the remaining time to the next hop addition 
will be displayed.** Otherwise the display of a boil type step looks the same as all the other steps.


**Sensor mode**
-----------

- Only displays the values and names of the sensortype.
- E.g. a iSpindel sensor can display temperature, gravity, battery etc. These values with 
corresponding sensorname is shown.
- The sensortype to be displayed is changed in settings section.
- If there is a missing sensor like from a future addon it can be added by typing in the code of function
"set_sensortype_for_sensor_mode" in the init.py file. 
- there is only OneWire and CustomSensor functioning (even some more are selectable)
- This is fixed in the future when ConfigType.SENSOR ist fixed by Manuel




**Fermenter mode: not implemented**
--------------
- Pretty much the same as multidisplay for all fermenter.
- Starts automatically if there is no Brewstep running and a active fermenterstep
- Displays the brew-name, fermenter-name, target-temperature, current-temperature of each fermenter.
- If the heater or cooler of the fermenter is on it will show a symbol.
A beerglas detects heater is on, * means cooler in on.
- The remaining time for each fermenter is shown like in weeks, days, hours. 
- Fermenter mode starts when a fermenter-step of any of the fermenter is starting and no brewing step is running(most likely)
- if there is a iSpindel sensor the Gravity is displayed at the corresponding fermenter.

Parameter
---------

There are several parameter to change in the **settings** menu:


**LCD_Address:**    
This is the address of the LCD module. You can detect it by 
using the following command in the commandbox of the Raspi:   
- sudo i2cdetect -y 1 
or 
- sudo i2cdetect -y 0.

Default is 0x27.


**LCD_Charactermap:**     
Changes value between A00 and A02. This is a character map build in by factory into the LCD. 
Most likely you get a LCD with A00 when you by it in China. A00 has got most of the European letters, and a lot 
of Asia letters. For germans the ÄÖÜß is missing in A00. In A02 there are more European letters incl. ÄÖÜß.
Therefore, the addon distinguish between the charmaps. 
In case A00 it substitutes ÄÜÖß with custom made symbols which represent these letters.
In case A02 the addon skips substitution. If you notice strange letters try to change this parameter.
Default is "A00".

 
**LCD_Display_Mode:**     
Changes between the 3 modes. Default is Multidisplay:
- Multidisplay 
- Singledisplay
- Sensordisplay


**LCD_Display_Sensortype:**     
Changes between sensortype (is like family of same sensors) which will be displayed in 
the sensormode (sensordisplay). Default is OneWire sensors. If there is more than one sensor of same sensor 
type the display toggles between the sensors


**LCD_Refresh:**		  
In Multidisplay and Sensor mode this is the time to wait until switching to next displayed kettle. 
Default is 3 sec.
 

**LCD_Singledisplay:** 	  
Here you can change the kettle to be displayed in single mode.


## Hints

- This is running in python3
- Changing a LCD_xxxx parameter in the parameters menu or any
file in LCDDisplay folder usually requires a reboot.
- Whenever you need a reboot, have a look in the comments of the parameters.
- Future: A new fermenter should have a target temperature and at least one step defined.
- Future: Maybe it is necessary to restart craftbeerpi after adding a new fermenter. 

- If the LCD address (e.g. 0x27) is right, but you still can not see letters displayed:
  - try to adjust contrast by the screw on the back of the LCD Hardware (I2C Module)
  - be sure to provide the LCD hardware with the right amount of voltage (mostly 5V or 3.3V)
  - use a strong power-supply. If you notice LCD fading, there is a lack of current.
  - use proper connections. Soldering the wires is best for connection. Bad connection can also result in fading the LCD.


## Known Problems
The LCD hardware does not like temperature below 0°C (32°F). 
It becomes slow and can be damaged like brightness is no more homogenous throughout the hole LCD area.
Fermenters are not implemented as they are not implemented in CBPI4 until now (5-2021)


## Questions  
Questions can be posed in the Craftbeerpi user group in Facebook or in the repository.

## Fixed Issues
- has to be done

