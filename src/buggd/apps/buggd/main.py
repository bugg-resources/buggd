import os
import sys
import time
import shutil
import signal
import threading
import datetime as dt
import json
import logging
import argparse
import atexit
from importlib import metadata
from google.cloud import storage
from pcf8574 import PCF8574

from buggd import sensors
from buggd.drivers.modem import Modem
from buggd.drivers.userled import UserLED
from buggd.drivers.leds import LEDs, Colour

from .utils import call_cmd_line, mount_ext_sd, copy_sd_card_config, discover_serial, clean_dirs, check_sd_not_corrupt, merge_dirs
from .utils import check_internet_conn, update_time, set_led,  wait_for_internet_conn, check_reboot_due
from .factorytest import FactoryTest
from .log import setup_logging

# Allow disabling of reboot feature for testing
# TODO: make this a configurable parameter from the config.json file
REBOOT_ALLOWED = True

# set a global name for a common logging for functions using this module
LOG = 'bugg-recording'
LOG_DIR = '/home/buggd/logs/'

# How many times to try for an internet connection before starting recording
BOOT_INTERNET_RETRIES = 30

# What time to reboot the device at daily
REBOOT_TIME_UTC = dt.time(2, 0, 0)

# How long to wait after an error for a reboot
ERROR_WAIT_REBOOT_S = 300

# GPIO information for the LED driver and LED colours
PCF8574_I2C_ADD = 0x23
PCF8574_I2C_BUS = 1
REC_LED_CHS = (7, 6, 5)
DATA_LED_CHS = (4, 3, 2)
PWR_LED_CHS = (1, 0)
DATA_LED_UPDATE_INT = 10
REC_LED_REC = (0, 1, 0)
REC_LED_SLEEP = (0, 0, 0)
DATA_LED_SETUP = (0, 1, 0)
DATA_LED_UPLOADING = (0, 1, 1)
DATA_LED_CONN = (0, 0, 1)
DATA_LED_NO_CONN = (1, 0, 0)
DATA_LED_NO_CONN_OFFL = (0, 0, 0)
LED_ALL_ON = (1, 1, 1)
LED_ALL_OFF = (0, 0, 0)
PWR_LED_ON = (0, 0)

CONFIG_FNAME = 'config.json'

SD_MNT_LOC = '/mnt/sd/'
FACTORY_TEST_TRIGGER_FULL = '/mnt/sd/factory-test-full.txt'
FACTORY_TEST_TRIGGER_BARE_BOARD = '/mnt/sd/factory-test-bare.txt'

GLOB_no_sd_mode = False
GLOB_is_connected = False
#TODO: make offline mode a configurable parameter from the config.json file
GLOB_offline_mode = False

leds = LEDs() # Make the LEDs object global so it can be accessed by the cleanup function

# Create a logger for this module and set its level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

"""
Running the recording process uses the following functions, which users
might want to repackage in bespoke code, or which it is useful to isolate
for testing:

Sensor setup and recording
* auto_sys_config() # returns automatically detected system configuration options
* auto_configure_sensor() # sets up the sensor using the config file
* record_sensor(sensor, wdir, udir, sleep=True) # initiates a single round of sampling

GCS server sync
* gcs_server_sync(sync_int, udir, die) # rolling synchronisation, intended to run in thread


"""

def auto_sys_config(sd_mnt_dir, use_sd_card):
    """
    Automatically determine sys config options:
    Returns:
        working_dir: working directory to store temporary files in
        upload_dir: the top level of the directory to sync with GCS
        data_dir: the subdirectory where the compressed data is written to
    """

    working_dir_name = 'rpi-ecosystem-monitoring_tmp'
    upload_dir_name = 'audio'

    working_dir = os.path.join('/tmp',working_dir_name)

    upload_dir_local = upload_dir_name

    if use_sd_card:
        upload_dir = os.path.join(sd_mnt_dir, upload_dir_name)

        # Merge upload_dir_local with the SD based upload directory
        if os.path.exists(upload_dir_local) and os.path.isdir(upload_dir_local):
            merge_dirs(upload_dir_local, upload_dir, delete_src=True)
    else:
        upload_dir = upload_dir_local


    # Set up the data directory under upload_dir with the correct config/project/device IDs
    proj_id = 'na'
    conf_id = 'na'
    cpu_id = discover_serial()
    # If there's a config file get the project and config IDs
    if os.path.exists(CONFIG_FNAME):
        dev_config = json.load(open(CONFIG_FNAME))['device']
        proj_id = dev_config['project_id']
        conf_id = dev_config['config_id']

    # Make the various levels to get to the data_directory level
    proj_dir = os.path.join(upload_dir, 'proj_{}'.format(proj_id))
    device_dir = os.path.join(proj_dir, 'bugg_{}'.format(cpu_id))
    data_dir = os.path.join(device_dir, 'conf_{}'.format(conf_id))

    return working_dir, upload_dir, data_dir

