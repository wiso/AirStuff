from selenium import webdriver
import pickle
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)

URL_LOGIN = 'https://air.unimi.it/au/login'


def get_driver(debug=False, driver='chrome'):
    WINDOW_SIZE = "1920,1080"

    if driver == 'chrome':
        logging.info('creating chrome')
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--incognito")
        if not debug:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)

        driver = webdriver.Chrome(options=chrome_options)
    elif driver == 'firefox':
        logging.info('creating firefox')
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.add_argument("-private")
        if not debug:
            firefox_profile = webdriver.FirefoxProfile()
            firefox_profile.set_preference("media.volume_scale", "0.0")
            firefox_options.profile = firefox_profile
            firefox_options.headless = True
        firefox_options.add_argument("--width=%s" % WINDOW_SIZE.split(',')[0])
        firefox_options.add_argument("--height=%s" % WINDOW_SIZE.split(',')[1])
        driver = webdriver.Firefox(options=firefox_options)

    return driver


def login():
    """Login to the website"""
    driver = get_driver(debug=True)

    driver.get(URL_LOGIN)

    input('press enter where you are logged in')
    cookies = driver.get_cookies()
    pickle.dump(cookies, open("cookies.pkl", "wb"))
    driver.quit()


def load_cookie(driver):
    cookies = pickle.load(open("cookies.pkl", "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)


if __name__ == '__main__':
    login()