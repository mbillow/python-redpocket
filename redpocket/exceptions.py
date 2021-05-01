"""
RedPocket Exceptions
"""


class RedPocketException(Exception):
    """Base API Exception"""

    def __init__(self, message: str = ""):
        self.message = message


class RedPocketAuthError(RedPocketException):
    """Invalid Account Credentials"""


class RedPocketAPIError(RedPocketException):
    """Error returned from API Call"""

    def __init__(self, message: str = "", return_code: int = -1):
        super().__init__(message=message)
        self.return_code = return_code
