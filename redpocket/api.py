import re
import requests
import logging
import base64
from dataclasses import dataclass, InitVar
from datetime import datetime
from typing import List, Callable, Tuple, Any, Union, Optional

from .exceptions import RedPocketException, RedPocketAuthError, RedPocketAPIError


def _today() -> datetime.date:
    """Partly for readability and mostly for testability."""
    return datetime.today().date()


@dataclass
class RedPocketPhone:
    """Phone specific Line Details"""

    model: str
    imei: str
    sim: str
    esn: str

    @classmethod
    def from_api(cls, api_response: dict):
        return cls(
            model=api_response.get("model"),
            imei=api_response.get("imei"),
            sim=api_response.get("sim"),
            esn=api_response.get("esn"),
        )


@dataclass
class RedPocketLineDetails:
    """Representation of RedPocket Line Details"""

    number: int
    product_code: str
    status: str
    plan_id: str
    plan_code: str
    expiration: Optional[datetime.date]
    last_autorenew: Optional[datetime.date]
    last_expiration: Optional[datetime.date]
    main_balance: Union[int, float]
    voice_balance: Union[int, float]
    messaging_balance: Union[int, float]
    data_balance: Union[int, float]
    phone: RedPocketPhone

    @classmethod
    def from_api(cls, api_response: dict):
        def sanitize_balance(balance: str) -> Union[int, float]:
            """API design is hard... What even is a none type..."""
            if balance.lower() in ["unlimited", "n/a"]:
                return -1
            # Take the string and convert it to a numeric type.
            to_number = float(balance.replace(",", ""))
            # Only return a float if we need decimal precision.
            return to_number if to_number % 1 else int(to_number)

        def str_to_date(date_str: str) -> Optional[datetime.date]:
            """Two formats of date values... because why not?!"""
            if not date_str:
                # If the type is falsy, return None.
                return
            try:
                return datetime.strptime(date_str, "%m/%d/%Y").date()
            except ValueError:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except TypeError:
                # If the type is truthy, but can't be cast to a date, return None.
                return

        return cls(
            number=int(api_response.get("mdn")),
            product_code=api_response.get("productCode"),
            status=api_response.get("accountStatus"),
            plan_id=api_response.get("plan_id"),
            plan_code=api_response.get("plan_code"),
            expiration=str_to_date(api_response.get("aed", "12/31/1969")),
            last_autorenew=str_to_date(
                api_response.get("lastAutoRenewDate", "12/31/1969")
            ),
            last_expiration=str_to_date(
                api_response.get("lastExpirationDate", "12/31/1969")
            ),
            main_balance=sanitize_balance(api_response.get("main_balance", "N/A")),
            voice_balance=sanitize_balance(api_response.get("voice_balance", "N/A")),
            messaging_balance=sanitize_balance(
                api_response.get("messaging_balance", "N/A")
            ),
            data_balance=sanitize_balance(api_response.get("data_balance", "N/A")),
            phone=RedPocketPhone.from_api(api_response),
        )

    @property
    def remaining_days_in_cycle(self) -> int:
        """Number of days until plan is refreshed."""
        if not self.expiration:
            return 0
        delta = self.expiration - _today()
        return int(delta.days)

    @property
    def remaining_months_purchased(self) -> int:
        """Number of months left for automatic renewal."""
        if not self.last_expiration:
            return 0
        start_date = _today()
        end_date = self.last_expiration
        return (end_date.year - start_date.year) * 12 + (
            end_date.month - start_date.month
        )


