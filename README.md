# 2Captcha.com Python API

This library implements a simple to use wrapper around the 2Captcha.com API.

### Installation
From PyPi
```
pip install twocaptchaapi
```

From source
```
git clone https://github.com/athre0z/twocaptcha-api.git
cd twocaptcha-api
python setup.py install
```

### Examples

#### Initializing the API
```python
from twocaptchaapi import TwoCaptchaApi
api = TwoCaptchaApi('<API KEY>')
```

#### Solving a captcha blockingly
```python
with open('/my/captcha/path.png', 'rb') as captcha_file:
    captcha = api.solve(captcha_file)

print(captcha.await_result())
```
Waits until the captcha is either solved or an error occurred (indicated through an exception).

#### Solve captcha "non-blockingly"
```python
captcha = api.solve(captcha_file)
print(captcha.try_get_result())
```
If already available, prints the captcha text, else `None`. Please note that while this code doesn't repeateately asks the API if the captcha was solved, the HTTP request is still sent synchronously, so this method isn't *really* non-blocking.

#### Reporting a bad captcha
```python
result = captcha.await_result()
if use_captcha_code(result) == 'failed':
    captcha.report_bad()
```

#### Query account balance
```python
print(api.get_balance())
```

### Compatibilty
This library was successfully tested on Python 2.7 and 3.5. Python versions < 2.7 are *not* officially supported.

### License
This code is released under MIT license. Dependencies are under their respective licenses.

*This project is _not_ affiliated with, maintained, authorized, endorsed or sponsored by 2Captcha.com or any of its affiliates.*
