from __future__ import unicode_literals, print_function, absolute_import, division

import requests
import time
import imghdr
import sys
import base64
import binascii


# ----------------------------------------------------------------------------------------------- #
# [Python version compatibility]                                                                  #
# ----------------------------------------------------------------------------------------------- #


if sys.version_info[0] == 2:
    from HTMLParser import HTMLParser
elif sys.version_info[0] == 3:
    from html.parser import HTMLParser


if sys.version_info[:2] >= (3, 5):
    # Py3.5 and upwards provide a function directly in the root module.
    from html import unescape
else:
    # For older versions, we use the bound method.
    unescape = HTMLParser().unescape


# ----------------------------------------------------------------------------------------------- #
# [Exception types]                                                                               #
# ----------------------------------------------------------------------------------------------- #


class TwoCaptchaApiError(Exception):
    """Base class for all 2Captcha API exceptions."""
    pass


class CommunicationError(TwoCaptchaApiError):
    """An error occurred while communicating with the 2Captcha API."""
    pass


class ResponseFormatError(TwoCaptchaApiError):
    """The response data doesn't fit what we expected."""
    pass


class OperationFailedError(TwoCaptchaApiError):
    """The 2Captcha API indicated failure of an operation."""
    pass


# ----------------------------------------------------------------------------------------------- #
# [Internal convenience decorators]                                                               #
# ----------------------------------------------------------------------------------------------- #


