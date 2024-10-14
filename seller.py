import asyncio
import logging
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


res_list = ['Самоцветы', 'Руда', 'Сера', 'Древесина', 'Ртуть', 'Кристаллы']

a =['https://www.heroeswm.ru/object-info.php?id=339',
    'https://www.heroeswm.ru/object-info.php?id=190',
    'https://www.heroeswm.ru/object-info.php?id=176',
    'https://www.heroeswm.ru/object-info.php?id=207',
    'https://www.heroeswm.ru/object-info.php?id=276',
    'https://www.heroeswm.ru/object-info.php?id=177',
    'https://www.heroeswm.ru/object-info.php?id=206',
    'https://www.heroeswm.ru/object-info.php?id=187',
    'https://www.heroeswm.ru/object-info.php?id=208',
    'https://www.heroeswm.ru/object-info.php?id=255',
    'https://www.heroeswm.ru/object-info.php?id=188',
    'https://www.heroeswm.ru/object-info.php?id=297',
    'https://www.heroeswm.ru/object-info.php?id=318',
    'https://www.heroeswm.ru/object-info.php?id=189',
    'https://www.heroeswm.ru/object-info.php?id=360',
    ]

def run_async_in_loop(loop, coro):
    asyncio.ensure_future(coro, loop=loop)


async def seller(driver):
    cicle = 3

    n = 0

    for i in a:
        try:
            driver.get(i)
            await asyncio.sleep(3)
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception as e:
            if 'no such element:' in e.msg:
                logging.info('переход в цикл')
                break
                # asyncio.get_event_loop().run_forever()
            logging.error(
                f'Ошибка в первом трае {cicle, e}')
            cicle = 3
            continue

        if 'Свободных мест' in page_text:
            free_count = page_text[page_text.find('Свободных мест: ') + 16:page_text.find('\n\nПроизведено:')]
        else:
            free_count = 1


        tab = driver.find_element(By.XPATH, '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody').text
        f = False
        for res in res_list:
            if res in tab:
                f = True
                break

        try:
            fir = driver.find_element(By.XPATH, '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/form/table/tbody/tr[2]/td[3]/b/font')
            f = False
        except NoSuchElementException:
            pass

        gold = driver.find_element(By.XPATH,
                                   '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td[1]/table[1]/tbody/tr/td[2]/b/table/tbody/tr/td[2]/b').text
        if int(gold.replace(",", "")) < 300:
            f = False

        if f:
            if 'Окончание смены:' in page_text and int(free_count) == 0:
                end_time = page_text[page_text.find('Окончание смены: ') + 17:page_text.find('\nСписок')]
                print(end_time)
                sleep_until_target_time(end_time, driver, driver.current_url)
            else:
                sleep_until_target_time(10, driver, driver.current_url)

        cicle += 1
        # cicle = 3



def sleep_until_target_time(target_time_str, driver, url):
    loop = asyncio.get_running_loop()

    now = datetime.now()
    if type(target_time_str) == int:
        target_time = now + timedelta(seconds=int(target_time_str))
    else:
        target_time = datetime.strptime(target_time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)

    if target_time < now:
        target_time += timedelta(days=1)

    delay = (target_time - now).total_seconds()+10

    # delay = 30
    if delay > 0:
        print(f"Функция будет вызвана через {delay} секунд.")

        loop.call_at(loop.time() + delay, run_async_in_loop, loop, selling(driver, url))


async def selling(driver, url):
    logging.info('Начинаю')
    page_text = driver.find_element(By.TAG_NAME, "body").text
    if 'Объект переполнен артефактами.' in page_text:
        return
    while True:
        driver.get(url)
        table = driver.find_element(By.XPATH, "/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody")
        rows = table.find_elements(By.TAG_NAME, "tr")

        for i, row in enumerate(rows):

            try:
                inpu = driver.find_element(By.XPATH,
                                           f"/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody/tr[{i}]/td[5]/form/nobr/input[1]")
                butto = driver.find_element(By.XPATH,
                                           f"/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody/tr[{i}]/td[5]/form/nobr/input[2]")

                res_count = driver.find_element(By.XPATH,
                                           f"/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[2]/tbody/tr[{i}]/td[6]").text
                inpu.clear()
                inpu.send_keys(int(res_count))
                butto.click()

            except NoSuchElementException:
                pass

        gold = driver.find_element(By.XPATH,
                                   '/html/body/center/table/tbody/tr/td/table/tbody/tr/td/table[1]/tbody/tr/td[1]/table[1]/tbody/tr/td[2]/b/table/tbody/tr/td[2]/b').text
        if int(gold.replace(",", "")) < 300:
            end_time = page_text[page_text.find('Окончание смены: ') + 17:page_text.find('\nСписок')]
            sleep_until_target_time(end_time, driver, driver.current_url)
            break

        await asyncio.sleep(1)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        free_count = page_text[page_text.find('Свободных мест: ') + 16:page_text.find('\n\nПроизведено:')]

        if int(free_count) == 0:
            end_time = page_text[page_text.find('Окончание смены: ') + 17:page_text.find('\nСписок')]
            sleep_until_target_time(end_time, driver, driver.current_url)
            break