def auto_configure_sensor():

    """
    Automatically configure the sensor based on the config file parameters
    Returns:
        An instance of a sensor class
    """

    # Get sensor configuration from config file if exists
    if os.path.exists(CONFIG_FNAME):
        config = json.load(open(CONFIG_FNAME))
        sensor_config = config['sensor']
        sensor_type = sensor_config['sensor_type']
        logger.info('Found local config file - configuring {} with settings from file'.format(sensor_type))

    else:
        # Otherwise fallback to I2SMic default settings
        logger.info('No local config file - falling back to I2SMic with default configuration')
        sensor_type = 'I2SMic'
        sensor_config = None

    try:
        sensor_class = getattr(sensors, sensor_type)
        logger.info('Sensor type {} being configured.'.format(sensor_type))
    except AttributeError as ate:
        logger.critical('Sensor type {} not found.'.format(sensor_type))
        raise ate

    # get a configured instance of the sensor - all options set to default values
    # TODO - not sure of exception classes here?
    try:
        sensor = sensor_class(sensor_config)
        logger.info('Sensor config succeeded.'.format(sensor_type))
    except ValueError as e:
        logger.critical('Sensor config failed.'.format(sensor_type))
        raise e

    # If it passes config, does it pass setup.
    if sensor.setup():
        logger.info('Sensor setup succeeded')
    else:
        logger.critical('Sensor setup failed')
        raise Exception('Sensor setup failed')

    return sensor


def record_sensor(sensor, working_dir, data_dir, led_driver):

    """
    Function to run the common sensor record loop. The sleep between
    sensor recordings can be turned off
    Args:
        sensor: A sensor instance
        working_dir: The working directory to be used by the sensor
        data_dir: The data directory to use for completed files
        led_driver: The I2C driver for the LEDs
    """

    # Capture data from the sensor
    logger.info('Capturing data from sensor')
    set_led(led_driver, REC_LED_CHS, REC_LED_REC)

    uncomp_f = sensor.capture_data(working_dir=working_dir, data_dir=data_dir)

    # Check whether the daily reboot is required
    cmd_on_complete = None
    if check_reboot_due(REBOOT_TIME_UTC):
        cmd_on_complete = 'sudo reboot'

    # Postprocess the raw data in a separate thread
    postprocess_t = threading.Thread(target=sensor.postprocess, args=(uncomp_f,cmd_on_complete,))
    postprocess_t.start()

    # Let the sensor sleep
    set_led(led_driver, REC_LED_CHS, REC_LED_SLEEP)
    sensor.sleep()

def exit_handler(signal, frame):

    """
    Function to allow the thread loops to be shut down
    :param signal:
    :param frame:
    :return:
    """

    logger.info('SIGINT detected, shutting down')
    # set the event to signal threads
    raise StopMonitoring

class StopMonitoring(Exception):

    """
    This is a custom exception that gets thrown by the exit handler
    when SIGINT is detected. It allows a loop within a try/except block
    to break out and set the event to shutdown cleanly
    """

    pass


