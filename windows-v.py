import json, threading, csv, time, threading, os, sys
from multiprocessing import Pool, cpu_count, freeze_support
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

# 셀레니움 설정
options = webdriver.ChromeOptions()
options.add_argument('headless')
options.add_argument('window-size=1920x1080')
options.add_argument("disable-gpu")
options.add_argument("lang=ko_KR")
options.add_argument(
    "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")

threadLocal = threading.local()

# 셀레니움 드라이버 가져오기


def get_driver():
    driver = getattr(threadLocal, 'driver', None)
    # if driver is None:
    #     driver = webdriver.Chrome(options=options)
    if getattr(sys, 'frozen', False): 
        chromedriver_path = os.path.join(sys._MEIPASS, "chromedriver.exe") # pylint: disable=no-member
        driver = webdriver.Chrome(chromedriver_path, options=options) 
    else:
        driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    setattr(threadLocal, 'driver', driver)
    return driver

# 카카오맵에서 검색후 목록가져오기


def get_details_by_link(query):
    driver = get_driver()
    driver.get("https://m.map.kakao.com/actions/searchView?q="+query)

    def get_place_list():
        driver.find_element_by_id('placeList')
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        place_list = soup.find_all(class_="search_item")
        for place in place_list:
            try:
                cid = place.attrs["data-cid"]
                # print(cid)
                result_list.append(cid)
            except Exception:
                # print(place)
                return

    flag = True

    def get_next_page():
        try:
            more_btn = driver.find_element_by_class_name("link_more")
            more_btn.send_keys(Keys.ENTER)  # 클릭
            time.sleep(1)
            return True
        except Exception:
            print('페이지끝')
            return False

    page = 1
    while flag:
        print(page, "페이지>")
        result = get_next_page()
        flag = result
        page = page+1

    result_list = []
    get_place_list()
    driver.quit()
    return result_list


def get_value(my_dict, key):
    if type(my_dict) == "str":
        return ""
    if key in my_dict:
        return my_dict[key]
    else:
        return ""


def get_depth_value(my_dict, keys):
    def check_key(search_dict, key):
        if key in search_dict:
            return True
    flag = True
    search_dict = my_dict
    for key in keys:
        flag = check_key(search_dict, key)
        if flag:
            search_dict = search_dict[key]

    if flag:
        return search_dict
    else:
        return ""


def get_list_by_index(my_list, index):
    if type(my_list) == list:
        return my_list[index]
    else:
        return {}


def get_map_detail(place_id):
    url = "https://place.map.kakao.com/main/v/" + place_id
    res = requests.get(url)
    result_json = res.json()
    basic_info = result_json['basicInfo']
    address = basic_info["address"]

    def get_score(top, down):
        try:
            return round(top/down, 1)
        except ZeroDivisionError:
            return 0

    place_data = {
        "업종명": get_value(basic_info, "cate1name"),
        "장소": get_value(basic_info, "placenamefull"),
        "전화번호": get_value(basic_info, "phonenum"),
        "주소": get_depth_value(address, ["region", "newaddrfullname"]) + " " + get_depth_value(address, ["newaddr", "newaddrfull"]) + "" + get_value(address, "addrdetail"),
        "업데이트일자": basic_info["source"]["date"],
        "크롤링일자": time.strftime("%Y.%m.%d"),
        "카테고리": get_value(basic_info, "catename"),
        "영문명": get_value(basic_info, "englishname"),
        "홈페이지": get_value(basic_info, "homepage"),
        "영업시간": get_value(get_list_by_index(get_depth_value(basic_info, ["openHour", "realtime", "currentPeriod", "timeList"]), 0), "timeSE"),
        "평점": get_score(get_depth_value(basic_info, ["feedback", "scoresum"]), get_depth_value(basic_info, ["feedback", "scorecnt"])),
        "태그": get_value(basic_info, "metaKeywordList"),
        "소개": get_value(basic_info, "introduction"),
        "cid": get_value(basic_info, "cid")
    }

    print(place_data["장소"])
    return place_data

if __name__ == '__main__':
    freeze_support()
    print("\n카카오맵 - 크롤러 - 퍼블릭스 - v0.1\n")
    query = input('검색어 입력> ')
    print("\"" + query + "\"" + " " + "카카오맵에서 검색중...")
    place_ids = get_details_by_link(query)


    # place_ids 중복제거
    filtered_place_ids = list(set(place_ids))
    print("[" + query + "]" + "검색 결과: ", len(filtered_place_ids), "건")
    print("\n\n####################################\n\n")


    pool = Pool(processes=4)  # 사용할프로세스 개수 cpu_count()-1
    print('상세정보 가져오는중...')

    pool_result = pool.map(get_map_detail, filtered_place_ids)



    # csv파일로 결과 저장
    current = time.strftime("%Y%m%d_%H%M%S")
    filename = query.replace(' ', '_') + '_' + current + '.csv'

    print("\n\n####################################\n\n")

    with open(filename, 'w', newline='', encoding='UTF-8-sig') as file:
        writer = csv.writer(file)
        header = ["순번"]
        header.extend(pool_result[0].keys())
        writer.writerow(header)

        for idx, item in enumerate(pool_result):
            values = [idx+1]
            values.extend(item.values())
            writer.writerow(values)

    print('저장완료:', filename)
    finish = input('종료하려면 아무키나 누르세요.')

# pyinstaller -F --noconsole --add-binary "C:\chromedriver.exe;." crawler.py
# pyinstaller -F --add-binary "C:\chromedriver.exe;." crawler.py
