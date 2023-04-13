import time
import re
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import visibility_of_element_located
from selenium.webdriver.support.wait import WebDriverWait


class Waits:
    @staticmethod
    def until_visible(wait, locator):
        wait.until(visibility_of_element_located(locator))


class Locators:
    usrInput = (By.NAME, "loginfmt")
    pssInput = (By.NAME, "passwd")
    loginButton = (By.ID, "idSIButton9")
    # table = (By.CLASS_NAME, "table-striped")
    pagination = (By.XPATH, "//*[@class='pagination pagination-centered justify-content-center']")


def login(browser, browser_wait):
    with open('C:/Users/amit5/OneDrive/Documents/projects/creds.txt', 'r') as f:
        creds = f.read().split(",")
    Waits.until_visible(browser_wait, Locators.usrInput)
    browser.find_element(*Locators.usrInput).send_keys(creds[0] + Keys.ENTER)
    Waits.until_visible(browser_wait, Locators.pssInput)
    browser.find_element(*Locators.pssInput).send_keys(creds[1] + Keys.ENTER)
    time.sleep(2)
    Waits.until_visible(browser_wait, Locators.loginButton)
    browser.find_element(*Locators.loginButton).click()


def get_tests(soup):
    tabs = soup.find('div', {'id': 'nav-tabContent'}).findChild('div').findChildren('h5', recursive=False)
    tests = {}
    for tab in tabs:
        if tab.text == "מבחנים":
            spans = tab.find_next_siblings('span')
            for span in spans:
                text_split = span.text.split(":")
                tests['' + text_split[0].strip() + ''] = text_split[-1].strip()
    return tests


# USE page_shows_search_results
def get_groups_info(page_source):
    group_spans = page_source.find('div', {'id': 'semester_information'}).findAll('span', class_='list-group-item')
    groups = []
    for span in group_spans:
        tables = span.find("table", class_='table').findAll('table')
        table_text = tables[0].text
        num = re.findall('[0-9]+', table_text)[0]
        lines = table_text.split('\n')
        vacancies = ""
        for t in range(len(lines)):
            if ':' in lines[t]:
                vacancies = lines[t+1]
        if vacancies == "":
            continue
        vacancies = re.findall('[0-9]+', vacancies)
        group = {
            "num": num,
            "vacancies": int(vacancies[0]) if vacancies else 0,
        }
        rows = tables[1].findAll('tr')
        schedule = []
        for row in rows:
            if "אין מידע" in row.text:
                continue
            cells = row.findAll('td')
            teacher, n = re.subn('[|\n]', '', cells[4].text)
            event = {
                "event_type": cells[0].text,
                "day:": cells[1].text,
                "time": cells[2].text,
                "location": cells[3].text,
                "teacher": teacher.strip(),
                "desc": cells[5].text
            }
            schedule.append(event)
        group["schedule"] = schedule
        groups.append(group)
    return groups


def get_course_info(courses):
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get("https://students.technion.ac.il/auth/oidc/")
    wait = WebDriverWait(driver, timeout=20)
    login(driver, wait)
    for course in courses:
        print("Fetching info for course #{}.".format(course["number"]))
        driver.get(course["link"])
        source_page = bs(driver.page_source, features="html.parser")
        with open("try.html", 'w+', encoding='utf-8') as f:
            f.write(driver.page_source)
        groups = get_groups_info(source_page)
        course["tests"] = get_tests(source_page)
        course["groups"] = groups

    driver.quit()
    return courses

