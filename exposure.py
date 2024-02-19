import u3
import sys
import time

kinesis_path = r'C:\Program Files\Thorlabs\Kinesis'
sys.path.append(kinesis_path)

import clr

clr.AddReference("System")
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.LaserDiodeCLI")

from System import Decimal
from Thorlabs.MotionControl.KCube import LaserDiodeCLI as ldcli
from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI as dmcli

LJ_OFF = 65535
LJ_ON = 0

laser_serial = '98251148'
lj_shutter_dac_channel = 0


class HoloController:
    def __init__(self, serial=None, dac=None, settle_time=0, laser_power=40):
        self.serial = serial
        self.dac = dac
        self.settle_time = settle_time
        self.laser_power = laser_power

        print("Setting up LabJack")

        self.lj = u3.U3()
        self.lj.getCalibrationData()
        self.lj.getFeedback(u3.DAC16(Dac=self.dac, Value=LJ_OFF))

        print("Setting up Kinesis Laser")

        dmcli.BuildDeviceList()
        print(list(dmcli.GetDeviceList()))

        self.device = ldcli.KCubeLaserDiode.CreateKCubeLaserDiode(self.serial)
        time.sleep(.5)
        self.device.Connect(self.serial)
        time.sleep(.5)
        self.device.SetConstP()

        print("Ready")

    def __del__(self):
        print("Cleaning up laser")
        try:
            self.device.DisconnectTidyUp()
        except:
            pass

    def set_power(self):
        self.device.SetLaserSetPoint(Decimal(float(self.laser_power)))
        print(self.device.GetLaserSetPoint().ToString())

    def set_laser_state(self, status=False):
        print(f"Setting laser state to {status}")
        if status:
            self.device.SetOn()
        else:
            self.device.SetOff()

    def set_shutter_state(self, status=False):
        print(f"Setting shutter state to {status}")
        value = LJ_ON if status else LJ_OFF
        self.lj.getFeedback(u3.DAC16(Dac=self.dac, Value=value))

    def run(self, exposure=0):
        def wait_countdown(wait_time):
            start = time.time()

            while time.time() - start < wait_time:
                left = wait_time - (time.time() - start)
                print(f"{left:.2f} left     ", end="\r", flush=True)
                time.sleep(0.01)

        print(f"Starting run with {exposure} second exposure")

        self.set_shutter_state(False)
        self.set_power()
        print(f"Enabling laser with power level {self.laser_power} mW")

        self.set_laser_state(True)

        print(f"Sleeping {self.settle_time} seconds for settle")

        wait_countdown(self.settle_time)

        print(f"Starting {exposure} second exposure")

        self.set_shutter_state(True)

        wait_countdown(exposure)

        print("Exposure complete, closing shutter and disabling laser")

        self.set_shutter_state(False)

        self.set_laser_state(False)

        print("Exposure complete")


if __name__ == '__main__':
    HoloController(serial=laser_serial, dac=lj_shutter_dac_channel, settle_time=5*60).run(10)
