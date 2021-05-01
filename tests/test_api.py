import pytest
import responses
from unittest.mock import MagicMock
from datetime import date, datetime
from redpocket import (
    RedPocket,
    RedPocketAuthError,
    RedPocketException,
    RedPocketAPIError,
)
from redpocket.api import _today, RedPocketPhone, RedPocketLine, RedPocketLineDetails


def test_today():
    assert _today() == datetime.today().date()


def test_phone_from_api(mock_line_details: dict):
    phone = RedPocketPhone.from_api(api_response=mock_line_details)
    assert phone.model == mock_line_details["model"]
    assert phone.imei == mock_line_details["imei"]
    assert phone.sim == mock_line_details["sim"]
    assert phone.esn == mock_line_details["esn"]


def test_line_details_from_api(mocker, mock_line_details: dict):
    details = RedPocketLineDetails.from_api(api_response=mock_line_details)
    assert details.number == 1234567890
    assert details.product_code == mock_line_details["productCode"]
    assert details.status == mock_line_details["accountStatus"]
    assert details.plan_id == mock_line_details["plan_id"]
    assert details.plan_code == mock_line_details["plan_code"]
    assert details.expiration == date(year=2021, month=5, day=12)
    assert details.last_expiration == date(year=2022, month=1, day=2)
    assert details.last_autorenew == date(year=2021, month=12, day=3)
    assert details.main_balance == -1
    assert details.voice_balance == -1
    assert details.messaging_balance == -1
    assert details.data_balance == 7657

    mocker.patch("redpocket.api._today", return_value=date(year=2021, month=5, day=1))
    assert details.remaining_days_in_cycle == 11
    assert details.remaining_months_purchased == 8


def test_line_from_api(mock_line: dict):
    mock_callback = MagicMock()

    line = RedPocketLine.from_other_lines_api(
        api_response=mock_line, details_callback=mock_callback
    )

    assert line.account_id == mock_line["e_users_accounts_id"]
    assert line.number == 1234567890
    assert line.plan == mock_line["plan_description"]
    assert line.expiration == date(year=2022, month=1, day=2)
    assert not line.family
    assert line.__hash__() == 1234567890

    line.get_details()
    mock_callback.assert_called_once_with("MTIzNDU2")


def test_line_without_callback(mock_line: dict):
    line = RedPocketLine.from_other_lines_api(api_response=mock_line)
    with pytest.raises(RedPocketException) as exc:
        line.get_details()
    assert exc.value.message == "Cannot get line details. No callback provided!"


@responses.activate
def test_login_bad_credentials(mock_login_page: str, mock_set_cookie_header: dict):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/login",
        status=200,
        body=mock_login_page,
    )
    responses.add(
        responses.POST,
        "https://www.redpocket.com/login",
        status=200,
        headers=mock_set_cookie_header,
    )
    with pytest.raises(RedPocketAuthError) as err:
        RedPocket(username="fake", password="password")

    assert err.value.message == "Failed to authenticate to RedPocket!"


@responses.activate
def test_login_good_credentials(successful_login: None):
    RedPocket(username="fake", password="password")


@responses.activate
def test_login_missing_csrf(mock_login_page_wo_csrf: str):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/login",
        status=200,
        body=mock_login_page_wo_csrf,
    )
    with pytest.raises(RedPocketException) as exc:
        RedPocket(username="fake", password="password")
    assert exc.value.message == "Failed to get CSRF token from login page!"


@responses.activate
def test_get_line(successful_login: None, mock_line: dict):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 1, "return_data": {"confirmedLines": [mock_line]}},
    )
    rp = RedPocket(username="fake", password="password")
    lines = rp.get_lines()

    assert len(lines) == 1
    assert type(lines[0]) == RedPocketLine
    assert lines[0].number == 1234567890


@responses.activate
def test_get_line_details(
    successful_login: None, mock_line: dict, mock_line_details: dict
):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 1, "return_data": {"confirmedLines": [mock_line]}},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-details?id=MTIzNDU2",
        status=200,
        json={"return_code": 1, "return_data": mock_line_details},
    )
    rp = RedPocket(username="fake", password="password")
    lines = rp.get_lines()
    line_details = lines[0].get_details()

    assert line_details.number == 1234567890


@responses.activate
def test_get_all_line_details(
    successful_login: None, mock_line: dict, mock_line_details: dict
):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 1, "return_data": {"confirmedLines": [mock_line]}},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-details?id=MTIzNDU2",
        status=200,
        json={"return_code": 1, "return_data": mock_line_details},
    )
    rp = RedPocket(username="fake", password="password")
    lines = rp.get_all_line_details()

    assert len(lines) == 1
    assert lines[0][0].number == 1234567890
    assert lines[0][1].number == 1234567890


@responses.activate
def test_request_retry_login_success(
    successful_login: None,
    mock_login_page: str,
    mock_set_cookie_header: dict,
    mock_line: dict,
):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 11, "return_data": {}},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/login",
        status=200,
        body=mock_login_page,
    )
    responses.add(
        responses.POST,
        "https://www.redpocket.com/login",
        status=302,
        headers={**mock_set_cookie_header, "Location": "/my-lines"},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/my-lines",
        status=200,
        headers=mock_set_cookie_header,
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 1, "return_data": {"confirmedLines": [mock_line]}},
    )

    rp = RedPocket(username="fake", password="password")
    lines = rp.get_lines()

    assert len(lines) == 1
    assert type(lines[0]) == RedPocketLine
    assert lines[0].number == 1234567890


@responses.activate
def test_request_retry_login_failure(
    successful_login: None,
    mock_login_page: str,
    mock_set_cookie_header: dict,
):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 11, "return_data": {}},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/login",
        status=200,
        body=mock_login_page,
    )
    responses.add(
        responses.POST,
        "https://www.redpocket.com/login",
        status=302,
        headers={**mock_set_cookie_header, "Location": "/my-lines"},
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/my-lines",
        status=200,
        headers=mock_set_cookie_header,
    )
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": 11, "return_data": {}},
    )

    rp = RedPocket(username="fake", password="password")

    with pytest.raises(RedPocketAuthError) as exc:
        rp.get_lines()
    assert exc.value.message == "Request failed even after re-authentication!"


@responses.activate
def test_request_non_200(successful_login: None):
    responses.add(
        responses.GET, "https://www.redpocket.com/account/get-other-lines", status=404
    )
    rp = RedPocket(username="fake", password="password")

    with pytest.raises(RedPocketAPIError) as exc:
        rp.get_lines()
    assert exc.value.message == "API Returned Non-200 Response!"


@responses.activate
def test_request_unknown_return_code(successful_login: None):
    responses.add(
        responses.GET,
        "https://www.redpocket.com/account/get-other-lines",
        status=200,
        json={"return_code": -1},
    )
    rp = RedPocket(username="fake", password="password")

    with pytest.raises(RedPocketAPIError) as exc:
        rp.get_lines()
    assert exc.value.message == "Unknown Error"
    assert exc.value.return_code == -1
