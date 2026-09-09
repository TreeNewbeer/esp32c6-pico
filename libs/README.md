# Local KiCad libraries

`Pico_Design.kicad_sym` contains the project's embedded symbols. MCU, flash, USB TVS and logic-buffer graphics group pins to make the peripheral wiring readable; pin numbers and electrical types are retained.

`Memory_Flash__W25Q32JVSN` uses the eight-pin W25Q32JVSNIQ SOIC-8 (150 mil) pinout. The former WSON exposed-pad pin 9 is removed; the other pin locations retain the existing visible peripheral wiring.

`power-GND.kicad_sym` and `power-+3V3.kicad_sym` are unmodified standard power symbols copied on 2026-09-08 from the official [KiCad symbol repository](https://gitlab.com/kicad/libraries/kicad-symbols/-/tree/master/power.kicad_symdir). They are inputs to `tools/redraw_schematic.py` and are embedded under local names in the delivered schematic. KiCad library content uses [CC BY-SA 4.0 with the KiCad library exception](https://www.kicad.org/libraries/license/).