def gcs_server_sync(sync_interval, upload_dir, die, config_path, led_driver, modem, data_led_update_int):

    """
    Function to synchronize the upload data folder with the GCS bucket

    Parameters:
        sync_interval: The time interval between synchronisation connections
        upload_dir: The upload directory to synchronise (top level, not the device specific subdirectory)
        die: A threading event to terminate the GCS server sync
        led_driver: The I2C driver for controlling the LEDs
        data_led_update_int: How often to update the status of the data LED in minutes
    """

    global GLOB_is_connected

    # Sleep the thread and keep updating the data LED until the first upload cycle
    start_t = time.time()
    start_offs = sync_interval/2
    logger.info('Sleeping data upload thread for {} secs before first upload'.format(start_offs))

    # Check for internet conn to update LED
    GLOB_is_connected = check_internet_conn(led_driver, DATA_LED_CHS, col_succ=DATA_LED_CONN, col_fail=DATA_LED_NO_CONN)
    # Turn off modem to save power
    modem.power_off()

    # Wait till half way through first recording to first upload try
    wait_t = start_offs - (time.time() - start_t)
    time.sleep(max(0, wait_t))

    # keep running while the die is not set
    while not die.is_set():
        # Update sync start time
        start_t = time.time()

        # Enable the modem and wait for an internet connection
        modem.power_on()
        GLOB_is_connected = wait_for_internet_conn(BOOT_INTERNET_RETRIES, led_driver, DATA_LED_CHS, col_succ=DATA_LED_CONN, col_fail=DATA_LED_NO_CONN)

        # Set data LED to active uploading state (only if the device is connected as otherwise it's confusing - is the device uploading or not?)
        if GLOB_is_connected:
            # Update time from internet
            update_time()

            logger.info('Started GCS sync at {} to upload_dir {}'.format(dt.datetime.utcnow(), upload_dir))

            # Set the LED to uploading colour
            set_led(led_driver, DATA_LED_CHS, DATA_LED_UPLOADING)

            try:
                # Get credentials from JSON file
                client = storage.Client.from_service_account_json(config_path)

                # Find the right GCS bucket
                bugg_device_conf = json.load(open(config_path))['device']
                gcs_bucket_name = bugg_device_conf['gcs_bucket_name']
                bucket = client.bucket(gcs_bucket_name)

                # Loop through local files, uploading them to the server
                for root, subdirs, files in os.walk(upload_dir):
                    for local_f in files:
                        local_path = os.path.join(root, local_f)
                        remote_path = local_path[len(upload_dir)+1:]
                        logger.info('Uploading {} to {}'.format(local_path, remote_path))
                        upload_f = bucket.blob(remote_path)
                        upload_f.upload_from_filename(filename=local_path)

                        # If the file did not upload successfully an Exception will be thrown
                        # by upload_from_filename, so if we're here it's safe to delete the local file
                        logger.info('Upload complete. Deleting local file at {}'.format(local_path))
                        os.remove(local_path)

            except Exception as e:
                logger.info('Exception caught in gcs_server_sync: {}'.format(str(e)))

            # Done uploading so set LED back to connected mode
            set_led(led_driver, DATA_LED_CHS, DATA_LED_CONN)

        else:
            logger.info('No internet connection available, so not trying GCS sync')

        # Disable the modem to save power
        logger.info('Disabling modem until next server sync (to save power)')
        modem.power_off()

        # Sleep the thread until the next upload cycle
        sync_wait = sync_interval - (time.time() - start_t)
        logger.info('Waiting {} secs to next sync'.format(sync_wait))
        time.sleep(max(0, sync_wait))


def continuous_recording(sensor, working_dir, data_dir, led_driver, die):

    """
    Runs a loop over the sensor sampling process

    Args:
        sensor: A instance of one of the sensor classes
        working_dir: Path to the working directory for recording
        data_dir: Path to the final directory used to store processed data files
        led_driver: The I2C driver for controlling the LEDs
        die: A threading event to terminate the server sync
    """

    try:
        # Start recording
        while not die.is_set():
            logger.info('GLOB_no_sd_mode: {}, GLOB_is_connected: {}, GLOB_offline_mode: {}'.format(GLOB_no_sd_mode, GLOB_is_connected, GLOB_offline_mode))
            record_sensor(sensor, working_dir, data_dir, led_driver)
    except Exception as e:
        logging.error('Caught exception on continuous_recording() function: {}'.format(str(e)))

        # Blink error code on LEDs
        blink_error_leds(led_driver, e, dur=ERROR_WAIT_REBOOT_S)


def blink_error_leds(led_driver, error_e, dur=None):

    #TODO: implement different flashing patterns for different error codes
    """
    Communicate that a major error has occurred through LEDs flashing. This is
    blocking and will stop all future code from running until rebooted

    Args:
        led_driver: The I2C driver for controlling the LEDs
        error_e: the exception that caused the error
        dur: duration in seconds to blink for
    """

    # Blink all status LEDs to indicate a major error has occurred
    running_t = 0
    state = 1

    # Return from function after finite duration if dur provided
    if dur is not None:
        while running_t < dur:
            if state: led_cols = LED_ALL_ON
            else: led_cols = LED_ALL_OFF
            state = not state

            set_led(led_driver, REC_LED_CHS, led_cols)
            set_led(led_driver, DATA_LED_CHS, led_cols)

            time.sleep(1)
            running_t += 1
    else:
        # Otherwise sleep forever
        while True: time.sleep(60)

    # Reboot unit
    if REBOOT_ALLOWED:
        logger.info('Rebooting device to try recover from error')
        call_cmd_line('sudo reboot')


