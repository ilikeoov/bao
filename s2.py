import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from datetime import datetime, timedelta

# 매핑 데이터 정의
mapping_data = {
    # 생략된 데이터
}

def get_logged_in_session():
    # Chrome WebDriver 자동 다운로드 및 설정
    driver_service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 헤드리스 모드
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=driver_service, options=options)
    
    login_url = "https://www.sonohotelsresorts.com/member/login?targetPath=/reserve"
    driver.get(login_url)

    try:
        # 명시적 대기 설정
        wait = WebDriverWait(driver, 10)
        
        # 로그인 절차
        username_input = wait.until(EC.element_to_be_clickable((By.ID, 'lginId')))
        username_input.send_keys('dangsj1')
        
        password_input = wait.until(EC.element_to_be_clickable((By.ID, 'lginPw')))
        password_input.send_keys('chdan6164!')
        
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @class='btn xl fill']")))
        login_button.click()
        
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
    end_date = datetime.strptime("20240731", "%Y%m%d")
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

