![cc-by-nc-sa-shield](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)

# Introduction

buggd is the Bugg recording daemon. It is a Python package. The package provides three applications - buggd, modemctl and soundcardctl. 

buggd is the daemon that is responsible for recording audio and uploading it to the user web app. Its behaviour is controlled by JSON configuration files that are provided by the web app. In addition to logging to the system journal, buggd provides status information on the Bugg's front panel LED's. buggd also provides a factory self-test function.

modemctl is a CLI tool for controlling the modem. It is intended for use during development. It allows the user to control the modem power, and get information like signal strength and SIM card status.

soundcardctl is a CLI tool for controlling the soundcard. It is intended for use during development. It allows the user to control the soundcard power, set gain and phantom modes, and run a basic recording test.

# Running
buggd is launched by a systemd service on boot.

# Configuring the device

To configure the device, use the web interface provided on the Bugg manager website to create and download a ``config.json`` file. This file should be placed on a microSD card, and inserted into the Bugg device. On boot, the Bugg device will read ``config.json`` from the microSD card and copy it to the local eMMC storage. An example ``config.json`` file can be found in the ``hardware_drivers`` directory.

The ``sensor`` part of the configuration file describes the recording parameters for the Bugg device.

The ``mobile_network`` part contains the APN details for the SIM card in the Bugg device. These can normally be found easily by searching the internet for the details specific to your provider (e.g., "Giffgaff pay monthly APN settings").

The ``device`` part contains relevant details to link the data to the correct project and configuration file on the Bugg backend (soon also being made open-source).

The remaining elements in ``config.json`` contain the authentication details for a service account created on the Google Cloud Services console (default upload route for the device is to a GCS bucket). On the GCS console you can download the key for a service account in JSON, and this should match the format of the Bugg's ``config.json`` file.

An example ``config.json`` file is provided in the ``docs`` folder.

# Project structure

The folder structure of buggd is as follows:
```
buggd
├── docs
├── src
│   └── buggd
│       ├── apps
│       │   ├── buggd
│       │   ├── modemctl
│       │   └── soundcardctl
│       ├── drivers
│       └── sensors
└── tests
```
The ``buggd/apps`` folder contains subfolders for each application, which each contain Python modules of application code. ``buggd/drivers`` contains Python modules for each hardware driver, for example the modem, soundcard and LED's. ``buggd/sensors`` contains Python modules for each "sensor" supported by the platform - currently the internal and external microphones, as well as code for parsing the configuration files.

# Recording code
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

# Factory test
buggd provides for two levels of factory test - a board-level test and a full test. The tests are triggered by the presence of "magic files" on the SD card. When a test is triggered, normal behaviour of the daemon (recording and upload) is disabled.

The board-level test is run on the bare mainboard before the product is assembled and the microphone and led boards are connected. It turns on the modem and soundcard power rails so an assembly technician can check the voltages on various test points. It flashes the mainboard user LED to indicate the test is active. The board-level test is triggered by inserting an SD card with an empty file called ``factory-test-bare.txt``. 

The full test is run on the fully assembled Bugg unit. It tests the modem, including the antenna connection by checking for cell towers, the SIM card interface, I2C connections to the internal microphone bridge, RTC and LED controller, as well as recording functionality on the internal and external microphones. At present, the recording test simply listens for white noise, though this will be improved in future. The full test is triggered by inserting an SD card with an empty file called ``factory-test-full.txt``.

## LED colour codes

When the full test is triggered, its results are displayed as follows:

| Top LED | Middle LED | Description |
|---------|------------|-------------|
| Magenta | off        | Tests running|
| Green   | off        | All tests pass |
| White   | off        | Failures in multiple categories |
| Yellow  |            | Failure in modem category |
| Yellow  | Red        | Modem USB enumeration fails |
| Yellow  | Magenta    | Modem not responding to AT commands |
| Yellow  | Blue       | SIM card not responding |
| Yellow  | Yellow     | No cell towers found - perhaps antenna not connected |
| Red     |            | Failure in I2C category
| Red     | Red        | I2S bridge not responding - perhaps mic board not connected |
| Red     | Cyan       | RTC not responding |
| Red     | Magenta    | LED controller not responding|
| Blue    |            | Failure in recording category|
| Blue    | Red        | No variance on internal channel |
| Blue    | Yellow     | No variance on external channel |
| Blue    | White      | No variance on either channel |

On a normal boot (factory test not triggered), a simplified test status is displayed for four seconds as follows:

| Top LED | Middle LED | Description |
|---------|------------|-------------|
| Magenta | Green | Factory test passed OK |
| Magenta | Red | Factory test failed or hasn't run |

## Results file

The results of the factory test are stored to ``/home/bugg/factory_test_results.txt``. This file is symlinked in ``/etc/issues.d`` so it is displayed to the console on login.

# Packaging
buggd is packaged using setuptools. The package definition is in ``pyproject.toml``. 

## Version numbering
buggd is versioned according to the [SemVer standard](https://semver.org). The version is set in ``pyproject.toml``

# To-dos

## Implement off times for the recording schedule. 

The configuration tool already allows users to pick specific hours of the day for recording, but this is not implemented yet in the firmware. Ideally the Pi would turn off or enter a low-power state during off times to conserve power.

## Offline mode

There is an offline mode in the firmware that means any attempts for connecting to the internet (updating time, uploading data) are skipped rather than just waiting for time outs. This is currently a hard flag, but should be loaded from the configuration file ideally.

[See also here](https://github.com/bugg-resources/bugg-notes/blob/main/Bugg%20TODO%20Long-Term%20Software.md)

# Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali

Work supported by Monad Gottfried Ltd. and UP Creative
