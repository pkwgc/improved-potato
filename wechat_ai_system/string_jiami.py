import base64
import rsa


def rsaenc(_model, _systemVersion, _deviceUid, _phoneNum, _timestamp, _authentication, _slipDistance, _slipTime):
    _model = stringPadRight(_model, 10)
    _systemVersion = stringPadRight(_systemVersion, 5)
    _deviceUid = stringPadRight(_deviceUid, 12)
    _phoneNum = stringPadRight(_phoneNum, 11)
    _timestamp = stringPadRight(_timestamp, 14)
    _authentication = stringPadRight(_authentication, 6)
    _slipDistance = stringPadRight(_slipDistance, 2)
    _slipTime = stringPadRight(_slipTime, 4)
    datastr = _model + _systemVersion + _deviceUid + _phoneNum + _timestamp + _authentication + _slipDistance + _slipTime
    #print(datastr)
    rsa_public_key = list()
    rsa_public_key.append('-----BEGIN PUBLIC KEY-----')
    rsa_public_key.append('MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBkLT15ThVgz6/NOl6s8GNPofdWzWbCkWnkaAm7O2LjkM1H7dMvzkiqdxU02jamGRHLX/ZNMCXHnPcW/sDhiFCBN18qFvy8g6VYb9QtroI09e176s+ZCtiv7hbin2cCTj99iUpnEloZm19lwHyo69u5UMiPMpq0/XKBO8lYhN/gwIDAQAB')
    rsa_public_key.append('-----END PUBLIC KEY-----')
    rsa_public_key = '\n'.join(rsa_public_key)
    rsa_public_key1 = rsa_public_key.encode()
    key=rsa.PublicKey.load_pkcs1_openssl_pem(rsa_public_key1)
    ss = rsa.encrypt(str.encode(datastr), key)
    sss = base64.b64encode(ss).decode("utf-8")
    return sss
def stringPadRight(str1, len1):
    result = ""
    if len(str1) >= len1:
        return str1[:len1]
    else:
        i = len1 - len(str1)
        while i >= 1:
            i = i - 1
            result = result + "$"
        return result

def cocode(temp):
    strdata = ""
    for char in temp:
        strdata = strdata + chr(ord(char) + 2)
    return strdata
