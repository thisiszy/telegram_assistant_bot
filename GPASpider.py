from bs4 import BeautifulSoup
import requests
import numpy as np
import re
import pprint
import pandas as pd


headers = {
    'user-agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/79.0.3945.117 '
        'Safari/537.36'
}

session = requests.session()
session.headers.update(headers)


# 获取成绩
def get_grades(semesterIds='62,81,101,121'):
    response = session.get("https://jw.ustc.edu.cn/for-std/grade/sheet/getGradeList?trainTypeId=1",
                           params={'semesterIds': semesterIds})
    soup = BeautifulSoup(response.content, 'lxml')
    content = soup.p.contents[0]
    content = re.sub('true', 'True', content)
    content = re.sub('null', 'None', content)

    # 按学期先取出成绩
    scores_semesters = re.findall(r'"scores":\[.*?\]', content)

    # 再把每学期的成绩取出
    scores = []
    for i in range(len(scores_semesters)):
        scores += (re.findall(r'\{.*?\}', scores_semesters[i]))

    pop_list = ['id', 'courseNameCh', 'semesterEn', 'score', 'credits', 'gp']
    for i in range(len(scores)):
        exec('scores[i] = ' + scores[i])
        keys = list(scores[i].keys())
        for key in keys:
            if key not in pop_list:
                scores[i].pop(key)

    # 处理成DataFrame
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)
    scores = pd.DataFrame(scores)
    scores.rename(columns={'gp': 'GPA', 'semesterEn': 'semester', 'courseNameCh': 'course'}, inplace=True)
    scores['score'] = scores['score'].apply(lambda x: float(x) if x else np.nan)
    # print(scores)

    scores_dropped = scores.dropna(axis=0, how='any')
    GPA_4 = scores_dropped['score'].copy().apply(lambda x: 4.0 if float(x) >= 90
    else 3.0 if float(x) >= 80
    else 2.0 if float(x) >= 70
    else 1.0 if float(x) >= 60
    else 0.0)

    GPA_weighted = np.sum(scores_dropped['credits'] * scores_dropped['GPA']) / np.sum(scores_dropped['credits'])
    score_weighted = np.sum(scores_dropped['credits'] * scores_dropped['score']) / np.sum(scores_dropped['credits'])
    score_average = np.sum(scores_dropped['score']) / len(scores_dropped['score'])
    GPA_4_weighted = np.sum(scores_dropped['credits'] * GPA_4) / np.sum(scores_dropped['credits'])
    return scores, GPA_weighted, score_weighted, score_average, GPA_4_weighted


# 获取培养计划
def get_courses():
    # 培养计划的xml地址
    response = session.get("https://jw.ustc.edu.cn/for-std/program/root-module-json/222")
    soup = BeautifulSoup(response.content, 'lxml')
    con = ''
    for i in range(len(soup.body.contents)):
        c = str(soup.body.contents[i])
        c = re.sub(r'true', 'True', c)
        c = re.sub(r'false', 'False', c)
        c = re.sub(r'null', 'None', c)
        c = re.sub(r'(<p>)|(<.p>)', '', c)
        con += c

    content = eval(con)
    courses = content['allPlanCourses']
    courses_list = []
    for i in range(len(courses)):
        courses_list.append([courses[i]['readableTerms'][0],
                             courses[i]['course']['nameZh'],
                             courses[i]['course']['periodInfo']['total'],
                             courses[i]['course']['periodInfo']['theory'],
                             courses[i]['course']['periodInfo']['practice'],
                             courses[i]['course']['periodInfo']['weeks'],
                             courses[i]['course']['periodInfo']['periodsPerWeek'],
                             courses[i]['course']['credits']])

    seq = {'1秋': 1, '1春': 2, '1夏': 3,
           '2秋': 4, '2春': 5, '2夏': 6,
           '3秋': 7, '3春': 8, '3夏': 9,
           '4秋': 10, '4春': 11, '4夏': 12
           }
    courses_columns = courses_list.sort(key=lambda x: seq[x[0]])
    courses_columns = ['readableTerms', 'course', 'total', 'theory', 'practice', 'weeks', 'periodsPerWeek', 'credits']
    courses_df = pd.DataFrame(courses_list,
                              columns=courses_columns
                              )
    return courses_df


def Spider_gpa(username, password):
    data = {'username': username, 'password': password}
    session.post("https://passport.ustc.edu.cn/login?service=https%3A%2F%2Fjw.ustc.edu.cn%2Fucas-sso%2Flogin", data = data)
    scores, GPA_weighted, score_weighted, score_average, GPA_4_weighted = get_grades()
    return scores, GPA_weighted, score_weighted, score_average, GPA_4_weighted