import os
import json
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException

from config import *
import Course
import fuck_kaptcha
import TTAP_reader

# Wait time for page loading
WAIT_TIME_VELI_SHORT = 0.5 # short short wait time
WAIT_TIME_SHORT = 3   #  3 seconds short waiting
WAIT_TIME_LONG  = 10  # 10 seconds long waiting

# Global constant variable, URLs
URL = "https://unitreg.utar.edu.my/portal/courseRegStu"
LOGIN_URL = URL + "/login.jsp"
REGISTER_URL = URL + "/registration/studentRegistrationSurvey.jsp"
REGISTER_COURSE_URL = URL + "/registration/registerUnitSurvey.jsp"

def sessionExpired(driver: webdriver):
    return bool(driver.find_elements(By.XPATH, "//*[contains(text(), 'Session Expired')]"))

# The function try to login the system if cookies are stored before
def tryLoginWithCookies(driver: webdriver):

    # If cookies.txt does not exist in current directory
    if not os.path.isfile("cookies.txt"):
        # Just back to the login page to login again
        return False

    # Open the file and read out all the cookies
    with open("cookies.txt", "r") as file:
        cookies = json.load(file)
        # Go to an 404 page to ensure cookies are set for the same site
        driver.get(URL+"/fuckyouutar")
        driver.delete_all_cookies()
        # Set cookies!
        for cookie in cookies:
            driver.add_cookie(cookie)
    # Go to the register url to see if login successful (The cookies may expired)
    driver.get(REGISTER_URL)
    expired = sessionExpired(driver)
    if expired:
        return False
    
    return True
        
def login(driver: webdriver):
    # Say my appreciation to UTAR
    print("Fuck you UTAR!")
    print("Trying to login...")

    # Go to login page
    driver.get(LOGIN_URL)

    # Wait for the page to be loaded
    try:
        WebDriverWait(driver, WAIT_TIME_SHORT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form[name=frmParam]"))
        )
    except TimeoutException:
        driver.refresh()
        return False

    # Locate the input fields
    try:
        student_id_input = driver.find_element(By.CSS_SELECTOR, "input[name=reqFregkey]")
        password_input = driver.find_element(By.CSS_SELECTOR, "input[name=reqPassword]")
        kaptcha_input = driver.find_element(By.CSS_SELECTOR, "input[name=kaptchafield]")
    except NoSuchElementException:
        print("Element not found")
        return False

    # Solve kaptcha
    kaptcha_img = driver.find_element(
        # This XPATH find:
        # XPATH                    MEANING
        # //                       the element shall locate at anywhere
        # input                    the element shall be an input
        # [@name='kaptchafield']   the name attribute shall have the name "kaptchafield"
        # /..                      go to its parent
        # /img[i]                  and get the first img child
        By.XPATH, "//input[@name='kaptchafield']/../img[1]"
    ).screenshot_as_png

    kaptcha_pass = fuck_kaptcha.getKaptchaText(kaptcha_img)

    # Enter all infomation and press enter
    student_id_input.send_keys(STUDENT_ID)
    password_input.send_keys(PASSWORD)
    kaptcha_input.send_keys(kaptcha_pass)
    kaptcha_input.send_keys(Keys.RETURN)

    # Wait to see if user successfully logged in
    try:
        WebDriverWait(driver, WAIT_TIME_VELI_SHORT).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Log Out')]"))
        )
    except TimeoutException:
        return False
    
    print("We are in!")
    return True

def storeCookies(driver: webdriver):
    cookies = driver.get_cookies()
    with open("cookies.txt", "w+") as file:
        json.dump(cookies, file)
        print("Cookies saved")

