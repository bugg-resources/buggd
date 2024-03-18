import subprocess
import os
import logging
import shutil
import filecmp
import json
import RPi.GPIO as GPIO
from datetime import datetime
import time
try:
    import httplib
except:
    import http.client as httplib


def set_led(led_driver, channels_arr, col_arr):
    """
    Sets LED colours using the PCF8574 I2C LED driver

    Args:
        led_driver: The I2C driver for the PCF8574 chip
        channels_arr: Array of channels on the PCA9865 that refer to colours in col_arr (tuple)
        col_arr: The target values for the LED channels (tuple)
    """

    for ch, col in zip(channels_arr, col_arr):
        led_driver.port[ch] = not col


def set_led_PCA9685(led_driver, channels_arr, col_arr):
    """
    Sets LED colours using the PCA9685 I2C LED driver

    Args:
        led_driver: The I2C driver for controlling the LEDs
        channels_arr: Array of channels on the PCA9865 that refer to colours in col_arr (tuple)
        col_arr: The target values for the LED channels (tuple)
    """

    LED_MAX = 4096

    for ch, col in zip(channels_arr, col_arr):
        led_driver.set_pwm(ch, LED_MAX - col, col)

def call_cmd_line(args, use_shell=True, print_output=False, run_in_bg=False):

    """
    Use command line calls - wrapper around subprocess.Popen
    """

    p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=use_shell, encoding='utf8')
    if run_in_bg: return

    res = ''
    while True:
        output = p.stdout.readline()
        if output == '' and p.poll() is not None:
            break
        if output:
            res = res + output.strip()
            if print_output: logging.info(output.strip())

    rc = p.poll()

    return res


def update_time():
    """
    Update the time from the internet, and write the updated time to the real-time clock module
    """

    # (Not needed if RTC properly set-up)
    # Read time from real-time clock module
    # logging.info('Reading time from RTC')
    # call_cmd_line('sudo hwclock -r')

    # Update time from internet
    logging.info('Updating time from internet before GCS sync')
    cmd_res = call_cmd_line('sudo timeout 180s ntpdate ntp.ubuntu.com')

    # Check if ntpdate was successful
    if 'adjust time server' in cmd_res:
        # Update time on real-time clock module
        logging.info('Writing updated time to RTC')
        call_cmd_line('sudo hwclock -w')



def check_internet_conn(led_driver=[], led_driver_chs=[], col_succ=[], col_fail=[], timeout=2):
    """
    Check if there is a valid internet conntection
    """

    # Try grabbing the header of google.com and catch the exception if not possible
    conn = httplib.HTTPConnection('google.com', timeout=timeout)
    success = False
    try:
        conn.request('HEAD', '/')
        conn.close()
        if led_driver:
            set_led(led_driver, led_driver_chs, col_succ)
        return True
    except Exception as e:
        if led_driver:
            set_led(led_driver, led_driver_chs, col_fail)
        return False


def wait_for_internet_conn(n_tries, led_driver, led_driver_chs, col_succ, col_fail, timeout=2, verbose=False):
    """
    Repeatedly check and wait for a valid internet conntection
    """

    is_conn = False

    logging.info('Waiting for internet connection...')

    for n_try in range(n_tries):
        # Try to connect to the internet
        is_conn = check_internet_conn(timeout=timeout)

        # If connected break out
        if is_conn:
            break

        # Otherwise sleep for a second and try again
        else:
            if verbose:
                logging.info('No internet connection on try {}/{}'.format(n_try+1, n_tries))
            time.sleep(1)

    if is_conn:
        logging.info('Connected to the Internet')
        set_led(led_driver, led_driver_chs, col_succ)
    else:
        logging.info('No connection to internet after {} tries'.format(n_tries))
        set_led(led_driver, led_driver_chs, col_fail)

    return is_conn


