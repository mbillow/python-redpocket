import os
import json
import pytest
import responses
import pathlib


@pytest.fixture(scope="session")
def mock_set_cookie_header() -> dict:
    return {
        "Set-Cookie": (
            "redpocket=p7cpn62s09rufdl0ggsskjrib7; "
            "expires=Sun, 02-May-2021 18:41:01 GMT; "
            "Max-Age=86400; path=/; HttpOnly"
        )
    }


@pytest.fixture(scope="session")
def mock_responses_path() -> pathlib.Path:
    return pathlib.Path(os.getcwd()) / "tests" / "mock_responses"


@pytest.fixture(scope="session")
def mock_line(mock_responses_path: pathlib.Path) -> dict:
    with open(mock_responses_path / "other_lines.json", "r") as other_lines:
        return json.load(other_lines)["return_data"]["confirmedLines"][0]


@pytest.fixture(scope="session")
def mock_other_lines(mock_responses_path: pathlib.Path) -> dict:
    with open(mock_responses_path / "other_lines.json", "r") as other_lines:
        return json.load(other_lines)


@pytest.fixture(scope="session")
def mock_line_details(mock_responses_path: pathlib.Path) -> dict:
    with open(mock_responses_path / "line_details.json", "r") as line_details:
        return json.load(line_details)["return_data"]


@pytest.fixture(scope="session")
def mock_login_page(mock_responses_path: pathlib.Path) -> str:
    with open(mock_responses_path / "login_form.html", "r") as login:
        return login.read()


@pytest.fixture(scope="session")
def mock_login_page_wo_csrf(mock_responses_path: pathlib.Path) -> str:
    with open(mock_responses_path / "login_form_without_csrf.html", "r") as login:
        return login.read()


@pytest.fixture
def successful_login(mock_login_page: str, mock_set_cookie_header: dict) -> None:
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