def record(led_driver, modem):

    """
    Function to setup, run and log continuous sampling from the sensor.

    Args:
        logfile_name: The filename that the logs from this run should be stored to
        log_dir: A directory to be used for logging. Existing log files
        found in will be moved to upload.
    """

    global GLOB_no_sd_mode
    global GLOB_is_connected
    global GLOB_offline_mode
    global LOG_DIR

    # Get the unique CPU ID of the device
    cpu_serial = discover_serial()

    # Start logging immediately. The log_dir can't be included in config
    # because we're not loading config until after logging has started.
    start_time = time.strftime('%Y%m%d_%H%M')

    # Create the logs directory and file if needed
    log_dir = LOG_DIR
    logfile_name = 'rpi_eco_{}_{}.log'.format(cpu_serial,start_time)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir,logfile_name)
    if not os.path.exists(logfile):
        open(logfile, 'w+')

    # Add handlers to logging so logs are sent to stdout and the file
    logging.getLogger().setLevel(logging.INFO)
    fmter = logging.Formatter('{} - %(message)s'.format(cpu_serial))
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmter)
    logging.getLogger().addHandler(ch)
    hdlr = logging.FileHandler(filename=logfile)
    logging.getLogger().addHandler(hdlr)

    logger.info("Saving logs to %s", logfile)

    logger.info('Start of buggd version %s at %s', metadata.version('buggd'), format(start_time))

    if not GLOB_offline_mode:
        # Enable the modem for a mobile network connection. If no modem set recorder to offline mode
        GLOB_offline_mode = not modem.power_on()

    # Try to mount the external SD card
    try:
        mount_ext_sd(SD_MNT_LOC)
        check_sd_not_corrupt(SD_MNT_LOC)
    except Exception as e:
        GLOB_no_sd_mode = True
        logger.info('Couldn\'t mount external SD card: {}'.format(str(e)))

    # Try to load the config files from the SD card
    try:
        copy_sd_card_config(SD_MNT_LOC, CONFIG_FNAME)
    except Exception as e:
        # Check if there's a local config file we can fall back to
        if os.path.exists(CONFIG_FNAME):
            logger.info('Couldn\'t copy SD card config, but a config file already exists so continuing ({})'.format(str(e)))
        else:
            logger.info('Couldn\'t copy SD card config, and no config already exists... ({})'.format(str(e)))

            if GLOB_no_sd_mode:
                # If there's no SD card too then there's no point in continuing
                logger.info('GLOB_no_sd_mode also activated - can\'t fallback as offline recorder so bailing')
                raise e
            else:
                # If there is an SD card we can just run as an offline recorder saving to the SD
                GLOB_offline_mode = True

    if GLOB_offline_mode:
        # Set LEDs to offline mode
        set_led(led_driver, DATA_LED_CHS, DATA_LED_NO_CONN_OFFL)
        logger.info('Recorder is in offline mode saving to SD card')
    else:
        # Waiting for internet connection
        GLOB_is_connected = wait_for_internet_conn(BOOT_INTERNET_RETRIES, led_driver, DATA_LED_CHS, col_succ=DATA_LED_CONN, col_fail=DATA_LED_NO_CONN)

        if GLOB_is_connected:
            # Update time from internet
            update_time()

    # Determine the system configuration options automatically
    working_dir, upload_dir, data_dir = auto_sys_config(SD_MNT_LOC, not GLOB_no_sd_mode)

    # Clean data directories
    clean_dirs(working_dir,upload_dir,data_dir)

    # move any existing logs into the upload folder for this pi
    try:
        upload_dir_logs = os.path.join(upload_dir, 'logs')
        if not os.path.exists(upload_dir_logs):
            os.makedirs(upload_dir_logs)

        existing_logs = [f for f in os.listdir(log_dir) if f.endswith('.log') and f != logfile_name]
        for log in existing_logs:
            shutil.move(os.path.join(log_dir, log),
                      os.path.join(upload_dir_logs, log))
            logger.info('Moved {} to upload'.format(log))
    except OSError:
        # not critical - can leave logs in the log_dir
        logging.error('Could not move existing logs to upload.')

    # Now get the sensor
    sensor = auto_configure_sensor()

    # Set up the threads to run and an event handler to allow them to be shutdown cleanly
    die = threading.Event()
    signal.signal(signal.SIGINT, exit_handler)

    if not GLOB_offline_mode:
        sync_thread = threading.Thread(target=gcs_server_sync, args=(sensor.server_sync_interval,
                                                                     upload_dir, die, CONFIG_FNAME,
                                                                     led_driver, modem, DATA_LED_UPDATE_INT))

    record_thread = threading.Thread(target=continuous_recording, args=(sensor, working_dir,
                                                                    data_dir, led_driver, die))

    # Initialise background thread to do remote sync of the root upload directory
    # Failure here does not preclude data capture and might be temporary so log
    # errors but don't exit.
    try:
        # start the recorder
        logger.info('Starting continuous recording at {}'.format(dt.datetime.utcnow()))
        record_thread.start()

        if GLOB_offline_mode:
            logger.info('Running in offline mode - no GCS synchronisation')
        else:
            # start the GCS sync thread
            sync_thread.start()
            logger.info('Starting GCS server sync every {} seconds at {}'.format(sensor.server_sync_interval, dt.datetime.utcnow()))

        # now run a loop that will continue with a small grain until
        # an interrupt arrives, this is necessary to keep the program live
        # and listening for interrupts
        while True:
            time.sleep(1)
    except StopMonitoring:
        # We've had an interrupt signal, so tell the threads to shutdown,
        # wait for them to finish and then exit the program
        die.set()
        record_thread.join()
        if not GLOB_offline_mode:
            sync_thread.join()

        logger.info('Recording and sync shutdown, exiting at {}'.format(dt.datetime.utcnow()))