def copy_sd_card_config(sd_mount_loc, config_fname):

    """
    Checks the boot sector on the SD card for any recorder config files -
    if there are any, copy them to the relevant directories
    """

    sd_config_path = os.path.join(sd_mount_loc, config_fname)
    local_config_path = config_fname

    try:
        # Try to load the config file on the SD card as JSON to validate it works
        config = json.load(open(sd_config_path))
    except Exception as e:
        logging.info('Couldn\'t parse {} as valid JSON'.format(sd_config_path))
        raise e

    # Check it's not just the same as the one we're already using
    if os.path.exists(local_config_path) and filecmp.cmp(sd_config_path, local_config_path):
        logging.info('SD card config file ({}) matches existing config ({})'.format(sd_config_path, local_config_path))
        return

    # Copy the SD config file and reboot
    # TODO: Indicate with LEDs / buzzer a new config has been found
    logging.info('Copied config from SD to local')
    shutil.copyfile(sd_config_path, local_config_path)

    # Try to configure modem, but it's not required so escape any errors
    try:
        # Load the mobile network settings from the config file
        config = json.load(open(local_config_path))
        modem_config = config['mobile_network']
        m_uname = modem_config['username']
        m_pwd = modem_config['password']
        m_host = modem_config['hostname']
        m_conname = m_host.replace('.','') + config['device']['config_id']

        # Add the profile to the network manager
        logging.info('Adding profile {}: host {} uname {} pwd {} to network manager'.format(m_conname, m_host, m_uname, m_pwd))
        nm_cmd = 'sudo nmcli connection add type gsm ifname \'*\' con-name \'{}\' apn \'{}\' connection.autoconnect yes'.format(m_conname, m_host)

        # Check if username and password aren't blank before adding them to the profile
        if m_uname.strip() != '':
            nm_cmd = nm_cmd + '  gsm.username {}'.format(m_uname)
        if m_pwd.strip() != '':
            nm_cmd = nm_cmd + '  gsm.password {}'.format(m_pwd)

        call_cmd_line(nm_cmd)

    except Exception as e:
        logging.info('Couldn\'t add network manager profile from config file: {}'.format(str(e)))


def mount_ext_sd(sd_mount_loc, dev_file_str='mmcblk1p'):

    """
    Tries to mount the external SD card, and if not possible flashes an error
    code on the LEDs
    """

    # Check if SD card already mounted
    if os.path.exists(sd_mount_loc) and os.path.ismount(sd_mount_loc):
        logging.info('Device already mounted to {}. Assuming SD card, but warning - might not be!'.format(sd_mount_loc))
        return

    # Make sure sd_mount_loc is an empty directory
    if os.path.exists(sd_mount_loc): shutil.rmtree(sd_mount_loc)
    os.makedirs(sd_mount_loc)

    # List potential devices that could be the SD card
    potential_dev_fs = [f for f in os.listdir('/dev') if dev_file_str in f]

    for dev_f in potential_dev_fs:
        # Try to mount each partition in turn
        logging.info('Trying to mount device {} to {}'.format(dev_f, sd_mount_loc))
        call_cmd_line('sudo mount -orw /dev/{} {}'.format(dev_f, sd_mount_loc))

        # Check if device mounted successfully
        if os.path.ismount(sd_mount_loc):
            logging.info('Successfully mounted {} to {}'.format(dev_f, sd_mount_loc))
            break

    # If unable to mount SD then raise an exception
    if not os.path.ismount(sd_mount_loc):
        logging.critical('ERROR: Could not mount external SD card to {}'.format(sd_mount_loc))
        raise Exception('Could not mount external SD card to {}'.format(sd_mount_loc))


def check_sd_not_corrupt(sd_mnt_dir):

    """
    Check the SD card allows writing data to each of the subdirectories, as
    sometimes slightly corrupt cards will allow reads and writes to some locations
    but not all. If corrupt, this function will raise an Exception
    """

    # Write and delete a dummy files to each subdirectory of the SD card to (quickly) check it's not corrupt
    for (dirpath, dirnames, filenames) in os.walk(sd_mnt_dir):
        for subd in dirnames:
            subdir_path = os.path.join(dirpath, subd)

            # Ignore system generated directories
            if 'System Volume information' in subdir_path: continue

            # Create and delete an empty text file
            dummy_f_path = os.path.join(subdir_path, 'test_f.txt')
            f = open(dummy_f_path, 'a')
            f.close()
            os.remove(dummy_f_path)

    logging.info('check_sd_not_corrupt passed with no issues - SD should be OK')

    return True


def merge_dirs(root_src_dir, root_dst_dir, delete_src=True):

    """
    Merge two directories including all subdirectories, optionally delete root_src_dir
    """

    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.copy(src_file, dst_dir)

    if delete_src:
        shutil.rmtree(root_src_dir, ignore_errors=True)

def discover_serial():

    """
    Function to return the Raspberry Pi serial from /proc/cpuinfo

    Returns:
        A string containing the serial number or an error placeholder
    """

    # parse /proc/cpuinfo
    cpu_serial = None
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpu_serial = line.split(':')[1].strip()
        f.close()
        # No serial line found?
        if cpu_serial is None:
            raise IOError
    except IOError:
        cpu_serial = "ERROR000000001"

    cpu_serial = "RPiID-{}".format(cpu_serial)

    return cpu_serial


