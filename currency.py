import csv
import datetime
import os

import requests
import json

from tabulate import tabulate

GITHUB_EVENT_ACTION = os.getenv('GITHUB_EVENT_NAME')


def get_bnu():
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad, pad
    import base64

    key = os.getenv('KEY').encode()  # 16, 24, or 32 bytes長度的金鑰
    iv = os.getenv('IV').encode()  # 16 bytes長度的初始向量

    def aes_cbc_decrypt(key, iv, ciphertext):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = cipher.decrypt(ciphertext)
        return unpad(plaintext, 16).decode('utf-8')

    def aes_cbc_encrypt(key, iv, plaintext):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext.encode('utf-8'), 16))
        return ciphertext

    payload = {
        'params_decrypt_str': base64.b64encode(
            aes_cbc_encrypt(key, iv, 'ActionMethod=exchangeRate&ccy=JPY&pageLanguage=C&PageLanguage=zh_CN'))
    }
    response = requests.request("POST", "https://online.bnu.com.mo/mba/rate.do?RestJson=Y", data=payload).json()

    data = json.loads(aes_cbc_decrypt(key, iv, base64.standard_b64decode(response['params_encrypt_str'])))
    return float(data['rateList'][0]['noteMopSell']) * 100


def get_boc():
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://wxs.bocmacau.com',
        'Pragma': 'no-cache',
        'Referer': 'https://wxs.bocmacau.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    json_data = {
        'InstNo': '148',
        'Currency': 'MOP',
    }

    response = requests.post('https://wxs.bocmacau.com/wx/portal/WXQryExchangeRate', headers=headers,
                             json=json_data).json()
    for pair in response['List']:
        if pair['ExchangeCurrency'] == "JPY":
            boc_rate = pair['CSRate']
            boc_tt_rate = pair['TTSRate']
            return boc_rate, boc_tt_rate + 0.050


def get_union():
    response = requests.get(
        'https://www.unionpayintl.com/upload/jfimg/{}.json'.format(datetime.datetime.now().strftime("%Y%m%d")), ).json()

    for pair in response['exchangeRateJson']:
        if pair['transCur'] == 'JPY' and pair['baseCur'] == 'MOP':
            union_rate = pair['rateData'] * 100
            return union_rate, union_rate + 0.018


def get_visa():
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://www.visa.com.hk/zh_HK/support/consumer/travel-support/exchange-rate-calculator.html',
        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    }

    params = {
        'amount': '1',
        'fee': '0',
        'utcConvertedDate': datetime.datetime.now().strftime("%m/%d/%Y"),
        'exchangedate': datetime.datetime.now().strftime("%m/%d/%Y"),
        'fromCurr': 'MOP',
        'toCurr': 'JPY',
    }

    response = requests.get('https://www.visa.com.hk/cmsapi/fx/rates', params=params, headers=headers).json()
    visa_rate = float(response['fxRateWithAdditionalFee']) * 100
    return visa_rate


def get_mastercard():
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
        'referer': 'https://www.mastercard.us/en-us/personal/get-support/convert-currency.html',
        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    }

    params = {
        'fxDate': '0000-00-00',
        'transCurr': 'JPY',
        'crdhldBillCurr': 'MOP',
        'bankFee': '00',
        'transAmt': '100',
    }

    response = requests.get(
        'https://www.mastercard.us/settlement/currencyrate/conversion-rate',
        params=params,
        headers=headers,
    ).json()
    mastercard_rate = response['data']['conversionRate'] * 100
    return mastercard_rate


def get_hsbc():
    params = {
        'locale': 'zh_HK',
    }
    response = requests.get(
        'https://rbwm-api.hsbc.com.hk/digital-pws-tools-investments-eapi-prod-proxy/v1/investments/exchange-rate',
        params=params,
    ).json()
    for i in response['detailRates']:
        if i['ccy'] == 'JPY':
            return float(i['ttSelRt']) * 1.0315 * 100


def get_text():
    rates = {}
    try:
        rates['bnu'] = get_bnu()
    except:
        pass
    try:
        rates['boc'], rates['boc TT withdraw (+MOP5 every 10,000yen)'] = get_boc()
    except:
        pass
    try:
        rates['union'], rates['union ICBC (+MOP18 every 100,000yen)'] = get_union()
    except:
        print('銀聯系統匯率週一至週五每日更新，週六周日延用週五匯率。如無特殊情況，部分歐系貨幣匯率生效時間為北京時間16:30，其他貨幣匯率生效時間為北京時間11:00。')
    try:
        rates['visa'] = get_visa()
    except:
        pass
    try:
        rates['mastercard'] = get_mastercard()
    except:
        pass
    try:
        rates['hsbc'] = get_hsbc()
    except:
        pass

    # print("boc_rate/union_rate {:%}".format(boc_rate / union_rate - 1))
    # print("union_rate/visa_rate {:%}".format(union_rate / visa_rate - 1))
    # print("boc_rate/visa_rate {:%}".format(boc_rate / visa_rate - 1))

    # Sort the dictionary by values in ascending order
    sorted_dict = dict(sorted(rates.items(), key=lambda x: x[1]))

    text = ''
    text += ('# Exchange Rate Tracer') + '\n\n'
    text += f'> Update: {datetime.datetime.now()} (UTC)\n\n'
    table = []
    last = 0
    # Print the sorted dictionary
    for key, value in sorted_dict.items():
        diff = ''
        if (last != 0):
            diff = f'+{(value - last) * 1000:.4f}\n'
        last = value
        table.append([key, value, diff])

    if GITHUB_EVENT_ACTION =='schedule':
        with open('log.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.datetime.now(),
                             rates['visa'],
                             rates['mastercard'],
                             rates['union'],
                             rates['bnu'],
                             rates['boc'],
                             rates['hsbc']
                             ])

    head = ["Name", "Rate", "Diff per 100,000 yen"]
    return text + tabulate(table, headers=head,
                           tablefmt="github") +\
'''

> 銀聯系統匯率週一至週五每日更新，週六周日延用週五匯率。如無特殊情況，部分歐系貨幣匯率生效時間為北京時間16:30，其他貨幣匯率生效時間為北京時間11:00。

> BNU下班時間匯率較差。
'''


print(get_text())
