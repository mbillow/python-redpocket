# python-redpocket

[![python38|39](https://img.shields.io/pypi/pyversions/python-redpocket)](https://pypi.org/project/python-redpocket/) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![codecov](https://codecov.io/gh/mbillow/python-redpocket/branch/main/graph/badge.svg?token=Q88GID8SSQ)](https://codecov.io/gh/mbillow/python-redpocket) [![pypi downloads](https://img.shields.io/pypi/dm/python-redpocket)](https://pypi.org/project/python-redpocket/)

A simple, fully tested, Pythonic wrapper around RedPocket Mobile's API.

## Example Usage

```python
from getpass import getpass
from redpocket import RedPocket

username = input("RedPocket Username: ")
password = getpass("Password:")

rp = RedPocket(username=username, password=password)

lines = rp.get_lines()
print(lines)
# [
#     RedPocketLine(
#         account_id='12345',
#         number=1234567890,
#         plan='Annual- Unlimited Everything + 8GB high speeds',
#         expiration=datetime.date(2022, 1, 2),
#         family=False
#     )
# ]

line_details = lines[0].get_details()
print(line_details)
# RedPocketLineDetails(
#     number=1234567890, 
#     product_code='GSMA', 
#     status='Active', 
#     plan_id='355', 
#     plan_code='E240GSMA', 
#     expiration=datetime.date(2021, 5, 12), 
#     last_autorenew=datetime.date(2021, 12, 3), 
#     last_expiration=datetime.date(2022, 1, 2), 
#     main_balance=-1, 
#     voice_balance=-1, 
#     messaging_balance=-1, 
#     data_balance=7657, 
#     phone=RedPocketPhone(model='Apple iPhone 12 A2172', imei='', sim='', esn='')

print(line_details.remaining_days_in_cycle)
# 11

print(line_details.remaining_months_purchased)
# 8
```

There is also a helper function to get all the lines and line details in one call:

```python
from redpocket import RedPocket

rp = RedPocket(username="", password="")
lines = rp.get_all_line_details()

print(lines)
# [
#     (
#         RedPocketLine(
#             account_id='12345', 
#             number=1234567890, 
#             plan='Annual- Unlimited Everything + 8GB high speeds', 
#             expiration=datetime.date(2022, 1, 2), 
#             family=False), 
#         RedPocketLineDetails(
#             number=1234567890, 
#             product_code='GSMA', 
#             status='Active', 
#             plan_id='355', 
#             plan_code='E240GSMA', 
#             expiration=datetime.date(2021, 5, 12), 
#             last_autorenew=datetime.date(2021, 12, 3), 
#             last_expiration=datetime.date(2022, 1, 2), 
#             main_balance=-1, 
#             voice_balance=-1, 
#             messaging_balance=-1, 
#             data_balance=7657, 
#             phone=RedPocketPhone(model='Apple iPhone 12 A2172', imei='', sim='', esn='')
#         )
#     )
# ]
```

If you know the hash or account number of the specific account you want to retrieve, you can do that as well:

```python
from redpocket import RedPocket

rp = RedPocket(username="", password="")

my_line_hash = rp.get_lines()[0].account_hash
print(my_line_hash)
# 'MTIzNDU2'

details = rp.get_line_details(account_hash=my_line_hash)
print(details)
# RedPocketLineDetails(
#     ...
# )
```
