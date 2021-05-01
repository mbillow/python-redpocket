import logging
from getpass import getpass

from . import RedPocket

logger = logging.getLogger("redpocket")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

username = input("RedPocket Username: ")
password = getpass("Password: ")

redpocket = RedPocket(username=username, password=password)

all_lines = redpocket.get_all_line_details()
for line, details in all_lines:
    print(f"\n== Red Pocket Line #{line.account_id} ==")
    print(f"  Number: {line.number}\n  Expires: {line.expiration}")
    print("  Details :")
    print("\n".join("    {}: {}".format(k, v) for k, v in details.__dict__.items()))
    print(f"    remaining_days_in_cycle: {details.remaining_days_in_cycle}")
    print(f"    remaining_months_purchased: {details.remaining_months_purchased}")
