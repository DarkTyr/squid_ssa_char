import sys
from instruments import bluebox


class TowerChannel:
    
    def __init__(self, column=0, cardaddr=3, serialport="tower", shockvalue=65535):

        self.COMMAND = '\033[95m'
        self.FCTCALL = '\033[94m'
        self.INIT = '\033[92m'
        self.WARNING = '\033[93m'
        self.FAIL = '\033[91m'
        self.ENDC = '\033[0m'
        self.BOLD = "\033[1m"

        self.green = "90EE90"
        self.red = "F08080"
        self.yellow = "FFFFCC"
        self.grey = "808080"
        self.white = "FFFFFF"

        self.verbosity = 0
        self.address = cardaddr
        self.column = column
        self.serialport = serialport
        self.shockvalue = shockvalue

        self.bluebox = bluebox.BlueBox(port=serialport,
                                       version='tower',
                                       address=self.address,
                                       channel=self.column,
                                       shared=True)

    def set_value(self, dac_value):
        if(self.verbosity > 3):
            print(("towerchannel.set_value() %g to addr %g, chn %g"%(dac_value, self.bluebox.address, self.bluebox.channel)))
        self.bluebox.setVoltDACUnits(int(dac_value))
