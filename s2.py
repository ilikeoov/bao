import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import json
from datetime import datetime, timedelta

# 매핑 데이터 정의
mapping_data = {
    "01": {
        "00H00101": "패밀리(취사/스탠다드/침대)[4인]",
        "00H00121": "패밀리(취사/울산바위뷰/침대)[4인]",
        "00I00101": "스위트(취사/스탠다드/침대)[5인]",
        "00I00121": "스위트(취사/울산바위뷰/침대)[5인]",
        "00HPF101": "패밀리(Pet Friendly/스탠다드/침대)[4인]",
        "00IPF101": "스위트(Pet Friendly/스탠다드/침대)[5인]",
        "00H001F1": "패밀리(취사/설악마운틴뷰/침대)[4인]",
        "00I001F1": "스위트(취사/설악마운틴뷰/침대)[5인]"
    },
    # ... (다른 매핑 데이터 생략)
}

def get_logged_in_session():
    # GitHub Secrets에서 로그인 정보 가져오기
    username = os.getenv('SONO_USERNAME')
    password = os.getenv('SONO_PASSWORD')

    # Chrome WebDriver 자동 다운로드 및 설정
    driver_service = Service(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=driver_service, options=chrome_options)
    login_url = "https://www.sonohotelsresorts.com/member/login?targetPath=/reserve"
    driver.get(login_url)

    try:
        # 로그인 절차
        driver.find_element(By.ID, 'lginId').send_keys(username)
        driver.find_element(By.ID, 'lginPw').send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='button' and @class='btn xl fill']").click()
        time.sleep(3)  # 페이지 로드 대기
        cookies = driver.get_cookies()
    finally:
        driver.quit()

    # Requests 세션에 쿠키 추가
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    return session

def fetch_data(session, check_in_date, check_out_date):
    url = "https://www.sonohotelsresorts.com/api/hms/user/memberReservation/room/list/remaining"
    params = {
        "lang": "ko",
        "deviceType": "PC",
        "mobileAppYn": "N",
        "memNo": "27095600",
        "userIndCd": "Y",
        "rsvIndCd": "9",
        "ciYmd": check_in_date,
        "coYmd": check_out_date,
        "nights": 1,
        "rmCnt": 1,
        "adultCnt": 1,
        "childCnt": 0,
        "rmTypeCode": "",
        "paymentType": ""
    }
    response = session.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def format_date(date_str):
    # 날짜 형식을 "MM월 DD일"로 변경
    return f"{date_str[4:6]}월 {date_str[6:8]}일"

def transform_status(status):
    if status in ["예약마감", "미운영"]:
        return "예약불가"
    elif status in ["예약원활", "마감임박"]:
        return "예약가능"
    else:
        return status  # 알 수 없는 상태는 그대로 반환

def extract_info(data):
    if data is None:
        return []
    
    result = []
    for store in data['body']:
        resort_name = store['storeNm']
        store_cd = store['storeCd']
        for room in store['rmTypeList']:
            rm_type_cd = room['rmTypeCd']
            rsv_status_nm = room['rsvStatusNm']
            ci_ymd = room['ciYmd']
            rm_type_nm = mapping_data.get(store_cd, {}).get(rm_type_cd, rm_type_cd)  # 매칭이 안되면 코드 그대로 사용
            result.append({
                '리조트명': resort_name,
                '날짜': format_date(ci_ymd),
                '룸타입': rm_type_nm,
                '상태': transform_status(rsv_status_nm)
            })
    return result

def generate_dates(start_date, end_date):
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    return date_list

def main():
    session = get_logged_in_session()
    start_date = datetime.strptime("20240701", "%Y%m%d")
    end_date = datetime.strptime("20241031", "%Y%m%d")
    dates = generate_dates(start_date, end_date)
    all_info = []
    
    for date in dates:
        check_in_date = date
        check_out_date = (datetime.strptime(date, "%Y%m%d") + timedelta(days=1)).strftime('%Y%m%d')
        data = fetch_data(session, check_in_date, check_out_date)
        if data:  # 데이터가 존재하는 경우에만 처리
            info = extract_info(data)
            all_info.extend(info)
    
    # JSON 파일로 저장
    with open('s2.json', 'w', encoding='utf-8') as f:
        json.dump(all_info, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
