![cc-by-nc-sa-shield](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

# CAUTION: This document needs re-writing to reflect the bifurcation of bugg-cm4-firmware into bugg-recording and the new bugg-os project. 

This document needs heavy editing - some of what follows below has been deprecated or is misleading as things currently stand, but as of March 2024 I haven't edited any of it yet, as there are some important details relevant for completing the firmware development. 

# bugg-cm4-firmware

[Bugg](https://www.bugg.xyz/) is a research project developing technologies for fully autonomous eco-acoustic monitoring. 

Bugg recording devices are based on the Raspberry Pi Compute Module 4 (CM4) and record, (optionally) compress, and robustly upload audio data from the field to a server. This repository contains all the custom firmware running on the CM4, and assumes the module is inserted into the custom Bugg PCBs.

For a full overview of the electronic and mechanical design of the Bugg recording device and detailed assembly instructions please refer to the [Bugg hardware handover document](https://raw.githubusercontent.com/bugg-resources/bugg-handover/master/bugg-handover.pdf?token=GHSAT0AAAAAABSRG7B7T6BEZWMJQBPE7FNYYSNI6KQ).

This project was built on an earlier prototype described in an [academic paper](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.13089) which should be cited when using this work. 

## Code design

The firmware is triggered to run on boot from the command ``python python_record.py`` in the ``/etc/profile`` script. The firmware (this repo) is located in the directory ``~/bugg-cm4-firmware``.

The sequence of events from the ``record`` function (in ``python_record.py``) is as follows:

1. Set up error logging.
2. Log the ID of the Pi device running the code and the current git version of the recorder script.
3. Enable the Sierra Wireless modem: ``enable_modem``
4. Mount the external SD card: ``mount_ext_sd``. If unsuccessful, save data to the eMMC storage onboard the Raspberry Pi Compute Module.
5. Copy the configuration file from the SD card: ``copy_sd_card_config``
6. Wait for a valid internet connection (if not running in offline mode): ``wait_for_internet_conn``
7. Instantiate a sensor class object with the configured recording parameters: ``auto_configure_sensor``
8. Create and launch a thread that executes the GCS data uploading: ``gcs_server_sync``
9. Create and launch a thread that records and compresses data from the microphone: ``continuous_recording``. The ``record_sensor`` function itself executes the sensor methods: a) ``sensor.capture_data()`` to record whatever it is the sensor records; b) ``sensor.postprocess()`` is run in a separate thread to avoid locking up the ``sensor_record`` loop; and then c) ``sensor.sleep()`` to pause until the next sample is due.
10. The recording and uploading threads repeat periodically until the device is powered down, or a reboot is performed (by default, at 2am UTC each day)


## Configuring the device

To configure the device, use the web interface provided on the Bugg manager website to create and download a ``config.json`` file. This file should be placed on a microSD card, and inserted into the Bugg device. On boot, the Bugg device will read ``config.json`` from the microSD card and copy it to the local eMMC storage. An example ``config.json`` file can be found in the ``hardware_drivers`` directory.

The ``sensor`` part of the configuration file describes the recording parameters for the Bugg device.

The ``mobile_network`` part contains the APN details for the SIM card in the Bugg device. These can normally be found easily by searching the internet for the details specific to your provider (e.g., "Giffgaff pay monthly APN settings").

The ``device`` part contains relevant details to link the data to the correct project and configuration file on the Bugg backend (soon also being made open-source).

The remaining elements in ``config.json`` contain the authentication details for a service account created on the Google Cloud Services console (default upload route for the device is to a GCS bucket). On the GCS console you can download the key for a service account in JSON, and this should match the format of the Bugg's ``config.json`` file.

## Setup

### Setup from pre-built OS image
The easiest way to deploy this firmware is to use a pre-built OS image and flash it to the Raspberry Pi Compute Module 4. No further set up is required if this route is taken. Pre-built images which are ready for flashing are hosted as releases on this repository.

On the Bugg main PCB, to the top right of the CM4 there is a micro-USB connector that should be used for flashing. Power is not supplied through this connector so the main Bugg power cable must also be plugged in. Note, to ensure the CM4 boots in the correct mode, you should first connect the micro-USB cable to your computer, then the power cable.  

