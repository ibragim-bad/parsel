from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.proxy import Proxy, ProxyType
import logging
from joblib import Parallel, delayed
from proxybroker import Broker
import asyncio
import random
import json
from tqdm import tqdm

WEBDRIVER_PATH = 'webdrivers/chromedriver'
FIREFOX = 'webdrivers/geckodriver'
OUTFILE = 'parsed/paras.json'
URL = 'https://otvet.mail.ru/'
PROXY_NUM = 10
JOBS = 4
PROXY = ''



user_agent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36']


class Parser:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.update_ua()
        self.current_proxy = self.get_vaild_proxy()

    def update_ua(self):
        self.cur_ua = random.choice(user_agent_list)
        self.logger.info(f"UserAgent updated: {self.cur_ua}")

    def get_firefox(self, proxy):
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')

        proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpProxy': proxy,
            'ftpProxy': proxy,
            'sslProxy': proxy,
            'noProxy': ''
        })


        driver = webdriver.Firefox(executable_path='webdrivers/geckodriver', options=options, proxy=proxy)
        return driver
    #
    # def get_webdriver(self, proxy):
    #     options = webdriver.ChromeOptions()
    #     options.add_argument('--headless')
    #     options.add_argument('--no-sandbox')
    #     options.add_argument('--disable-dev-shm-usage')
    #
    #     caps = webdriver.DesiredCapabilities.CHROME
    #     caps['marionette'] = True
    #
    #     caps['proxy'] = {
    #         "proxyType": "MANUAL",
    #         "httpProxy": proxy,
    #         "ftpProxy": proxy,
    #         "sslProxy": proxy
    #     }
    #
    #     driver = webdriver.Chrome(WEBDRIVER_PATH, options=options)#, desired_capabilities=caps)
    #
    #     return driver

    def get_vaild_proxy(self):

        proxy = self.getProxies(PROXY_NUM)
        i = 0
        pr = ''
        while i < len(proxy):
            pr = proxy[i]
            self.logger.info(f'check {i} proxy: {pr}')
            driver = self.get_firefox(pr)
            driver.get("https://otvet.mail.ru/")
            sou = driver.page_source
            i += 1
            if len(sou) > 50:
                break
            pr = ''
        if pr == '':
            raise TimeoutError('Not find proxy!')
        return pr

    def update_proxy(self):
        self.current_proxy = self.get_vaild_proxy()
        self.logger.info(f"proxy updated to {self.current_proxy}")

    def getProxies(self, n):
        async def show(proxies):
            p = []
            while True:
                    proxy = await proxies.get()
                    if proxy is None: break
                    a = f"{proxy.host}:{proxy.port}"
                    p.append(a)
            return p

        proxies = asyncio.Queue()
        broker = Broker(proxies)
        tasks = asyncio.gather(broker.find(types=['HTTP', 'HTTPS'],
                                           countries=['CZ', 'DE', 'RU', 'FR', 'IT'],
                                           limit=n), show(proxies))
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(tasks)[1]

    def get_search_res(self, request):
        driver = self.get_firefox(self.current_proxy)
        '''можно ускорить поиск если создать пул воркеров и не пересоздавать каждый раз браузер'''
        driver.get(URL)

        '''
        тут проверка если заблочили, условие (какой-то элемент на странице обычно, что слишком много заросов с ip)
        если заблочили, меняешь ip на новый и перезагружаешь
        '''
        # if len(driver.page_source < 50):
        #     self.update_proxy()
        #     driver = self.get_firefox(self.current_proxy)
        #     driver.get(get_firefox)

        '''
        тут функционал selenium как находить элементы страницы
        '''
        search = driver.find_element_by_name('q')
        search.click()
        search.clear()
        search.send_keys(request)
        search.submit()
        timeout = 5
        samples = []
        for i in range(1, 6):
            '''
            тут функционал selenium как находить элементы страницы, на странице сайта через инструмент разработчик
            находишь нужный xpath
            '''
            xpath = f'//*[@id="ColumnCenter"]/div/div/div[3]/div/div[{i}]/a[2]'
       #     element = driver.find_element_by_xpath(xpath)

            driver.wait = WebDriverWait(driver, timeout)

            try:
                '''
                ждет пока загрузится нужный элемент'''
                element = driver.wait.until(
                    ec.presence_of_element_located(
                        (By.XPATH, xpath)
                        ))
            except:
                self.logger.info(f'error for {driver.current_url}')
                break
            samples.append(element.text)
        driver.close()
        return {request: samples}


def main():
    logger = logging.getLogger(__name__)
    tr = Parser()

    sents = list(range(12))

    paras = Parallel(n_jobs=JOBS)(delayed(tr.get_search_res)(chunk) for chunk in tqdm(sents))
    #paras = [tr.get_search_res(chunk) for chunk in tqdm(sents)]
    with open(OUTFILE, 'w') as out:
        json.dump(paras, out, indent=4, ensure_ascii=False)
    logger.info("Done.")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[
        # logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ], level=logging.INFO)
    main()
