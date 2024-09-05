import asyncio
import logging
import os
import requests
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import string
from io import BytesIO
import cv2

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.enums import ParseMode
from tensorflow.keras.models import load_model

import requests
import numpy as np
import cv2

load_dotenv()

dp = Dispatcher()
chats_id = os.environ.get('CHAT_ID')
mode = os.environ.get('MODE')

symbols = string.ascii_uppercase + "0123456789"
num_symbols = len(symbols)
main_id = os.environ.get('MAIN_ID')


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


@dp.message()
async def get_captcha(message: Message) -> None:
    try:
        mes = message.text.split()
        dp['data'][f'func{mes[0]}']['captcha'] = mes[1]
        dp['data'][f'func{mes[0]}']['predicted'] = False
        await message.answer(f"Принято")
        logging.info(f'ввел капчу {message.chat.username}')
    except Exception as e:
        logging.error(f'Неправильная капча {e}, {message.text, message.chat.username}')
        await message.answer(f"Неправильный формат, отправь еще раз")


async def main():
    bot = Bot(token=os.environ.get('TOKEN'),
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
            'predicted': False,
            'type': '',
            'captcha': ''
        }
        funcs.append(messaging(os.environ.get(f'LOGIN{i}'), os.environ.get(f'PASSWORD{i}'), i))
    # await dp.start_polling(bot)
    await asyncio.gather(*funcs, dp.start_polling(bot))


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
    symbols = string.ascii_uppercase + "0123456789"  # All symbols captcha can contain
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


async def get_predict(url, num):
    model = load_model('models/model_v0.0.2.keras')
    pred = predict(get_img(url), model)
    dp['data'][f'func{num}']['captcha'] = pred
    dp['data'][f'func{num}']['predicted'] = True


async def captcha_loop(img, type, n):
    await send_tg_message(img, type, n, main_id)
    i = 0
    while True:
        if not dp['data'][f'func{n}']['captcha'] or dp['data'][f'func{n}']['predicted']:
            i += 1
            if i == 1800:
                i = 0
            await asyncio.sleep(1)
        else:
            break


async def auth(login, password, num, driver):
    driver.get("https://www.heroeswm.ru/")
    element = driver.find_element(By.XPATH, "//*[@title='Логин в игре']")
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
        capt_element = driver.find_element(By.XPATH,
                                           "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody"
                                           "/tr[4]/td/table/tbody/tr/td[1]/img")
        img_url = capt_element.get_attribute("src")
        img_data = requests.get(img_url).content
        if not dp['data'][f'func{num}']['predicted']:
            await get_predict(img_url, num)
            # dp['data'][f'func{num}']['captcha'] = '123123123'
            # dp['data'][f'func{num}']['predicted'] = True
        else:
            await captcha_loop(img_url, 'auth', num)

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