If the CM4 eMMC does not mount as an external storage device, you may need to install and run the rpiboot tool - see the official Compute Module [documentation](https://www.raspberrypi.com/documentation/computers/compute-module.html#flashing-the-compute-module-emmc). The image can be flashed to the device using the [Raspberry Pi Imager](https://www.raspberrypi.com/documentation/computers/getting-started.html#using-raspberry-pi-imager).

### Setup from a stock Raspberry Pi OS image
If you would rather start using a stock Raspberry Pi OS image, there's an extra couple of steps before you start the above process. The below steps assume you have downloaded and installed the [Raspberry Pi OS Lite image](https://www.raspberrypi.org/software/operating-systems/).

To begin, the Pi OS Lite image does not have the required packages to connect to the internet using the Sierra Wireless modem onboard the Bugg main PCB. Therefore, the Raspberry Pi Compute Module must first be inserted into a separate carrier board (e.g., the [official Compute Module 4 IO board](https://www.raspberrypi.org/products/compute-module-4-io-board/)) which has a USB port. A USB Wifi dongle can then be used to establish the internet connection needed to set-up the Bugg device firmware from scratch.

* Flash the Raspberry Pi OS Lite image to the Raspberry Pi Compute Module 4 (CM4)
* Modify ``/boot/config.txt``
	* Enable USB ports by adding ``dtoverlay=dwc2,dr_mode=host``
	* Disable Bluetooth by adding ``dtoverlay=disable-bt``
* Establish shell access to the CM4 using a keyboard and monitor, or via [a serial connection](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-5-using-a-console-cable/enabling-serial-console)
* General setup: ``sudo raspi-config``
	* Enable autologin to CLI
	* Enable the I2C interface
	* Enable the serial port
	* Enable remote GPIO access
	* Ensure timezone is set to UTC
* Enable hardware watchdog (triggers automatic reboot if OS kernel panics)
	* Add ``dtparam=watchdog=on`` to ``/boot/config.txt``
	* ``sudo reboot``
	* ``sudo apt-get install -y watchdog``
	* Add the following to ``/etc/watchdog.conf``
		* ``watchdog-device = /dev/watchdog``
		* ``watchdog-timeout = 15``
		* ``max-load-1 = 24``
	* Enable the system service
		* ``sudo systemctl enable watchdog``
		* ``sudo systemctl start watchdog``
		* ``sudo systemctl status watchdog``
* Set up Network/Modem Manager for Sierra Wireless modem
	* Edit ``/boot/config.txt``
		* Comment out ``#dtoverlay=dwc2,dr_mode=host``
		* Add ``otg_mode=1``
	* ``sudo apt-get install modemmanager network-manager``
	* Edit ``/etc/dhcpcd.conf``
		* Add ``denyinterfaces wwan0``
	* Test the connection (substitute real APN details for SIM card):
		* ``sudo nmcli connection add type gsm ifname '*' con-name 'voxi' apn 'pp.vodafone.co.uk' connection.autoconnect yes gsm.username wap gsm.password wap``
		* ``nmcli device status``
* Set up Google Cloud Services
	* ``sudo apt-get install -y python3-pip``
	* ``sudo pip3 install --upgrade six google-cloud-storage``
* Install extra packages
	* ``sudo apt-get -y install git ffmpeg  ntpdate``
	* ``sudo pip3 install RPi.GPIO``
* Set up monitoring firmware
	* ``git clone https://github.com/bugg-eco-monitoring/bugg-cm4-firmware``
	* Add startup commands to ``/etc/profile``:
		* ``cd /home/pi/bugg-cm4-firmware``
		* ``sudo -E python3 -u python_record.py  &`` or to log from the device over serial ``(sudo -E python3 -u python_record.py 2>&1 | tee /dev/serial0) &``
* DEPRECATED Enable I2S interface for microphone
	* ``sudo pip3 install --upgrade adafruit-python-shell``
	* ``cd ~/bugg-cm4-firmware/hardware_drivers``
	* ``sudo python3 i2smic_with_cm4.py``
* Set up DS2331 real-time clock
	* Add ``dtoverlay=i2c-rtc,ds3231,wakeup-source`` to ``/boot/config.txt``
	* ``cat /proc/driver/rtc``
	* Disable the fake Pi hardware clock
		* ``sudo apt-get -y remove fake-hwclock``
		* ``sudo update-rc.d -f fake-hwclock remove``
		* ``sudo systemctl disable fake-hwclock``
	* Edit ``/lib/udev/hwclock-set``
		* Comment out ``#if [ -e /run/systemd/system ] ; then``
		* Comment out ``#exit 0``
		* Comment out ``#fi``
		* Comment out ``#/sbin/hwclock --rtc=$dev --systz --badyear``
		* Comment out ``#/sbin/hwclock --rtc=$dev --systz``
	* Test by checking status: ``timedatectl``
* Set up PCF8574 I2C LED chip
	* ``sudo apt-get install libffi-dev``
	* ``pip3 install pcf8574``

## Implementing new sensors

To implement a new sensor type simply create a class in the ``sensors`` directory that extends the SensorBase class. The SensorBase class contains default implementations of the required class methods, which can be overridden in derived sensor classes. The required methods are:

* ``__init__`` - This method is loads the sensor options from the JSON configuration file, falling back to the default options (see the ``options`` static method below) where an option isn't included in the config. The ``__init.py__`` file in the ``sensors`` module provides the shared function ``set_options`` to help with this.
* ``options`` - This static method defines the config options and defaults for the sensor class
* ``setup`` - This method should be used to check that the system resources required to run the sensor are available: required Debian packages, correctly installed devices.
* ``capture_data`` - This method is used to capture data from the sensor input. The data will normally be stored to a working directory, set in the config file, in case further processing is needed before data is uploaded. If no further processing is needed, the data could be written directly to the upload directory.
* ``postprocess`` - This method performs any postprocessing that needs to be done to the raw data (e.g. compressing it) before upload. If no post processing is needed, you don't need to provide the method, as the default SensorBase implementation contains a simple stub to handle calls to ``Sensor.postprocess()``.
* ``sleep`` - This method is a simple wrapper to pause between data captures - the pause length is implemented as a variable in the JSON config, so you're unlikely to need to override the base method.

Note that threads are used to run the ``capture_data`` and ``postprocess`` methods so that they operate independently.

Finally add ``from sensors.YourNewSensor import YourNewSensor`` to ``sensors/__init__.py``

## To-dos

### Implement off times for the recording schedule. 

The configuration tool already allows users to pick specific hours of the day for recording, but this is not implemented yet in the firmware. Ideally the Pi would turn off or enter a low-power state during off times to conserve power.

### Offline mode

There is an offline mode in the firmware that means any attempts for connecting to the internet (updating time, uploading data) are skipped rather than just waiting for time outs. This is currently a hard flag, but should be loaded from the configuration file ideally.

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali

Work supported by Monad Gotfried Ltd. and UP Creative
