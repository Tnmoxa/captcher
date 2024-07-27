import asyncio
import logging
import os
import sys
import threading
import requests
import time
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.enums import ParseMode

load_dotenv()

dp = Dispatcher()
chats_id = os.environ.get('CHAT_ID')
mode = os.environ.get('MODE')

main_id = os.environ.get('MAIN_ID')


async def send_tg_message(img_url, type, n, id) -> None:
    try:
        if id == 'other':
            id_num = min(dp['data']['chats'].values())
            id = [id for id, value in dp['data']['chats'].items() if value == id_num][0]
        bot = dp.get('bot')
        dp['data'][f'func{n}']['type'] = type
        print('Отправил на ', id)
        await bot.send_photo(id, img_url, caption=f'фото №{n}')
    except Exception as e:
        print('Ошибка send_tg_message', e)


@dp.message()
async def get_captcha(message: Message) -> None:
    try:
        mes = message.text.split()
        dp['data'][f'func{mes[0]}']['captcha'] = mes[1]
        await message.answer(f"Принято")
    except Exception as e:
        print('get_captcha_error', e, message.text)
        await message.answer(f"Неправильный формат, отправь еще раз")


async def main():
    bot = Bot(token='6791529955:AAF2sQa9AFmWnszcQ6q4VtX6hOYnAjvvkAA',
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp['bot'] = bot
    dp.bot = bot
    dp['data'] = dict()
    funcs = []
    dp['data']['chats'] = dict()
    for i in chats_id.split():
        dp['data']['chats'][str(i)] = 0
    for i in range(int(mode)):
        dp['data'][f'func{i}'] = {
            'type': '',
            'captcha': ''
        }
        funcs.append(messaging(os.environ.get(f'LOGIN{i}'), os.environ.get(f'PASSWORD{i}'), i))
    a = dp['data']
    await asyncio.gather(*funcs, dp.start_polling(bot))


async def captcha_loop(img, type, n):
    await send_tg_message(img, type, n, main_id)
    i = 0
    while True:
        if not dp['data'][f'func{n}']['captcha']:

            # i+=1
            # if i == 30:
            #     await send_tg_message(img, type, n, 'other')
            await asyncio.sleep(1)
        else:
            break


async def messaging(login, password, num):
    # a = (login, password, n)
    # print(login, password, n)
    # await asyncio.sleep(111111111)

    driver = webdriver.Chrome()
    driver.get("https://www.heroeswm.ru/")
    element = driver.find_element(By.XPATH, "//*[@title='Логин в игре']")
    element.clear()
    element.send_keys(login)
    element = driver.find_element(By.XPATH, "//*[@title='Пароль в игре']")
    element.clear()
    element.send_keys(password)

    element.send_keys(Keys.RETURN)

    if driver.current_url == "https://www.heroeswm.ru/login.php":
        capt_element = driver.find_element(By.XPATH,
                                           "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody"
                                           "/tr[4]/td/table/tbody/tr/td[1]/img")
        img_url = capt_element.get_attribute("src")
        img_data = requests.get(img_url).content
        await captcha_loop(img_url, 'auth', num)
        with open(f'photo/{dp['data'][f'func{num}']['captcha']}.jpg', 'wb') as handler:
            handler.write(img_data)

        element = driver.find_element(By.XPATH,
                                      "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody/tr[1]/td[2]/input")
        element.clear()
        element.send_keys(login)
        element = driver.find_element(By.XPATH,
                                      "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody/tr[2]/td[2]/input")
        element.clear()
        element.send_keys(password)
        element = driver.find_element(By.XPATH, '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table'
                                                '/tbody/tr[4]/td/table/tbody/tr/td[2]/input')
        element.clear()
        element.send_keys(dp['data'][f'func{num}']['captcha'])
        dp['data'][f'func{num}'] = {
            'type': '',
            'captcha': ''
        }
        element.send_keys(Keys.RETURN)

    n = 3
    # driver.get("https://www.heroeswm.ru/pers_settings.php")
    # element = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr/td/table/tbody/tr[6]/td[2]/input[3]')
    # element.click()
    # element = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr/td/table/tbody/tr[1]/td/input')
    # element.click()

    while True:
        try:
            driver.get("https://www.heroeswm.ru/map.php")
            element = driver.find_element(By.XPATH, "//*[@hint='Производство']")
            element.click()
            await asyncio.sleep(3)
            content = driver.find_element(By.XPATH,
                                          f'//*[@id="hwm_map_objects_and_buttons"]/div[2]/div[2]/table/tbody/tr[{n}]')
            if '»»»' in content.text:
                button = driver.find_element(By.XPATH,
                                             f'//*[@id="hwm_map_objects_and_buttons"]/div[2]/div[2]/table/tbody/tr[{n}]/td[5]/a')
                button.click()
                await asyncio.sleep(3)
            elif '»»' in content.text:
                n += 1
                continue
        except Exception as e:
            await asyncio.sleep(3600)
        try:
            capt_element = driver.find_element(By.XPATH, '//*[@id="getjob_form"]/img[1]')
            img_url = capt_element.get_attribute("src")
            img_data = requests.get(img_url).content
            await captcha_loop(img_url, 'auth', num)

            input_s = driver.find_element(By.CSS_SELECTOR, '#code')
            input_s.clear()
            input_s.click()
            for i in range(6):
                input_s.send_keys(dp['data'][f'func{num}']['captcha'][i])
            dp['data'][f'func{num}'] = {
                'type': '',
                'captcha': ''
            }
            input_s.send_keys(Keys.RETURN)
            try:
                input_s = driver.find_element(By.XPATH,
                                              '/html/body/center/table[2]/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td/b')
                if input_s.text == 'Вы устроены на работу!':
                    with open(f'photo/{dp['data'][f'func{num}']['captcha']}.jpg', 'wb') as handler:
                        handler.write(img_data)
                    print(f'Выполнено {login, password}', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                    await asyncio.sleep(3650)
            except Exception as e:
                print(e)
            try:
                input_s = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td/font/b')
                if input_s.text == 'Введён неправильный код.':
                    print(f'Неверная капча {login, password}', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                    continue
                else:
                    print(f'Неизвестная ошибка /html/body/center/table[2]/tbody/tr/td/table/tbody/tr/td/table['
                          f'1]/tbody/tr/td/font/b {login, password}', input_s.text, time.strftime("%Y-%m-%d %H:%M:%S",
                                                                                    time.localtime()))
                    await asyncio.sleep(3650)
                    continue
            except Exception as e:
                print(e)
            try:
                input_s = driver.find_element(By.XPATH,'/html/body/center/table[2]/tbody/tr/td/table/tbody/tr/td/font')
                if input_s.text != 'Вы уже устроены.' or input_s.text != 'Прошло меньше часа с последнего устройства на работу. Ждите.':
                    await asyncio.sleep(3650)
                elif input_s.text != 'Нет рабочих мест.':
                    continue
                else:
                    print(
                        f'Неизвестная ошибка /html/body/center/table[2]/tbody/tr/td/table/tbody/tr/td/table['
                        '1]/tbody/tr/td/font/b {login, password}', input_s.text, time.strftime("%Y-%m-%d %H:%M:%S",
                                                                                 time.localtime()))
                    await asyncio.sleep(3650)
                    continue
            except Exception as e:
                raise NoSuchElementException
        except NoSuchElementException:
            try:
                button = driver.find_element(By.XPATH, '//*[@id="wbtn"]')
                button.click()
                print(f'Выполнено {login, password}', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                await asyncio.sleep(3650)
            except NoSuchElementException:
                print(f'Уже устроен {login, password}', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                await asyncio.sleep(3650)
        except Exception as e:
            print(e, login, password, num, n)
            continue

        n = 3

    driver.quit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
