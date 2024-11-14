import asyncio
import logging
import os
import string
import time
from datetime import datetime, timedelta

import cv2
import numpy as np
import requests
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select



from tensorflow.keras.models import load_model

load_dotenv()

dp = Dispatcher()
chats_id = os.environ.get('CHAT_ID')
mode = os.environ.get('MODE')

symbols = string.ascii_uppercase + "0123456789"
num_symbols = len(symbols)
main_id = os.environ.get('MAIN_ID')

lots_list = []

model = load_model('models/model_v0.0.3.keras')

async def get_predict(url, num):
    pred = predict(get_img(url), model)
    dp['data'][f'func{num}']['captcha'] = pred


@dp.message()
async def get_captcha(message: Message) -> None:
    try:
        mes = message.text.split()
        dp['data'][f'func{mes[0]}']['captcha'] = mes[1]
        await message.answer(f"Принято")
        logging.info(f'ввел капчу {message.chat.username}')
    except Exception as e:
        logging.error(f'Неправильная капча {e}, {message.text, message.chat.username}')
        await message.answer(f"Неправильный формат, отправь еще раз")


async def send_tg_message(img_url, type, n, id) -> None:
    try:
        bot = dp.get('bot')
        if type == 'alarm':
            await bot.send_message(main_id, text=f'СРОЧНО{str(img_url)}')
        if id == 'other':
            id_num = min(dp['data']['chats'].values())
            id_ca = [id_c for id_c, value in dp['data']['chats'].items() if value == id_num][0]
            dp['data']['chats'][id_ca] += 1
            logging.info(f'Отправил {img_url} на {id_ca}')
            await bot.send_photo(id_ca, img_url, caption=f'фото №{n}, предсказано {dp['data'][f'func{n}']['captcha']}')
        else:
            await bot.send_photo(id, img_url, caption=f'фото №{n}, предсказано {dp['data'][f'func{n}']['captcha']}')
        dp['data'][f'func{n}']['type'] = type
    except Exception as e:
        logging.error(f'Ошибка send_tg_message {e}, {type}')


def get_img(url):
    X = np.zeros((1, 64, 256, 1))
    img_data = requests.get(url).content
    np_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_GRAYSCALE)
    img_cropped = img[:, 10:-10]
    img = cv2.resize(img_cropped, (256, 64))
    _, img = cv2.threshold(img, 211, 255, cv2.THRESH_BINARY_INV)
    img = img / 255.0
    img = np.reshape(img, (64, 256, 1))
    # X[0] = img
    return np.array(img)


def predict(img, model):
    symbols = string.ascii_uppercase + "0123456789"
    res = np.array(model.predict(img[np.newaxis, :, :, np.newaxis]))
    ans = np.reshape(res, (6, 36))
    l_ind = []
    # probs = []
    for a in ans:
        l_ind.append(np.argmax(a))
        # probs.append(np.max(a))

    capt = ''
    for l in l_ind:
        capt += symbols[l]
    return capt  # , sum(probs) / 6


async def captcha_loop(img, type, n):
    await send_tg_message(img, type, n, main_id)
    # i = 0
    # while True:
    #     if not dp['data'][f'func{n}']['captcha'] or dp['data'][f'func{n}']['predicted']:
    #         i += 1
    #         if i == 1800:
    #             i = 0
    #         await asyncio.sleep(1)
    #     else:
    #         break


