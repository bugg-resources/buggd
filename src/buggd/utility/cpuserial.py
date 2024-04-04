""" Module to discover the Raspberry Pi serial number """

def discover_serial():

    """
    Function to return the Raspberry Pi serial from /proc/cpuinfo

    Returns:
        A string containing the serial number or an error placeholder
    """

    # parse /proc/cpuinfo
    cpu_serial = None
    try:
        f = open('/proc/cpuinfo', 'r', encoding='utf-8')
        for line in f:
            if line[0:6] == 'Serial':
                cpu_serial = line.split(':')[1].strip()
        f.close()
        # No serial line found?
        if cpu_serial is None:
            raise IOError
    except IOError:
        cpu_serial = "ERROR000000001"

    cpu_serial = f"RPiID-{cpu_serial}"

    return cpu_serial
