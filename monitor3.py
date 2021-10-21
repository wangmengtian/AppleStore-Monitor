# -*- coding: UTF-8 –*-
"""
@Author: LennonChin
@Contact: i@coderap.com
@Date: 2021-10-19
"""

import sys
import os
import random
import datetime
import requests
import json
import time
import hmac
import hashlib
import base64
import traceback
from threading import Thread
import urllib.parse


class Utils:

    @staticmethod
    def time_title(message):
        return "[{}] {}".format(datetime.datetime.now().strftime('%H:%M:%S'), message)

    @staticmethod
    def log(message):
        print(Utils.time_title(message))

    @staticmethod
    def send_message(notification_configs, message, **kwargs):
        if len(message) == 0:
            return

        # DingTalk message
        Utils.send_dingtalk_message(notification_configs["dingtalk"], message, **kwargs)

        # Telegram message
        Utils.send_telegram_message(notification_configs["telegram"], message, **kwargs)

    @staticmethod
    def send_dingtalk_message(dingtalk_configs, message, **kwargs):
        if len(dingtalk_configs["access_token"]) == 0 or len(dingtalk_configs["secret_key"]) == 0:
            return

        timestamp = str(round(time.time() * 1000))
        secret_enc = dingtalk_configs["secret_key"].encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, dingtalk_configs["secret_key"])
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        headers = {
            'Content-Type': 'application/json'
        }

        params = {
            "access_token": dingtalk_configs["access_token"],
            "timestamp": timestamp,
            "sign": sign
        }

        content = {
            "msgtype": "text" if "message_type" not in kwargs else kwargs["message_type"],
            "text": {
                "content": message
            },
            "at": {
                "atMobiles":[
                    "13141327620",
                    "15811566905"
                ],
            }
        }

        response = requests.post("https://oapi.dingtalk.com/robot/send", headers=headers, params=params, json=content)
        print(response.json())
        Utils.log("Dingtalk发送消息状态码：{}".format(response.status_code))

    @staticmethod
    def send_telegram_message(telegram_configs, message, **kwargs):
        if len(telegram_configs["bot_token"]) == 0 or len(telegram_configs["chat_id"]) == 0:
            return

        headers = {
            'Content-Type': 'application/json'
        }

        proxies = {
            "https": telegram_configs["http_proxy"],
        }

        content = {
            "chat_id": telegram_configs["chat_id"],
            "text": message
        }

        url = "https://api.telegram.org/bot{}/sendMessage".format(telegram_configs["bot_token"])
        response = requests.post(url, headers=headers, proxies=proxies, json=content)
        Utils.log("Telegram发送消息状态码：{}".format(response.status_code))