async def auth(login, password, num, driver):
    driver.get("https://www.heroeswm.ru/")
    # but = driver.find_element(By.XPATH, '//*[@id="rXOa8"]/div/label/input')
    # but.click()
    while True:
        try:
            element = driver.find_element(By.XPATH, "//*[@title='Логин в игре']")
            break
        except:
            pass
    element.clear()
    element.send_keys(login)
    element = driver.find_element(By.XPATH, "//*[@title='Пароль в игре']")
    element.clear()
    element.send_keys(password)

    element.send_keys(Keys.RETURN)

    if driver.current_url == "https://www.heroeswm.ru/login.php":
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if 'Слишком много неудачных попыток, попробуйте позже.' in page_text:
            await asyncio.sleep(1800)
            await auth(login, password, num, driver)
            return
        img_url = driver.find_element(By.XPATH,
                                      "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody"
                                      "/tr[4]/td/table/tbody/tr/td[1]/img").get_attribute("src")
        img_data = requests.get(img_url).content
        await get_predict(img_url, num)

        element = driver.find_element(By.XPATH,
                                      "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody/tr["
                                      "1]/td[2]/input")
        element.clear()
        element.send_keys(login)
        element = driver.find_element(By.XPATH,
                                      "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody/tr["
                                      "2]/td[2]/input")
        element.clear()
        element.send_keys(password)
        element = driver.find_element(By.XPATH, '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table'
                                                '/tbody/tr[4]/td/table/tbody/tr/td[2]/input')
        element.clear()
        element.send_keys(dp['data'][f'func{num}']['captcha'])
        with open(f'photo/{dp['data'][f'func{num}']['captcha']}.jpg', 'wb') as handler:
            handler.write(img_data)
            logging.info(f'Сохранена капча {dp['data'][f'func{num}']['captcha']}.jpg, {img_data}')
        dp['data'][f'func{num}'] = {
            'predicted': False,
            'type': '',
            'captcha': ''
        }
        element.send_keys(Keys.RETURN)


def run_async_in_loop(loop, coro):
    asyncio.ensure_future(coro, loop=loop)


def start_buyer(driver, func, *args, **kwargs):
    url = kwargs['url']

    driver.get(url)
    page_text = driver.find_element(By.TAG_NAME, "body").text

    if 'Защитники предприятия не справились! Объект разрушен до' in page_text:
        target_time_str = page_text[
                          page_text.find('Объект разрушен до ') + 19:page_text.find('Объект разрушен до ') + 24]
    else:
        target_time_str = page_text[page_text.find('Окончание смены: ') + 17:page_text.find('Окончание смены: ') + 22]

    loop = asyncio.get_running_loop()

    now = datetime.now()
    if type(target_time_str) == int:
        target_time = now + timedelta(seconds=int(target_time_str))
    elif type(target_time_str) == str:
        try:
            target_time = datetime.strptime(target_time_str, "%H:%M").replace(year=now.year, month=now.month,
                                                                              day=now.day)
        except ValueError:
            time.sleep(2)
            start_buyer(driver, func, *args, **kwargs)
            return
    else:
        target_time = target_time_str

    if target_time < now:
        target_time += timedelta(days=1)

    delay = (target_time - datetime.now()).total_seconds() - 120

    # delay = 30
    if delay > 0:
        print(f"Таргет {target_time} секунд.")

        loop.call_at(loop.time() + delay, run_async_in_loop, loop, func(driver, *args, **kwargs))


async def action(driver, *args, **kwargs):
    try:
        url = kwargs['url']
        logging.info(f'Запуск актион{url}')
        driver.get(url)
        element = driver.find_element(By.XPATH,
                                      '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td[1]/a[1]')
        element.click()
        element = driver.find_element(By.XPATH,
                                      '//*[@id="dbut0"]')
        try:
            element.click()
        except ElementNotInteractableException:
            pass
        while True:
            element = driver.find_element(By.XPATH, '//*[@id="set_mobile_max_width"]/div[1]')
            if 'Перемещение' in element.text:
                time.sleep(1)
            else:
                break

        driver.get(url)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if 'Защитники предприятия не справились! Объект разрушен до' in page_text:
            logging.info(f'Защитники предприятия не справились! Объект разрушен {url}')
            start_buyer(driver, action, *args, **kwargs)
            return
        logging.info(f'Начало скупки{url}')
        for i in range(500):
            try:
                driver.get(url)
                driver.find_element(By.XPATH, '//*[@id="buy_res_btn"]').click()
                break
            except Exception:
                pass
        logging.info(f'Конец скупки{url}')
        start_buyer(driver, action, *args, **kwargs)
    except Exception as e:
        logging.info(f'Конец скупки ошибка{url,e}')
        start_buyer(driver, action, *args, **kwargs)