def main():
    """
    Main function to run the recording daemon
    
    If the trigger file exists for the full or bare-board factory test, run the factory test and exit.

    Otherwise, run the continuous recording function.
    
    Args:
        --force-factory-test: Run factory test, even if trigger file is not present.
        --force-factory-test-bare: Run factory test in bare-board mode, even if trigger file is not present.
    """
    global leds
    atexit.register(cleanup)

    print("main logger.name", logger.name)
    parser = argparse.ArgumentParser(description='Bugg Recording Daemon')
    parser.add_argument('--force-factory-test', action='store_true',
                        help='Run factory test, even if trigger file is not present.')
    parser.add_argument('--force-factory-test-bare', action='store_true',
                        help='Run factory test in bare-board mode, even if trigger file is not present.')
    parser.add_argument('--version', action='version', version=metadata.version('buggd'))
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)
    logger.info('Starting buggd')

    test = FactoryTest(leds)

    # If the trigger file exists, run the factory test
    if args.force_factory_test or os.path.exists(FACTORY_TEST_TRIGGER_FULL):
        leds.top.stay_on_at_exit = True
        leds.middle.stay_on_at_exit = True
        sys.exit(test.run())

    # If the bare-board trigger file exists, run the factory test. Full test
    # takes precedence.
    if args.force_factory_test_bare or os.path.exists(FACTORY_TEST_TRIGGER_BARE_BOARD):
        test.run_bare_board()
        sys.exit(0)

    # On boot, set the LEDs to show the status of the factory test
    leds.top.set(Colour.MAGENTA)
    leds.bottom.set(Colour.RED)
    if test.passed_at_factory():
        leds.middle.set(Colour.GREEN)
    else:
        leds.middle.set(Colour.RED)
    time.sleep(4)
    # Turn off test status leds before beginning recording, just so it's a bit clearer what's happening
    leds.all_off()
    
    # TODO: replace this old way of handling the LED's with the new LED driver
    # Initialise LED driver and turn all channels off
    led_driver = PCF8574(PCF8574_I2C_BUS, PCF8574_I2C_ADD)
    modem = Modem()

    # Initialise the LED on the main board
    led = UserLED()
    try:
        # run continuous recording function
        led.on()
        record(led_driver, modem)
    except Exception as e:
        logging.error('Caught exception on main record() function: {}'.format(str(e)))
        led.off()

        # Blink error code on LEDs
        blink_error_leds(led_driver, e, dur=ERROR_WAIT_REBOOT_S)


def cleanup():
    """
    Cleanup function to turn off the LEDs on exit
    """
    global leds
    exc_type, _, _ = sys.exc_info()

    logger.info('At-exit handler called')
    print("At-exit handler called")

    led = UserLED()
    led.off()

    if exc_type is not None:
        logging.warning("Exiting due to exception: %s", exc_type.__name__)
        colour = Colour.YELLOW
    else:
        logger.info("Exiting normally without exception.")
        colour = Colour.RED

    leds.bottom.set(colour)
    leds.at_exit()

if __name__ == "__main__":
    setup_logging()

    # Get the unique CPU ID of the device
    cpu_serial = discover_serial()
    # Get the current time - this is the time buggd was started
    start_time = time.strftime('%Y%m%d_%H%M')

    logger.info('Start of buggd version %s at %s', metadata.version('buggd'), format(start_time))
    logger.info("Saving logs to bee%s", logfile)

    main()