class AppleStoreMonitor:
    headers = {
        'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'Referer': 'https://www.apple.com.cn/store',
        'DNT': '1',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'sec-ch-ua-platform': '"macOS"',
    }

    def __init__(self):
        self.count = 1
        self.err_count = 0

    @staticmethod
    def config():
        """
        进行各类配置操作
        """
        products = json.load(open('products.json', encoding='utf-8'))

        configs = {
            "selected_products": {},
            "selected_area": "",
            "notification_configs": {
                "dingtalk": {},
                "telegram": {}
            },
            "scan_interval": 30
        }
        while True:
            # chose product type
            print('--------------------')
            for index, item in enumerate(products):
                print('[{}] {}'.format(index, item))
            product_type = list(products)[int(input('选择要监控的产品：'))]

            # chose product classification
            print('--------------------')
            for index, (key, value) in enumerate(products[product_type].items()):
                print('[{}] {}'.format(index, key))
            product_classification = list(products[product_type])[int(input('选择要监控的产品子类：'))]

            # chose product classification
            print('--------------------')
            for index, (key, value) in enumerate(products[product_type][product_classification].items()):
                print('[{}] {}'.format(index, value))
            product_model = list(products[product_type][product_classification])[int(input('选择要监控的产品型号：'))]

            configs["selected_products"][product_model] = (
                product_classification, products[product_type][product_classification][product_model])

            print('--------------------')
            if len(input('是否添加更多产品[Enter继续添加，非Enter键退出]：')) != 0:
                break

        # config area
        print('选择计划预约的地址：')
        url_param = ['state', 'city', 'district']
        choice_params = {}
        param_dict = {}
        for step, param in enumerate(url_param):
            print('请稍后...{}/{}'.format(step + 1, len(url_param)))
            response = requests.get("https://www.apple.com.cn/shop/address-lookup", headers=AppleStoreMonitor.headers,
                                    params=choice_params)
            result_param = json.loads(response.text)['body'][param]
            if type(result_param) is dict:
                result_data = result_param['data']
                print('--------------------')
                for index, item in enumerate(result_data):
                    print('[{}] {}'.format(index, item['value']))
                input_index = int(input('请选择地区序号：'))
                choice_result = result_data[input_index]['value']
                param_dict[param] = choice_result
                choice_params[param] = param_dict[param]
            else:
                choice_params[param] = result_param

        print('正在加载网络资源...')
        response = requests.get("https://www.apple.com.cn/shop/address-lookup", headers=AppleStoreMonitor.headers,
                                params=choice_params)
        selected_area = json.loads(response.text)['body']['provinceCityDistrict']
        configs["selected_area"] = selected_area
        print("选择的计划预约的地址是：{}".format(selected_area))

        print('--------------------')
        # config notification configurations
        notification_configs = configs["notification_configs"]

        # config dingtalk notification
        dingtalk_access_token = input('输入钉钉机器人Access Token[如不配置直接回车即可]：')
        dingtalk_secret_key = input('输入钉钉机器人Secret Key[如不配置直接回车即可]：')

        # write dingtalk configs
        notification_configs["dingtalk"]["access_token"] = dingtalk_access_token
        notification_configs["dingtalk"]["secret_key"] = dingtalk_secret_key

        # config telegram notification
        print('--------------------')
        telegram_bot_token = input('输入Telegram机器人Token[如不配置直接回车即可]：')
        telegram_chat_id = input('输入Telegram机器人Chat ID[如不配置直接回车即可]：')
        telegram_http_proxy = input('输入Telegram HTTP代理地址[如不配置直接回车即可]：')

        # write telegram configs
        notification_configs["telegram"]["bot_token"] = telegram_bot_token
        notification_configs["telegram"]["chat_id"] = telegram_chat_id
        notification_configs["telegram"]["http_proxy"] = telegram_http_proxy

        # 输入扫描间隔时间
        print('--------------------')
        scan_interval = int(input('输入扫描间隔时间[以秒为单位，默认为30秒，如不配置直接回车即可]：') or 30)
        configs["scan_interval"] = scan_interval

        with open('apple_store_monitor_configs.json', 'w') as file:
            json.dump(configs, file, indent=2)
            print('--------------------')
            print("扫描配置已生成，并已写入到{}文件中\n请使用 python {} start 命令启动监控".format(file.name, os.path.abspath(__file__)))

    def start(self, comb_config_no=None):
        """
        开始监控
        """
        configs = json.load(open('apple_store_monitor_configs_comb.json', encoding='utf-8'))
        selected_products = configs["selected_products"]
        selected_area = configs["selected_area"]
        notification_configs = configs["notification_configs"]
        scan_interval = configs["scan_interval"]
        option_config_name = "selected_product_with_options%d" % int(comb_config_no)
        selected_product_with_options = configs[option_config_name]

        # 上次整点通知时间
        last_exactly_time = -1
        while True:
            available_list = []
            tm_hour = time.localtime(time.time()).tm_hour
            try:
                # ----------------- 扫描其他组合 ----------------
                Utils.log('-------------------- 第{}次扫描 开始扫描组合 --------------------'.format(self.count))
                params_with_option = {
                    "location": selected_area,
                    "mt": "regular"
                }
                for product_code, options_map in selected_product_with_options.items():
                    params_with_option["parts.0"] = product_code
                    for option_code, product_name in options_map.items():
                        time.sleep(random.randint(0, 2))
                        Utils.log('-------------------- 第{}次扫描 {} --------------------'.format(self.count, product_name))
                        params_with_option["option.0"] = option_code
                        params_with_option["_"] = int(time.time() * 1000)
                        response = requests.get("https://www.apple.com.cn/shop/fulfillment-messages",
                                                headers=AppleStoreMonitor.headers,
                                                params=params_with_option)
                        print(response.url)
                        try:
                            json_result = json.loads(response.text)
                        except:
                            print(response.text)
                            raise
                        stores = json_result['body']['content']['pickupMessage']['stores']
                        message = ''
                        for item in stores:
                            store_name = item['storeName']
                            if store_name in ['大连恒隆广场', '百年城', '济南恒隆广场', '青岛万象城']:
                                continue
                            # print("直营店： {}".format(store_name))
                            for product_code in item['partsAvailability']:
                                pickup_search_quote = item['partsAvailability'][product_code]['pickupSearchQuote']
                                pickup_display = item['partsAvailability'][product_code]['pickupDisplay']
                                # store_pickup_product_title = item['partsAvailability'][product_code]['storePickupProductTitle']
                                message += '{}-{}|'.format(store_name, pickup_search_quote)
                                if pickup_search_quote == '今天可取货' or pickup_display != 'unavailable':
                                    available_list.append((store_name, product_code, product_name))
                        print(message)

                        if len(available_list) > 0:
                            messages = []
                            print("命中货源，请注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                            Utils.log("以下直营店预约可用：")
                            for item in available_list:
                                messages.append("【{}】 {}".format(item[0], item[2]))
                                print("【{}】{}".format(item[0], item[2]))
                            print("命中货源，请注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

                            Utils.send_message(notification_configs,
                                            Utils.time_title("第{}次扫描到直营店有货，信息如下：\n{}".format(self.count, "\n".join(messages))))

                # ---------------------------------------------

            except Exception as err:
                self.err_count += 1
                Utils.log(err)
                Utils.log(traceback.format_exc())
                # 6:00 ~ 23:00才发送异常消息
                if 6 <= tm_hour <= 23:
                    Utils.send_message(notification_configs,
                                   Utils.time_title("第{}次扫描出现异常：{}。错误次数 {}".format(self.count, repr(err), self.err_count)))
                time.sleep(60)
                if self.err_count > 3:
                    time.sleep(240)
                if self.err_count > 5:
                    time.sleep(300)
                if self.err_count > 7:
                    time.sleep(3000)
                if self.err_count > 10:
                    time.sleep(86400)

            if len(available_list) == 0:
                # interval = max(random.randint(int(scan_interval / 2), scan_interval * 2), 5)
                interval = random.uniform(5, 30)
                Utils.log('{}秒后进行第{}次尝试...'.format(interval, self.count+1))

                # 整点通知，用于阶段性检测应用是否正常
                if last_exactly_time != tm_hour and (6 <= tm_hour <= 23):
                    Utils.send_message(notification_configs,
                                       Utils.time_title("已扫描{}次，monitor2扫描程序运行正常".format(self.count)))
                    last_exactly_time = tm_hour
                time.sleep(interval)
            else:
                time.sleep(5)

            # 次数自增
            self.count += 1

class ScanOneOptionThread(Thread):

    def __init__(self, selected_area, product_code, product_name, option_code, count, notification_configs):
        Thread.__init__(self)
        self.product_code = product_code
        self.selected_area = selected_area
        self.product_name = product_name
        self.option_code = option_code
        self.count = count
        self.notification_configs = notification_configs

    def run(self) -> None:
        time.sleep(random.uniform(0, 50))
        Utils.log('-------------------- 第{}次扫描 {} --------------------'.format(self.count, self.product_name))
        params_with_option = {
            "location": self.selected_area,
            "mt": "regular",
            "parts.0": self.product_code
        }
        params_with_option["option.0"] = self.option_code
        params_with_option["_"] = int(time.time() * 1000)
        response = requests.get("https://www.apple.com.cn/shop/fulfillment-messages",
                                headers=AppleStoreMonitor.headers,
                                params=params_with_option)
        print(response.url)
        try:
            json_result = json.loads(response.text)
            stores = json_result['body']['content']['pickupMessage']['stores']
        except:
            print(response.text)
            raise
        available_list = []
        message = ''
        for item in stores:
            store_name = item['storeName']
            if store_name in ['大连恒隆广场', '百年城', '济南恒隆广场', '青岛万象城']:
                continue
            # print("直营店： {}".format(store_name))
            for product_code in item['partsAvailability']:
                pickup_search_quote = item['partsAvailability'][product_code]['pickupSearchQuote']
                pickup_display = item['partsAvailability'][product_code]['pickupDisplay']
                # store_pickup_product_title = item['partsAvailability'][product_code]['storePickupProductTitle']
                message += '[{}-{}]'.format(store_name, pickup_search_quote)
                if pickup_search_quote == '今天可取货' or pickup_display != 'unavailable':
                    available_list.append((store_name, product_code, self.product_name))
        print(message)

        if len(available_list) > 0:
            messages = []
            print("命中货源，请注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            Utils.log("以下直营店预约可用：")
            for item in available_list:
                messages.append("【{}】 {}".format(item[0], item[2]))
                print("【{}】{}".format(item[0], item[2]))
            print("命中货源，请注意 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            for _ in range(10):
                Utils.send_message(self.notification_configs,
                            Utils.time_title("第{}次扫描到直营店有货，信息如下：\n{}".format(self.count, "\n".join(messages))))
                time.sleep(1)


if __name__ == '__main__':
    args = sys.argv

    if len(args) != 2:
        print("""
        Usage: python {} <option>
        option can be:
        \tconfig: pre config of products or notification
        \tstart: start to monitor
        """.format(args[0]))
        exit(1)

    if args[1] == "config":
        AppleStoreMonitor.config()

    if args[1] == "start":
        AppleStoreMonitor().start()

    if args[1] == "start1":
        AppleStoreMonitor().start(1)
    if args[1] == "start2":
        AppleStoreMonitor().start(2)
    if args[1] == "start3":
        AppleStoreMonitor().start(3)