def check_reboot_due(reboot_time_utc):
    """
    Check if a device reboot is due
    """

    now = datetime.utcnow()
    uptime_s = get_sys_uptime()

    if uptime_s > 3600 and now.hour == reboot_time_utc.hour:
        return True
    else:
        return False


def get_sys_uptime():
    """
    Get system uptime in seconds
    """

    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])

    return uptime_seconds



def disable_modem():
    """
    Turn off the Sierra Wireless modem by turning off 3V7_EN
    """

    # Define outputs on correct GPIO lines
    EN_GPIO = 8
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(EN_GPIO, GPIO.OUT)

    # Set 3V7_EN to low
    GPIO.output(EN_GPIO, 0)
    logging.info('3V7 to modem disabled')


def enable_modem(verbose=False):
    """
    Enable the Sierra Wireless modem by turning on 3V7_EN and pulsing POWER_ON_N
    high for 1 second.

    Then wait for the modem to actually boot and enumerate on USB
    """

    # Define outputs on correct GPIO lines
    EN_GPIO = 8
    POWER_ON_GPIO = 5
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(EN_GPIO, GPIO.OUT)
    GPIO.setup(POWER_ON_GPIO, GPIO.OUT)

    # Set 3V7_EN to high
    logging.info('Setting EN_GPIO high')
    GPIO.output(EN_GPIO, 1)
    time.sleep(1)

    # Pulse POWER_ON_N high for 1 second
    logging.info('Pulsing POWER_ON_N high for 1s')
    GPIO.output(POWER_ON_GPIO, 1)
    time.sleep(1)
    GPIO.output(POWER_ON_GPIO, 0)

    # Wait for modem to boot
    logging.info('Waiting for modem to boot and enumerate...')

    modem_enumerated = False
    total_tries = 0
    max_tries = 10
    sleep_inc = 2
    while not modem_enumerated and total_tries < max_tries:
        stdout = call_cmd_line('lsusb', use_shell=False)
        if 'Sierra Wireless' in stdout:
            modem_enumerated = True
            break
        else:
            time.sleep(sleep_inc)
            total_tries += 1
            if verbose:
                logging.info('No modem on USB, trying again ({}/{})'.format(total_tries, max_tries))

    if modem_enumerated:
        logging.info('Modem successfully enumerated on USB')
    else:
        logging.info('Modem did not enumerate on USB after {} tries'.format(max_tries))

    return modem_enumerated


def clean_dirs(working_dir, upload_dir, data_dir):

    """
    Function to tidy up the directory structure, any files left in the working
    directory and any directories in upload emptied by server mirroring

    Once tidied, then make new directories if needed

    Args
        working_dir: Path to the working directory
        upload_dir: Path to the upload directory
        data_dir: Path to the data directory
    """

    ### CLEAN EMPTY DIRECTORIES

    if os.path.exists(working_dir):
        logging.info('Cleaning up working directory')
        shutil.rmtree(working_dir, ignore_errors=True)

    if os.path.exists(upload_dir):
        # Remove empty directories in the upload directory, from bottom up
        for subdir, dirs, files in os.walk(upload_dir, topdown=False):
            if not os.listdir(subdir):
                logging.info('Removing empty upload directory: {}'.format(subdir))
                shutil.rmtree(subdir, ignore_errors=True)


    ### MAKE NEW DIRECTORIES (if needed)

    # Check for / create working directory (where temporary files will be stored)
    if os.path.exists(working_dir) and os.path.isdir(working_dir):
        logging.info('Using {} as working directory'.format(working_dir))
    else:
        os.makedirs(working_dir)
        logging.info('Created {} as working directory'.format(working_dir))

    # Check for / create upload directory (root which will be used to upload files from)
    if os.path.exists(upload_dir) and os.path.isdir(upload_dir):
        logging.info('Using {} as upload directory'.format(upload_dir))
    else:
        os.makedirs(upload_dir)
        logging.info('Created {} as upload directory'.format(upload_dir))

    # Check for / create data directory (where final data files will be stored) - must be under upload_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        logging.info('Using {} as data directory'.format(data_dir))
    else:
        os.makedirs(data_dir)
        logging.info('Created {} as data directory'.format(data_dir))