async def second_jober(driver, *args, **kwargs):
    login = kwargs['login']
    num = kwargs['num']
    flag = kwargs['flag']
    url = kwargs['url']
    n = 0
    logging.info(f'Запуск jober{url}')
    driver.get(url)
    element = driver.find_element(By.XPATH,
                                  '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td[1]/a[1]')
    element.click()
    element = driver.find_element(By.XPATH,
                                  '//*[@id="dbut0"]')
    try:
        element.click()
    except ElementNotInteractableException:
        pass
    while True:
        element = driver.find_element(By.XPATH, '//*[@id="set_mobile_max_width"]/div[1]')
        if 'Перемещение' in element.text:
            time.sleep(1)
        else:
            break

    driver.get(url)
    page_text = driver.find_element(By.TAG_NAME, "body").text
    if 'Защитники предприятия не справились! Объект разрушен до' in page_text:
        logging.info(f'Защитники предприятия не справились! Объект разрушен {url}')
        start_buyer(driver, second_jober, *args, **kwargs)
        return
    for i in range(444):
        page_text = driver.find_element(By.TAG_NAME, "body").text
        driver.get(url)
        if ('Вы уже устроены.' in page_text or 'Прошло меньше часа с последнего устройства на работу. Ждите.' in page_text
                or 'Нет рабочих мест.' in page_text):
            continue
        elif 'Поставьте галочку в квадратике "Я не робот" и нажмите кнопку "Работать' in page_text:
            break


        try:
            button = driver.find_element(By.XPATH, '//*[@id="wbtn"]')
            try:
                capt_element = driver.find_element(By.XPATH, '//*[@id="getjob_form"]/img[1]')
            except NoSuchElementException:
                button.click()
                logging.info(f'Выполнено {num, login}')
                break
            else:
                img_url = capt_element.get_attribute("src")
                img_data = requests.get(img_url).content
                await get_predict(img_url, num)
                logging.info(f'Предсказано {dp['data'][f'func{num}']['captcha']}')

                input_s = driver.find_element(By.CSS_SELECTOR, '#code')
                input_s.clear()
                input_s.click()
                for i in range(6):
                    input_s.send_keys(dp['data'][f'func{num}']['captcha'][i])
                input_s.send_keys(Keys.RETURN)
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                except Exception as e:
                    logging.error(
                        f'body не найден после find_element(By.TAG_NAME, "body") {e, login, num}')
                    break
                if 'Вы устроены на работу!' in page_text:
                    logging.info(f'Выполнено {num, login}')
                    with open(f'photo/{dp['data'][f'func{num}']['captcha']}.jpg', 'wb') as handler:
                        handler.write(img_data)
                        logging.info(
                            f'Сохранена капча {dp['data'][f'func{num}']['captcha']}.jpg, {num, login, img_data}')
                    dp['data'][f'func{num}'] = {
                        'type': '',
                        'captcha': ''
                    }
                    break
                elif 'Введён неправильный код.' in page_text:
                    logging.info(f'Неверная капча {num, login}')
                    break
                else:
                    logging.info(f'Неизвестное состояние объекта {page_text, num, login}')
                    break
        except Exception as e:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if ('Объект переполнен артефактами.' in page_text or 'Нет рабочих мест.' in page_text or
                    'На объекте недостаточно золота.' in page_text or 'Защитники предприятия не справились!' in page_text):
                logging.info(
                    'переполнен или нет мест или недостаточно золота или Защитники предприятия не справились')
                break
            elif 'Слишком высокий штраф трудоголика - вы не можете устраиваться на производственные предприятия. Попробуйте устроиться на добычу или обработку, или победите в битве.' in page_text:
                logging.info(f'Слишком высокий штраф трудоголика {num, login}')
                break
            logging.info(f'Неизвестная ошибка в конце {e, login, num, page_text}')
            break

    logging.info(f'Конец jober{url}')
    start_buyer(driver, second_jober, *args, **kwargs)


