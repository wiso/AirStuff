from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
import pickle
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)
selenium_logger.setLevel(logging.WARNING)

URL_LOGIN = 'https://air.unimi.it/au/login'
URL_MYDSPACE = 'https://air.unimi.it/mydspace'
URL_SUBMIT = 'https://air.unimi.it/submit'

from enum import Enum
class ReturnValue(Enum):
    SUCCESS = 1
    DUPLICATE = 2


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
        # cookies do not work in firefox private session
        # firefox_options.add_argument("-private")
        if not debug:
            firefox_profile = webdriver.FirefoxProfile()
            firefox_profile.set_preference("media.volume_scale", "0.0")
            firefox_options.profile = firefox_profile
            firefox_options.headless = True
        firefox_options.add_argument("--width=%s" % WINDOW_SIZE.split(',')[0])
        firefox_options.add_argument("--height=%s" % WINDOW_SIZE.split(',')[1])
        driver = webdriver.Firefox(options=firefox_options)

    return driver


def login(driver):
    """Login to the website"""

    driver.get(URL_LOGIN)

    input('press enter where you are logged in')
    save_cookies(driver)
    driver.quit()

def save_cookies(driver):
    cookies = driver.get_cookies()
    logging.info('saving %d cookies', len(cookies))
    pickle.dump(cookies, open("cookies.pkl", "wb"))


def load_cookie(driver):
    cookies = pickle.load(open("cookies.pkl", "rb"))
    if not cookies:
        raise IOError("no cookie found. Have you login?")
    for cookie in cookies:
        driver.add_cookie(cookie)
    logging.info('%d cookies have been loaded' % len(cookies))


def upload_from_doi(driver, info):
    driver.get('https://air.unimi.it')
    try:
        load_cookie(driver)
    except IOError:
        logging.info('no cookies found')

    driver.get(URL_SUBMIT)

    if 'login' in driver.current_url:
        logging.warning("You are not logged in")
        input('press enter when you are logged in')
        save_cookies(driver)
        driver.get(URL_SUBMIT)

    driver.find_element_by_xpath("//a[contains(text(), 'Ricerca per identificativo')]").click()
    element_doi = driver.find_element_by_id("identifier_doi")
    logging.debug('waiting for element to be visible')
    WebDriverWait(driver, 10).until(EC.visibility_of(element_doi))
    element_doi.clear()
    logging.debug('insert doi %s', info['doi'])
    element_doi.send_keys(info['doi'])
    driver.find_element_by_id("lookup_idenfifiers").click()

    # second page
    logging.debug('waiting for page')
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "checkresult0"))).click()
    type_document_selector = driver.find_element_by_id("select-collection0")
    sel = Select(type_document_selector)
    sel.select_by_visible_text("01 - Articolo su periodico")
    logging.debug('ask to import selected records')
    driver.find_element_by_xpath("//button[contains(text(), 'Importa i record selezionati')]").click()

    # third page (licence)
    driver.find_element_by_name("submit_grant").click()

    # check duplicate
    if driver.find_elements_by_id('duplicateboxtitle'):
        logging.warning('Trying to insert duplicate')
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'cancelpopup'))).click()
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, 'submit_remove'))).click()
        return ReturnValue.DUPLICATE

    # warning authors
    many_authors = False
    try:
        driver.find_element_by_xpath("//h4[@class='modal-title' and contains(text(), 'Attenzione')]//../..//button[contains(text(), 'Chiudi')]").click()
        many_authors = True
    except NoSuchElementException:
        pass

    page = PageDescrivere2()
    logging.debug('filling page Descrivere 2')
    if not page.get_title():
        page.set_title(info['title'])
    if not page.get_abstract():
        page.set_abstract(info['abstract'])
    if not page.get_keywords():
        page.set_keywords(info['keywords'])


    import pdb; pdb.set_trace()

    return ReturnValue.SUCCESS


class PageDescrivere2:
    def __init__(self, driver):
        self.driver = driver

    def set_title(self, title):
        element_title = self.driver.find_element_by_id("dc_title_id")
        element_title.clear()
        element_title.send_keys(title)

    def get_title(self):
        element_title = self.driver.find_element_by_id("dc_title_id")
        return element_title.text

    def set_abstract(self, abstract):
        Select(self.driver.find_element_by_name('dc_description_qualifier')).select_by_visible_text('Inglese')

        element_abstract = self.driver.find_element_by_name('dc_description_value')
        element_abstract.clear()
        element_abstract.send_keys(abstract)

    def get_abstract(self):
        element_abstract = self.driver.find_element_by_name('dc_description_value')
        return element_abstract.text

    def set_keywords(self, keyworkds):
        k = '; '.join('keywords')
        element_keywords = self.driver.find_element_by_id('dc_subject_keywords_id')
        element_keywords.clear()
        element_keywords.send_keys(k)

    def get_keywords(self):
        element_keywords = self.driver.find_element_by_id('dc_subject_keywords_id')
        return element_keywords.text


def upload(driver, info):
    driver.get('https://air.unimi.it')
    load_cookie(driver)
    driver.get(URL_SUBMIT)

    if 'login' in driver.current_url:
        logging.warning("You are not logged in")
        input('press enter when you are logged in')
        save_cookies()
        driver.get(URL_SUBMIT)

    type_document_selector = driver.find_element_by_id("select-collection-manual")
    sel = Select(type_document_selector)
    sel.select_by_visible_text("01 - Articolo su periodico")
    driver.find_element_by_id("manual-submission-button").click()
    driver.find_element_by_name("submit_grant").click()

    page = PageDescrivere2()

    # title
    page.set_title(driver, info['title'])

    # abstract
    page.set_abstract(into['abstract'])

    # keywords
    page.set_keywords(info['keywords'])

    # international authors
    element_international = driver.find_element_by_xpath("//select[@name='dc_description_international']")
    # firefox is choosy: it cannot select on hidden <select> (chrome works)
    old_class = element_international.get_attribute('class')
    driver.execute_script("arguments[0].setAttribute('class', '')", element_international)
    sel = Select(element_international)
    sel.select_by_visible_text('Sì')
    driver.execute_script("arguments[0].setAttribute('class', '%s')" % old_class, element_international)

    # language
    element_language = driver.find_element_by_xpath("//select[@name='dc_language_iso']")
    old_class = element_language.get_attribute('class')
    driver.execute_script("arguments[0].setAttribute('class', '')", element_language)
    sel = Select(element_language)
    sel.select_by_visible_text('English')
    driver.execute_script("arguments[0].setAttribute('class', '%s')" % old_class, element_language)

    # authors
    element_authors = driver.find_element_by_id("widgetContributorSplitTextarea_dc_authority_people")
    element_authors.clear()
    element_authors.send_keys(';'.join(info['authors']))
    driver.find_element_by_id("widgetContributorParse_dc_authority_people").click()


    import pdb; pdb.set_trace()


if __name__ == '__main__':
    driver = get_driver(debug=True, driver='chrome')

    #login(driver)
    #upload(driver, {'title': 'my title',
    #                'keywords': ['key1', 'key2'],
    #                'abstract': 'my abstract',
    #                'authors': ['Attilio Andreazza', 'Leonardo Carminati']})
    upload_from_doi(driver, None)