def _rewrite_http_to_com_err(func):
    """Rewrites HTTP exceptions from `requests` to `CommunicationError`s."""
    def proxy(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.RequestException:
            raise CommunicationError(
                "an error occurred while communicating with the 2Captcha API"
            )
    return proxy


def _rewrite_to_format_err(*exception_types):
    """Rewrites arbitrary exception types to `ResponseFormatError`s."""
    def decorator(func):
        def proxy(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if any(isinstance(e, x) for x in exception_types):
                    raise ResponseFormatError("unexpected response format")
                raise
        return proxy
    return decorator


def _is_base64(string):
    """Validates if a string is a base64 one. Returns False otherwise."""
    try:
        base64.decodestring(string)
        return True
    except (binascii.Error):
        return False


def _captcha_from_response(text, two_captcha_api_object):
    """
    Takes a text from a captcha request and look for expected format. 
    Raise OperationFailedError if the text does not comply. 
    """

    # Success?
    if '|' in text:
        _, captcha_id = text.split('|')
        return Captcha(two_captcha_api_object, captcha_id)

    # Nope, failure.
    raise OperationFailedError("Operation failed: %r" % (text,))

# ----------------------------------------------------------------------------------------------- #
# [Public API]                                                                                    #
# ----------------------------------------------------------------------------------------------- #


class TwoCaptchaApi(object):
    """Provides an interface to the 2Captcha API."""
    BASE_URL = 'http://2captcha.com'
    REQ_URL = BASE_URL + '/in.php'
    RES_URL = BASE_URL + '/res.php'
    LOAD_URL = BASE_URL + '/load.php'

    def __init__(self, api_key):
        self.api_key = api_key

    def get(self, url, params, **kwargs):
        """Sends a HTTP GET, for low-level API interaction."""
        params['key'] = self.api_key
        return requests.get(url, params, **kwargs)

    def post(self, url, data, **kwargs):
        """Sends a HTTP POST, for low-level API interaction."""
        data['key'] = self.api_key
        return requests.post(url, data, **kwargs)

    @_rewrite_http_to_com_err
    @_rewrite_to_format_err(ValueError)
    def get_balance(self):
        """Obtains the balance on our account, in dollars."""
        return float(self.get(self.RES_URL, {
            'action': 'getbalance'
        }).text)

    @_rewrite_http_to_com_err
    def get_stats(self, date):
        """Obtains statistics about our account, as XML."""
        return self.get(self.RES_URL, {
            'action': 'getstats',
            'date': date if type(date) == str else date.isoformat(),
        }).text

    @_rewrite_http_to_com_err
    def get_load(self):
        """Obtains load statistics of the server."""
        return self.get(self.LOAD_URL, {}).text

    @_rewrite_http_to_com_err
    @_rewrite_to_format_err(IndexError, ValueError)
    def solve(self, file, captcha_parameters=None):
        """
        Queues a captcha for solving. `file` may either be a path, a file object or a base64 string.
        Optional parameters for captcha solving may be specified in a `dict` via
        `captcha_parameters`, for valid values see section "Additional CAPTCHA parameters"
        in API documentation here:
        https://2captcha.com/api-2captcha
        """
        if _is_base64(file):
            # Send request.
            text = self.post(
                self.REQ_URL,
                data = {'key': self.api_key, 'method': 'base64', 'body': file}
            ).text
        else:
            # If path was provided, load file.
            if type(file) == str:
                with open(file, 'rb') as f:
                    raw_data = f.read()
            else:
                raw_data = file.read()

            # Detect image format.
            file_ext = imghdr.what(None, h=raw_data)

            # Send request.
            text = self.post(
                self.REQ_URL,
                captcha_parameters or {'method': 'post'},
                files={'file': ('captcha.' + file_ext, raw_data)}
            ).text

        return _captcha_from_response(text, self)

    @_rewrite_http_to_com_err
    @_rewrite_to_format_err(IndexError, ValueError)
    def solve_googlev2(self, data_key, protected_url, captcha_parameters=None):
        """
        Queues a captcha for solving. `data_key` is the extracted string from the captcha page.
        The field `protected_url` is the URL of the page after the captcha.
        Optional parameters for captcha solving may be specified in a `dict` via
        `captcha_parameters`, for valid values see section "Additional CAPTCHA parameters"
        in API documentation here:
        https://2captcha.com/api-2captcha
        """
        # Send request.
        text = self.get(
            self.REQ_URL,
            params = {
                'key': self.api_key, 
                'method': 'userrecaptcha', 
                'googlekey': data_key,
                'pageurl': protected_url
            }
        ).text

        return _captcha_from_response(text, self)


class Captcha(object):
    """Represents a captcha that was queued for solving."""

    def __init__(self, api, captcha_id):
        """
        Constructs a new captcha awaiting result. Instances should not be created
        manually, but using the `TwoCaptchaApi.solve` method.
        :type api: TwoCaptchaApi
        """
        self.api = api
        self.captcha_id = captcha_id
        self._cached_result = None
        self._reported_bad = False

    @_rewrite_http_to_com_err
    @_rewrite_to_format_err(ValueError)
    def try_get_result(self):
        """
        Tries to obtain the captcha text. If the result is not yet available,
        `None` is returned.
        """
        if self._cached_result is not None:
            return self._cached_result

        text = self.api.get(self.api.RES_URL, {
            'action': 'get',
            'id': self.captcha_id,
        }).text

        # Success?
        if '|' in text:
            _, captcha_text = unescape(text).split('|')
            self._cached_result = captcha_text
            return captcha_text

        # Nope, either failure or not ready, yet. Yep, they mistyped "Captcha".
        if text in ('CAPCHA_NOT_READY', 'CAPTCHA_NOT_READY'):
            return None

        # Failure.
        raise OperationFailedError("Operation failed: %r" % (text,))

    def await_result(self, sleep_time=1.):
        """
        Obtains the captcha text in a blocking manner.
        Retries every `sleep_time` seconds.
        """
        while True:
            # print('Trying to obtain result ..')
            result = self.try_get_result()
            if result is not None:
                break
            time.sleep(sleep_time)
        return result

    @_rewrite_http_to_com_err
    def report_bad(self):
        """Reports to the server that the captcha was solved incorrectly."""
        if self._cached_result is None:
            raise ValueError("tried reporting bad state for captcha not yet retrieved")
        if self._reported_bad:
            raise ValueError("tried double-reporting bad captcha")

        resp = self.api.get(self.api.RES_URL, {
            'action': 'reportbad',
            'id': self.captcha_id,
        })
        if resp.text != 'OK_REPORT_RECORDED':
            raise ResponseFormatError("unexpected API response")