def lots_parser(driver):
    new_lots_list = []
    driver.get('https://www.heroeswm.ru/auction.php')
    rows = driver.find_element(By.XPATH,
                               '/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table').find_elements(
        By.TAG_NAME, "tr")

    for i, row in enumerate(rows):
        if i <= 3:
            continue
        try:
            lot_name_full_text = driver.find_elements(By.XPATH,
                                                      f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{i}]/td[1]/table/tbody/tr/td[2]')[
                0].text
            lot_name = lot_name_full_text[lot_name_full_text.find(' - ') + 3:lot_name_full_text.find(' [i]')]
            try:
                count = driver.find_element(By.XPATH,
                                            f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{i}]/td[1]/table/tbody/tr/td[2]/b[2]').text
            except NoSuchElementException:
                count = 1

            price_text = driver.find_element(By.XPATH,
                                             f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{i}]/td[3]/table/tbody/tr').text

            full_price, value_price = price_text.split('\n ')[0].replace('.', ''), price_text.split('\n ')[1].replace(
                '(', '').replace(')', '')
            new_lots_list.append(
                {'name': lot_name,
                 'count': count,
                 'full_price': full_price,
                 'value_price': value_price
                 })
        except IndexError:
            break
    return new_lots_list


goods = {
    # 'Лук рассвета': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=weapon&sort=0&art_type=bow17',
    #     'min_price': 10250,
    #     'max_price': 11000,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
     'Лук полуночи': {
         'link': 'https://www.heroeswm.ru/auction.php?cat=weapon&art_type=bow14',
         'min_price': 10600,
         'max_price': 11100,
         'min_lots_price': 0,
         'last_slot': False,
         'last_slot_name': ''
     },
    # 'Меч возрождения': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=weapon&art_type=firsword15',
    #     'min_price': 18400,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    'Рубиновый меч': {
        'link': 'https://www.heroeswm.ru/auction.php?cat=weapon&art_type=mm_sword',
        'min_price': 17700,
        'max_price': 18700,
        'min_lots_price': 0,
        'last_slot': False,
        'last_slot_name': ''
    },
    # 'Доспех пламени': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=cuirass&art_type=armor15',
    #     'min_price': 9400,
    #     'max_price': 9700,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'Гладий предвестия': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=weapon&art_type=sword18',
    #     'min_price': 17914,
    #     'max_price': 18200,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'огненный кристалл': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=fire_crystal',
    #     'min_price': 2900,
    #     'max_price': 4000,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'осколок метеорита': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=meteorit',
    #     'min_price': 4100,
    #     'max_price': 4500,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'ядовитый гриб': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=badgrib',
    #     'min_price': 160,
    #     'max_price': 200,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'цветок ведьм': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=witch_flower',
    #     'min_price': 160,
    #     'max_price': 250,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'цветок ветров': {
    #         'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=wind_flower',
    #         'min_price': 6600,
    #         'max_price': 7000,
    #         'min_lots_price': 0,
    #         'last_slot': False,
    #         'last_slot_name': ''
    #     },
    # 'ледяной кристалл': {
    #     'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=ice_crystal',
    #     'min_price': 2900,
    #     'max_price': 3100,
    #     'min_lots_price': 0,
    #     'last_slot': False,
    #     'last_slot_name': ''
    # },
    # 'абразив': {
    #         'link': 'https://www.heroeswm.ru/auction.php?cat=elements&sort=0&art_type=abrasive',
    #         'min_price': 3100,
    #         'max_price': 3300,
    #         'min_lots_price': 0,
    #         'last_slot': False,
    #         'last_slot_name': ''
    #     },
}


