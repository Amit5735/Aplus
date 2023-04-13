import requests
from bs4 import BeautifulSoup as bs
import re
from datetime import datetime
import json


def throw_error_close(code):
    errors = ["Could not load courses page.",
              "Could not load session parameters.",
              "No courses to display.",
              "could not load course page."]
    print(errors[code])
    exit(0)

def get_session_params():
    url = 'https://students.technion.ac.il/local/technionsearch/search'
    resp = requests.Session().get(url)
    if not resp or resp.status_code != 200:
        throw_error_close(0)

    cookies = resp.cookies.get_dict()
    soup = bs(resp.content, features="html.parser")
    script_content = soup.findAll('script')[1].text
    sess_key = script_content[script_content.find("sesskey"): script_content.find('","sessiontimeout"')]
    if "sesskey" not in sess_key or not cookies['MoodleSessionstudentsprod']:
        throw_error_close(1)
    return {"cookie": cookies['MoodleSessionstudentsprod'], "session_key": sess_key[10:]}


def parse_courses_table(table):
    page_courses = []
    try:
        rows = table.select('tr:not(.emptyrow)')[1:]
        for row in rows:
            c1 = row.find('td', class_='c1')
            course = {
                "number": c1.text[:c1.text.find(" ")],
                "name": c1.text[c1.text.find(" - ") + 3:],
                "link": c1.find('a')['href'],
                "faculty": row.find('td', class_='c2').text,
                "is_taught": row.find('td', class_='c4').text,
            }
            page_courses.append(course)

    except():
        throw_error_close(2)

    return page_courses


def export_to_json(all_courses, file_prefix):
    outfile = open("./courses/" + file_prefix + ' ' + datetime.now().strftime("%d-%m%y %H_%M_%S.json"), "wb")
    outfile.write(json.dumps(all_courses, ensure_ascii=False).encode('utf-8'))


def add_semester(semester, add):
    year = int(semester[:4])
    season = int(semester[4:])
    season += add
    while season < 1:
        season += 3
        year -= 1
    while season > 3:
        year += 1
        season -= 3
    return str(year) + '0' + str(season)


def page_shows_search_results(soup):
    maincontent = soup.find('span', {'id': 'maincontent'})
    try:
        row = maincontent.find_next_siblings('div', class_="row")[1].text
        if  "אין כלום להציג" in row:
            return False
    finally:
        return True



def get_course_page(url, data, sess_params):
    soup = False
    for x in range(3):
        try:
            resp = requests.post(url, data, cookies={'MoodleSessionstudentsprod': sess_params["cookie"]})
            soup = bs(resp.content.decode('utf-8', 'ignore'), features="html.parser")
            break
        except():
            print("Couldn't get course page on try #{}.".format(x))

    if not soup:
        throw_error_close(3)
    return soup


def get_courses(sess_params, semester, humanities, level):
    base_url = "https://students.technion.ac.il/local/technionsearch/search"
    faculty = '32' if humanities else '_qf__force_multiselect_submission'
    all_courses = []
    data = {
        'mform_isexpanded_id_advance_filters': 0,
        'sesskey': str(sess_params["session_key"]),
        '_qf__local_technionsearch_form_search_advance': 1,
        'course_name': '',
        'semesterscheckboxgroup[' + add_semester(semester, -3) + ']': 0,
        'semesterscheckboxgroup[' + add_semester(semester, -2) + ']': 0,
        'semesterscheckboxgroup[' + add_semester(semester, -1) + ']': 0,
        'semesterscheckboxgroup[' + semester + ']': 1,
        'semesterscheckboxgroup[' + add_semester(semester, 1) + ']': 0,
        'semesterscheckboxgroup[' + add_semester(semester, 2) + ']': 0,
        'semesterscheckboxgroup[' + add_semester(semester, 3) + ']': 0,
        'faculties': faculty,
        'lecturer_name': '_qf__force_multiselect_submission',
        'daycheckboxgroup[sunday]': 1,
        'daycheckboxgroup[monday]': 1,
        'daycheckboxgroup[tuesday]': 1,
        'daycheckboxgroup[wednesday]': 1,
        'daycheckboxgroup[thursday]': 1,
        'daycheckboxgroup[friday]': 1,
        'hours_group_filter[fromtime]': '7.00',
        'hours_group_filter[totime]': '23.30',
        'credit_group_filter[min_points]': '0.0',
        'credit_group_filter[max_points]': '20.0',
        'academic_level_group[1]': int(level == 'bs'),
        'academic_level_group[2]': int(level == 'advanced'),
        'academic_level_group[3]': int(level == 'pre'),
        'has_english_lessons': 0,
        'submitbutton': '%D7%97%D7%99%D7%A4%D7%95%D7%A9'
    }
    soup = get_course_page(base_url, data, sess_params)
    page_num = int(soup.find("nav", class_="pagination").findAll('li')[-2]['data-page-number'])
    for page in range(0, page_num):
        table = soup.find('table')
        all_courses += parse_courses_table(table)
        url = base_url + "?page=" + str(page + 1)
        soup = get_course_page(url, data, sess_params)

    return all_courses


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


def get_groups_info(all_courses, sess_params):
    for course in all_courses:
        print("Fetching groups for course #{}.".format(course["number"]))
        soup = get_course_page(course["link"], {}, sess_params)
        if not page_shows_search_results(soup):
            continue

        course["tests"] = get_tests(soup)
        group_spans = soup.find('div', {'id': 'semester_information'}).findAll('span', class_='list-group-item')
        for span in group_spans:
            tables = span.find("table", class_='table').findAll('table')
            num = re.findall('[0-9]+', tables[0].text)[0]
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

            group = next((x for x in course["groups"]if x["number"] == num), None)
            if group is not None:
                group["schedule"] = schedule

    return courses
