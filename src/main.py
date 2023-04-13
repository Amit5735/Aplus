import argparse

from src.modules.curl import get_session_params, get_courses, export_to_json
from src.modules.automation import get_course_info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("semester", help="format: YYYY0X, whereas YYYY is the year and X is the number of semester.")
    parser.add_argument("-u", "--humanities", action="store_true", help="Retrieve data only for faculty of humanities")
    parser.add_argument("level", help="Choose academic level - pre / bs / advanced")
    args = parser.parse_args()
    session_params = get_session_params()
    courses = get_courses(session_params, args.semester, args.humanities, args.level)
    # with open("./courses/use.json", 'r', encoding="utf-8") as f:
    #     courses = json.loads(f.read())
    courses = get_course_info(courses)
    prefix = "hum - " if args.humanities else "all - "
    export_to_json(courses, prefix)