async def seller(driver, *args, **kwargs):
    loop = asyncio.get_running_loop()
    try:
        global lots_list
        flag = kwargs.get('flag', False)

        if flag:
            lots_list = lots_parser(driver)
        new_lots_list = lots_parser(driver)
        if lots_list != new_lots_list:
            pass

        goods_names = list(goods.keys())
        for i in goods_names:
            driver.get(goods[i]['link'])
            a = 3
            while True:
                try:
                    red = driver.find_element(By.XPATH,
                                              f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{a}]/td[1]/table/tbody/tr/td[2]/font[1]/b').text
                    a += 1
                except NoSuchElementException:
                    break
            price = driver.find_element(By.XPATH,
                                        f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{a}]/td[3]/table/tbody/tr').text.split(
                '\n')[0].replace(',', '')
            last_lot = driver.find_element(By.XPATH, f'/html/body/center/table/tbody/tr/td/table/tbody/tr[2]/td[2]/table/tbody/tr[{a}]/td[5]/form/a/b').text
            goods[i]['min_lots_price'] = int(price)
            if goods[i]['min_lots_price'] > goods[i]['max_price']:
                goods[i]['min_lots_price'] = goods[i]['max_price']
            goods[i]['last_slot_name'] = last_lot
            goods[i]['last_slot'] = last_lot == 'ГоджоСатору'

        driver.get('https://www.heroeswm.ru/auction_new_lot.php')

        select_element = driver.find_element(By.XPATH, '//*[@id="sel"]')

        options = Select(select_element).options

        cell_flag = False
        # Пройтись по всем опциям и вывести их значения
        for option in options:
            text = option.text

            for i in goods_names:
                if i in text:
                    if goods[i]['min_lots_price'] < goods[i]['min_price'] or goods[i]['last_slot']:
                        # print(goods[i]['min_lots_price'], goods[i]['min_price'])
                        # print(goods[i]['min_lots_price'] < goods[i]['min_price'], goods[i]['last_slot'])
                        continue
                    option.click()
                    count_input = driver.find_element(By.XPATH, '//*[@id="anl_count"]')
                    count_input.clear()
                    if '3' in text or '4' in text:
                        count_input.send_keys(2)
                    elif '5' in text or '6' in text:
                        count_input.send_keys(3)
                    else:
                        count_input.send_keys(1)

                    price_input = driver.find_element(By.XPATH, '//*[@id="anl_price"]')
                    price_input.clear()
                    price_input.send_keys(goods[i]['min_lots_price']-1)

                    button = driver.find_element(By.XPATH, '//*[@id="first_submit_button"]')
                    button.click()
                    time.sleep(3)
                    button = driver.find_element(By.XPATH, '//*[@id="set_mobile_max_width"]/div[2]/form/table/tbody/tr/td[1]/input')
                    button.click()
                    button = driver.find_element(By.XPATH, '/html/body/div[12]/div[7]/div/button')
                    button.click()
                    cell_flag = True
                    break
            if cell_flag:
                break
        logging.info('вызов seller')
        loop.call_at(loop.time() + 200, run_async_in_loop, loop, seller(driver))
        return
    except Exception as e:
        logging.error(f'ошибка seller {e}')
        loop.call_at(loop.time() + 200, run_async_in_loop, loop, seller(driver))


async def game_session(login, password, num, flag=''):
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument("--headless")
    options.add_argument('--disable-gpu')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)



    await auth(login, password, num, driver)

    link_list = [
        # 'https://www.heroeswm.ru/object-info.php?id=309',
        # 'https://www.heroeswm.ru/object-info.php?id=188',
        # 'https://www.heroeswm.ru/object-info.php?id=298',
        # 'https://www.heroeswm.ru/object-info.php?id=160',

        'https://www.heroeswm.ru/object-info.php?id=187',
        'https://www.heroeswm.ru/object-info.php?id=189',
        # 'https://www.heroeswm.ru/object-info.php?id=297'

    ]
    start_buyer(driver, second_jober, num=0, flag='diamonds', login=os.environ.get(f'LOGIN{0}'),
                 url='https://www.heroeswm.ru/object-info.php?id=165')
    for i in link_list:
        start_buyer(driver, action, url=i)
    await seller(driver, flag=True)


async def main():
    bot = Bot(token=os.environ.get('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp['bot'] = bot
    dp.bot = bot
    dp['data'] = dict()
    funcs = []
    dp['data']['chats'] = dict()
    for i in chats_id.split():
        dp['data']['chats'][str(i)] = 0
    for i in range(int(mode)):
        dp['data'][f'func{i}'] = {
            'predicted': False,
            'type': '',
            'captcha': ''
        }
        funcs.append(game_session(os.environ.get(f'LOGIN{i}'), os.environ.get(f'PASSWORD{i}'), i, 'diamonds'))
    await asyncio.gather(*funcs, dp.start_polling(bot))


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='app.log',
        filemode='a'
    )
    logging.getLogger('urllib3').setLevel('CRITICAL')
    logging.getLogger('aiogram.event').setLevel('CRITICAL')
    asyncio.run(main())
