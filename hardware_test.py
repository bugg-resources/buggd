""" This script is run by bugg-test.service once the hardware is fully configured.
It exercises some hardware for production line test."""
from systemd import journal
import subprocess

SYSLOG_ID = "hardware-test"
TEST_SERVICE = "bugg-test.service"

# Journal priorities can be:
# LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR, LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG

def disable_systemd_service(service_name):
    """ systemd-python doesn't have a method to disable a service, so we use subprocess."""
    try:
        subprocess.run(['systemctl', 'disable', service_name], check=True)
        print(f"Service {service_name} successfully disabled.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to disable service {service_name}: {e}")


def main():
    """ Start the hardware test, write to journal """
    journal.send("Start hardware test", SYSLOG_IDENTIFIER=SYSLOG_ID, PRIORITY=journal.LOG_INFO)
    journal.send("Doing a thing...", SYSLOG_IDENTIFIER=SYSLOG_ID, PRIORITY=journal.LOG_INFO)
    journal.send("End hardware test", SYSLOG_IDENTIFIER=SYSLOG_ID, PRIORITY=journal.LOG_INFO)

    journal.send("Disabling bugg-test.service", SYSLOG_IDENTIFIER=SYSLOG_ID, PRIORITY=journal.LOG_INFO)
    disable_systemd_service(TEST_SERVICE)

if __name__ == "__main__":
    main()