async def messaging(login, password, num):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)

    await auth(login, password, num, driver)

    cicle = 3

    while True:
        try:
            try:
                if not dp['data'][f'func{num}']['predicted']:
                    dp['data'][f'func{num}'] = {
                        'type': '',
                        'captcha': '',
                        'predicted': False
                    }
            except KeyError:
                dp['data'][f'func{num}'] = {
                    'predicted': False,
                    'type': '',
                    'captcha': ''
                }
                continue
            if cicle == 19:
                cicle = 3
                logging.info(f'Предприятий нет павуза {num, login, password}')
                await asyncio.sleep(600)
            driver.get("https://www.heroeswm.ru/map.php")
            await asyncio.sleep(1)
            element = driver.find_element(By.XPATH, "//*[@hint='Добыча']")
            element.click()
            await asyncio.sleep(1)
            content = driver.find_element(By.XPATH,
                                          f'//*[@id="hwm_map_objects_and_buttons"]/div[2]/div[2]/table/tbody/tr[{cicle}]')
            if '»»»' in content.text:
                button = driver.find_element(By.XPATH,
                                             f'//*[@id="hwm_map_objects_and_buttons"]/div[2]/div[2]/table/tbody/tr[{cicle}]/td[5]/a')
                button.click()
                await asyncio.sleep(3)
                page_text = driver.find_element(By.TAG_NAME, "body").text
            else:
                cicle += 1
                continue
        except Exception as e:
            try:
                if 'id="hwm_map_objects_and_buttons"]/div[2]/div[2]/table/tbody/tr' in e:
                    cicle = 3
                    logging.info(f'Предприятий нет павуза {num, login, password}')
                    await asyncio.sleep(600)
                    continue
                elif 'Добыча' in e.msg:
                    await auth(login, password, num, driver)
                    logging.info(f'Перезаход {num, login, password}')
                    continue
                logging.error(
                    f'body не найден после driver.get("https://www.heroeswm.ru/map.php") или пустой список предприятий {login, num, cicle, e.msg, password,}', )
                cicle = 3
                continue
            except Exception as e:
                logging.error(
                    f' {login, num, cicle, e, password}', )
        if 'Вы уже устроены.' in page_text or 'Прошло меньше часа с последнего устройства на работу. Ждите.' in page_text:
            logging.info(f'Уже устроен {num, login, password}')
            await asyncio.sleep(600)
            continue
        elif ('Объект переполнен артефактами.' in page_text or 'Нет рабочих мест.' in page_text or
              'На объекте недостаточно золота.' in page_text or 'Защитники предприятия не справились!' in page_text):
            logging.info('переполнен или нет мест или недостаточно золота или Защитники предприятия не справились')
            continue
        elif 'Слишком высокий штраф трудоголика - вы не можете устраиваться на производственные предприятия. Попробуйте устроиться на добычу или обработку, или победите в битве.' in page_text or 'Вам нужно победить в битве.' in page_text:
            logging.info(f'Слишком высокий штраф трудоголика {num, login, password}')
            await send_tg_message(f'Слишком высокий штраф трудоголика {login, password}', 'alarm', cicle, main_id)
            await asyncio.sleep(600)
            continue
        try:
            button = driver.find_element(By.XPATH, '//*[@id="wbtn"]')
            try:
                capt_element = driver.find_element(By.XPATH, '//*[@id="getjob_form"]/img[1]')
            except NoSuchElementException:
                button.click()
                logging.info(f'Выполнено {num, login, password}')
                await asyncio.sleep(3650)
            else:
                img_url = capt_element.get_attribute("src")
                img_data = requests.get(img_url).content
                if not dp['data'][f'func{num}']['predicted']:
                    await get_predict(img_url, num)
                    # dp['data'][f'func{num}']['captcha'] = 'qweqwe'
                    # dp['data'][f'func{num}']['predicted'] = True
                    logging.info(f'Предсказано {dp['data'][f'func{num}']['captcha']}')
                else:
                    await captcha_loop(img_url, 'auth', num)

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
                        f'body не найден после find_element(By.TAG_NAME, "body") {e, login, password, num, cicle}')
                    cicle += 1
                    continue
                if 'Вы устроены на работу!' in page_text:
                    logging.info(f'Выполнено {num, login, password}')
                    with open(f'photo/{dp['data'][f'func{num}']['captcha']}.jpg', 'wb') as handler:
                        handler.write(img_data)
                        logging.info(
                            f'Сохранена капча {dp['data'][f'func{num}']['captcha']}.jpg, {num, login, password, img_data}')
                    dp['data'][f'func{num}'] = {
                        'type': '',
                        'captcha': ''
                    }
                    await asyncio.sleep(3650)
                elif 'Введён неправильный код.' in page_text:
                    logging.info(f'Неверная капча {num, login, password}')
                    continue
                elif 'На объекте недостаточно золота.' in page_text:
                    logging.info(f'На объекте недостаточно золота. {num, login, password}')
                    continue
                elif 'Нет рабочих мест.' in page_text:
                    logging.info(f'Нет рабочих мест. {num, login, password}')
                    continue
                else:
                    logging.info(f'Неизвестное состояние объекта {page_text, num, login, password}')
        except Exception as e:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if ('Объект переполнен артефактами.' in page_text or 'Нет рабочих мест.' in page_text or
                    'На объекте недостаточно золота.' in page_text or 'Защитники предприятия не справились!' in page_text):
                logging.info('переполнен или нет мест или недостаточно золота или Защитники предприятия не справились')
                continue
            elif 'Слишком высокий штраф трудоголика - вы не можете устраиваться на производственные предприятия. Попробуйте устроиться на добычу или обработку, или победите в битве.' in page_text:
                logging.info(f'Слишком высокий штраф трудоголика {num, login, password}')
                await asyncio.sleep(600)
                continue
            logging.info(f'Неизвестная ошибка в конце {e, login, password, num, cicle, page_text}')
            try:
                await auth(login, password, num, driver)
            except Exception as e:
                pass
            cicle += 1
            continue
        cicle = 3

    driver.quit()


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
