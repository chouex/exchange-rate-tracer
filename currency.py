import csv
import datetime
import os
import time

import requests
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
import base64

from tabulate import tabulate
from bs4 import BeautifulSoup

GITHUB_EVENT_NAME = os.getenv('GITHUB_EVENT_NAME')
currencies = ['JPY', 'CNY']


def get_bnu():
    response = requests.get('https://online.bnu.com.mo/ebank/bnu/ExchangeRates?lv1ID=0&lv2ID=0&lang=C').text
    table_data = [[cell.text.strip() for cell in row("td")] for row in BeautifulSoup(response, 'html.parser')("tr")]
    for row in table_data:
        if row[0] in currencies:
            yield row[0], float(row[9 if row[0] != 'CNY' else 5]) * 100
    return
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
        if pair['ExchangeCurrency'] in currencies:
            boc_rate = pair['CSRate']
            boc_tt_rate = pair['TTSRate']
            yield pair['ExchangeCurrency'], (
                boc_rate if pair['ExchangeCurrency'] != 'CNY' else boc_tt_rate, boc_tt_rate + 0.050)


def get_union():
    response = requests.get(
        'https://www.unionpayintl.com/upload/jfimg/{}.json'.format(
            (datetime.datetime.now() + datetime.timedelta(
                days=0 if datetime.datetime.now().hour >= 11 else -1)).strftime(
                "%Y%m%d")), ).json()

    for pair in response['exchangeRateJson']:
        if pair['transCur'] in currencies and pair['baseCur'] == 'MOP':
            union_rate = pair['rateData'] * 100
            yield pair['transCur'], union_rate


def get_visa():
    for c in currencies:
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
            'toCurr': c,
        }

        response = requests.get('https://www.visa.com.hk/cmsapi/fx/rates', params=params, headers=headers).json()
        visa_rate = float(response['fxRateWithAdditionalFee']) * 100
        yield c, visa_rate


def get_mastercard():
    for c in currencies:
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
            'transCurr': c,
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
        yield c, mastercard_rate


def get_hsbc():
    params = {
        'locale': 'zh_HK',
    }
    response = requests.get(
        'https://rbwm-api.hsbc.com.hk/digital-pws-tools-investments-eapi-prod-proxy/v1/investments/exchange-rate',
        params=params,
    ).json()
    for i in response['detailRates']:
        if i['ccy'] in currencies:
            yield i['ccy'], float(i['ttSelRt']) * 1.0315 * 100


def get_soicheong():
    response = requests.get(
        'https://www.soicheong.com/index.php?g=Api&m=Exchange&a=getRate',
    ).json()
    for i in response['value']:
        if i['codenum'] == 'RMB': i['codenum'] = 'CNY'
        if i['codenum'] in currencies:
            yield i['codenum'], float(i['rate2']) * 1.0315 * 100


def get_jcb():
    day_delta = 0
    if datetime.datetime.now().weekday() == 5:
        day_delta = -1
    elif datetime.datetime.now().weekday() == 6:
        day_delta = -2
    elif datetime.datetime.now().hour < 10:
        day_delta = -1

    response = requests.get(
        'https://www.jcb.jp/rate/usd{}.html'.format(
            (datetime.datetime.now() + datetime.timedelta(
                days=day_delta)).strftime(
                "%m%d%Y")), )
    if response.status_code == 404:
        response = requests.get(
            'https://www.jcb.jp/rate/usd.html')
        href = BeautifulSoup(response.text, 'html.parser').select('li a')[0].attrs['href']
        response = requests.get(
            'https://www.jcb.jp'.format(href))

    response = response.text
    table_data = [[cell.text.strip() for cell in row("td")] for row in BeautifulSoup(response, 'html.parser')("tr")]
    for row in table_data:
        if row[-1] == 'MOP':
            MOP_SELL = float(row[4])
    for row in table_data:
        if row[-1] in currencies:
            BUY = float(row[2])
            yield row[-1], MOP_SELL / BUY * 100


def get_text():
    rates = {}

    rates['bnu'] = dict(get_bnu())

    try:
        rates['boc'] = dict(get_boc())
        # , rates['boc TT withdraw (+MOP5 every 10,000yen)']
    except:
        pass
    try:
        rates['union'] = dict(get_union())
        # , rates['union ICBC (+MOP18 every 100,000yen)']
    except:
        # rates['union'] = 999
        print('銀聯系統匯率週一至週五每日更新，週六周日延用週五匯率。如無特殊情況，部分歐系貨幣匯率生效時間為北京時間16:30，其他貨幣匯率生效時間為北京時間11:00。')
    try:
        rates['visa'] = dict(get_visa())
    except:
        pass

    rates['mastercard'] = dict(get_mastercard())
    rates['hsbc'] = dict(get_hsbc())
    rates['soicheong'] = dict(get_soicheong())
    rates['jcb'] = dict(get_jcb())

    # print("boc_rate/union_rate {:%}".format(boc_rate / union_rate - 1))
    # print("union_rate/visa_rate {:%}".format(union_rate / visa_rate - 1))
    # print("boc_rate/visa_rate {:%}".format(boc_rate / visa_rate - 1))
    text = ''
    text += ('# Exchange Rate Tracer') + '\n\n'
    text += f'> Update: {datetime.datetime.now()} (UTC)\n\n'
    for c in currencies:
        text += f'## {c}\n\n'
        # Sort the dictionary by values in ascending order
        names = {}
        for k, v in rates.items():
            if c not in v: continue
            if k == 'union':
                names[k] = v[c]
                if c == 'JPY':
                    names['union ICBC (+MOP18 every 100,000yen)'] = v[c] + 0.018
                if c == 'CNY':
                    names['union ICBC (+MOP18 every 10,000yuan)'] = v[c] + 0.18
            elif k == 'boc':
                names[k] = v[c][0]
                if c == 'JPY':
                    names['boc TT withdraw (+MOP5 every 10,000yen)'] = v[c][1]
            else:
                names[k] = v[c]
        sorted_dict = dict(sorted(names.items(), key=lambda x: x[1]))
        table = []
        last = 0
        # Print the sorted dictionary
        for key, value in sorted_dict.items():
            diff = ''
            if value != 999:
                if (last != 0):
                    diff = f'+{(value - last) * 1000:.4f} ({value / last - 1:.4%})\n'
                last = value

                table.append([key, f'{value:.5f}\t({1 / value * 10000:.4f})' if c == 'CNY' else value, diff])

        if GITHUB_EVENT_NAME == 'schedule':
            with open('logs/{0}.csv'.format(c), 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([datetime.datetime.now(),
                                 rates['visa'][c],
                                 rates['mastercard'][c],
                                 rates['union'][c],
                                 rates['bnu'][c],
                                 rates['boc'][c],
                                 rates['hsbc'][c],
                                 rates['jcb'][c]
                                 ])

        head = ["Name", "Rate", "Diff per 100,000 " + c]
        text += tabulate(table, headers=head,
                         tablefmt="github")
        text += f'\n\n'
    return text + """
> 銀聯系統匯率週一至週五每日更新，週六周日延用週五匯率。如無特殊情況，部分歐系貨幣匯率生效時間為北京時間16:30，其他貨幣匯率生效時間為北京時間11:00。

> BNU下班時間匯率較差。
"""


# while True:
#     print(get_text())
#     time.sleep(300)
print(get_text())