def regsiterCourse(driver: webdriver, course: Course):

    # Testing only
    # driver.get("file:///C:/Users/yee05/Application/fuck_utar/utar/unitreg_shit/myUTAR%20-%20The%20Universiti%20Tunku%20Abdul%20Rahman%20Web%20Portal.html")
    driver.get(REGISTER_COURSE_URL)

    # wait for the page to be loaded
    try:
        WebDriverWait(driver, WAIT_TIME_SHORT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table#tblGrid"))
        )
    except TimeoutException:
        if sessionExpired(driver):
            login(driver)
        return False
    
    # ========================================== #
    #           View course timetable            #
    # ========================================== #
    
    # Locate input field for course code and "View" button
    try:
        course_input = driver.find_element(By.CSS_SELECTOR, "input#reqUnit[name=reqUnit]")
    except NoSuchElementException:
        print("Element not found in register course...")
        return False

    # Enter course code and click "View"
    print(f"Registering course {course.code} - {course.name}...")
    course_input.send_keys(course.code)
    course_input.send_keys(Keys.RETURN)

    # ========================================== #
    #    Select course according to timetable    #
    # ========================================== #

    # wait for the timetable to be loaded
    try:
        WebDriverWait(driver, WAIT_TIME_SHORT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form[name=frmSummary]"))
        )
    except TimeoutException:
        driver.refresh()
        return False
    
    try:
        timetable = driver.find_elements(By.CSS_SELECTOR, "form[name=frmSummary] tr:nth-child(n+3):has(input)")
        submit_btn = timetable.pop().find_element(By.CSS_SELECTOR, "input[name=Submit]")
    except NoSuchElementException:
        print("Element not found in register course...")
        return False

    max_slots = len(course.slots)
    # To select the slot with highest priority
    slot_priority = {
        "L": 99,
        "T": 99,
        "P": 99
    }
    # loop through the timetable and select the course
    for row in timetable:
        try:
            class_type = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text
            class_slot = int(row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text)
        except NoSuchElementException:
            print("Element not found in register course...")
            return False

        # Check if the class type and slot is in the list
        class_slots = course.slots.get(class_type)
        if class_slots != None and class_slot in class_slots:
            try:
                row.find_element(By.CSS_SELECTOR, "input[type=checkbox]").click()
            except NoSuchElementException:
                print("Holly shit you are late for this slot!")
            else:
                max_slots -= 1

        if max_slots == 0:
            break
    
    if max_slots > 0:
        print("Shit, no available slots!")
        driver.get(REGISTER_URL)
        return True

    submit_btn.click()

    try:
        WebDriverWait(driver, WAIT_TIME_VELI_SHORT).until(
            (EC.alert_is_present())
        )
    except TimeoutException:
        print("Registered!")
        return True

    alert = Alert(driver)
    if "please select a valid class combination" in alert.text:
        print("Something when wrong when selecting...")
        print("Will retry in this case")
        return False
    elif "the time of selected units are clashed with the other registered units" in alert.text:
        print("Invalid timetable! Please check again!")
        return True
    elif "your schedule has exceeded the maximum number of credit hours allowed":
        print("Maximum credit hours reached! You so hardworking meh? No lah")
        return True

    print("Should be okay here")
    return True

def registerCourses(driver: webdriver, courses: list[Course.Course]):

    driver.get(REGISTER_URL)

    # Testing
    # driver.get("file:///C:/Users/yee05/Application/fuck_utar/utar/unitreg_shit/myUTAR%20-%20The%20Universiti%20Tunku%20Abdul%20Rahman%20Web%20Portal_register.html")

    # wait for the page to be loaded
    try:
        WebDriverWait(driver, WAIT_TIME_SHORT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table#tblGrid"))
        )
    except TimeoutException:
        if sessionExpired(driver):
            login(driver)
        return False
    
    # Loop the courses list and register each course
    for course in courses:
        loop = True
        while loop:
            try:
                WebDriverWait(driver, WAIT_TIME_VELI_SHORT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name=Register]"))
                )
            except TimeoutException:
                print("Shit the registration is not open yet!")
                print("Try to relogin...")
                while not login(driver):
                    print("Can't login, retrying...")
                driver.get(REGISTER_URL)
            except UnexpectedAlertPresentException:
                print("Why the fuck there is an alert!?")
                continue
            
            # locate the "Register" button
            try:
                register_btn = driver.find_element(By.CSS_SELECTOR, "input[name=Register]")
            except NoSuchElementException:
                print("weird, someting when wrong...")
                continue
            # Click click
            register_btn.click()

            print("Biding course...")
            if regsiterCourse(driver, course):
                loop = False

    print("Done!")

    return True

# Create a new instance of the Firefox driver
if __name__ == "__main__":
    
    drivers = webdriver.Chrome()

    logged_in = tryLoginWithCookies(drivers)

    if not logged_in:
        while(not login(drivers)):
            print("Oh shit! Failed to login! UTAR sucks!")
            print("No worry lets try again!")

    print("Storing cookies...yum yum yum")
    storeCookies(drivers)

    drivers.get(REGISTER_URL)

    courses = TTAP_reader.readTimetable(FILENAME)

    while(not registerCourses(drivers, courses)):
        print("Trying to register courses...")

    # Dunno what to do so wait for 10 seconds
    sleep(10)

    # Close the driver
    drivers.quit()