@dataclass
class RedPocketLine:
    """Dataclass for RedPocket Line Information"""

    account_id: str
    number: int
    plan: str
    expiration: datetime.date
    family: bool
    details_callback: InitVar[Callable] = None

    def __post_init__(self, details_callback: Callable):
        self._details_callback = details_callback

        # If a callback function is not provided, we need to fail gracefully.
        if not details_callback:

            def fail_to_get_details(_line: Any) -> RedPocketLineDetails:
                raise RedPocketException(
                    "Cannot get line details. No callback provided!"
                )

            self._details_callback = fail_to_get_details

    def __hash__(self) -> int:
        return self.number

    @property
    def account_hash(self) -> str:
        hash_bytes = base64.b64encode(self.account_id.encode("utf-8"))
        return hash_bytes.decode("utf-8")

    def get_details(self) -> RedPocketLineDetails:
        return self._details_callback(self.account_hash)

    @classmethod
    def from_other_lines_api(
        cls, api_response: dict, details_callback: Callable = None
    ):
        return cls(
            account_id=api_response.get("e_users_accounts_id"),
            number=int(api_response.get("mdn")),
            plan=api_response.get("plan_description"),
            expiration=datetime.strptime(
                api_response.get("aed", "12/31/1969"), "%m/%d/%Y"
            ).date(),
            family=False if api_response.get("family") == "no" else True,
            details_callback=details_callback,
        )


class RedPocket:
    """Simple API Interface for RedPocket Accounts"""

    def __init__(self, username: str, password: str):
        self._logger = logging.getLogger("redpocket")
        self._session = requests.Session()
        self._username = username
        self._password = password
        self._login()

    def _fetch_csrf(self) -> str:
        """
        Request the login page and parse the CSRF token out.
        :return: CSRF Token
        :rtype str
        """
        login_page = self._session.get("https://www.redpocket.com/login")
        csrf_element = re.search(
            r'<input type="hidden" name="csrf" value="([\w|-]+)">', login_page.text
        )

        if csrf_element:
            csrf = csrf_element.group(1)
            self._logger.debug("Using CSRF: %s", csrf)
            return csrf

        raise RedPocketException("Failed to get CSRF token from login page!")

    def _login(self):
        """Login to the RedPocket account."""

        # Make sure the CSRF is not an empty string.
        csrf = self._fetch_csrf()

        form_data = {"mdn": self._username, "password": self._password, "csrf": csrf}
        login_req = self._session.post(
            "https://www.redpocket.com/login", data=form_data
        )
        returned_ok = login_req.status_code == requests.codes.ok
        has_cookie = "redpocket" in login_req.cookies.keys()
        did_redirect = login_req.url == "https://www.redpocket.com/my-lines"
        if returned_ok and has_cookie and did_redirect:
            return
        raise RedPocketAuthError("Failed to authenticate to RedPocket!")

    def request(
        self,
        method: str = "get",
        url: str = "",
        params: dict = None,
        data: dict = None,
        _is_retry: bool = False,
    ) -> requests.Response:
        self._logger.debug("API Request: [%s] URL: %s", method.upper(), url)

        request = self._session.request(
            method=method, url=url, params=params, data=data
        )
        if request.status_code != requests.codes.ok:
            raise RedPocketAPIError("API Returned Non-200 Response!")

        request_json = request.json()

        return_code = request_json.get("return_code", -1)
        if return_code == 1:
            return request

        if return_code == 11 and _is_retry:
            raise RedPocketAuthError("Request failed even after re-authentication!")

        # If the API thinks we aren't logged-in, re-authenticate.
        if return_code == 11:
            self._login()
            return self.request(method=method, url=url, data=data, _is_retry=True)

        raise RedPocketAPIError("Unknown Error", return_code)

    def get_lines(self) -> List[RedPocketLine]:
        lines = self.request(url="https://www.redpocket.com/account/get-other-lines")
        lines_json = lines.json()

        return [
            RedPocketLine.from_other_lines_api(
                api_response=account, details_callback=self.get_line_details
            )
            for account in lines_json.get("return_data", {}).get("confirmedLines", [])
        ]

    def get_line_details(self, account_hash: str) -> RedPocketLineDetails:
        params = {
            "id": account_hash,
            "type": "api",
        }
        details = self.request(
            url="https://www.redpocket.com/account/get-details",
            params=params,
        )
        details_json = details.json()
        return RedPocketLineDetails.from_api(
            api_response=details_json.get("return_data")
        )

    def get_all_line_details(self) -> List[Tuple[RedPocketLine, RedPocketLineDetails]]:
        all_lines = self.get_lines()
        return [(line, line.get_details()) for line in all_lines]
