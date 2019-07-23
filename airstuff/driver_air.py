from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from selenium.common.exceptions import NoSuchElementException
import pickle
import time
import datetime
from enum import Enum
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bibtexparser").setLevel(logging.WARNING)
selenium_logger.setLevel(logging.WARNING)

URL_LOGIN = 'https://air.unimi.it/au/login'
URL_MYDSPACE = 'https://air.unimi.it/mydspace'
URL_SUBMIT = 'https://air.unimi.it/submit'


class ReturnValue(Enum):
    SUCCESS = 1
    DUPLICATE = 2


def get_driver(debug=False, driver='chrome'):
    WINDOW_SIZE = "1920,1080"

    if driver == 'chrome':
        logging.info('creating chrome')
        chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument("--incognito")
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
        driver.add_cookie({'name': cookie['name'], 'value': cookie['value']})
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

    logging.debug('you are log in')
    driver.find_element_by_xpath("//a[contains(text(), 'Ricerca per identificativo')]").click()
    element_doi = driver.find_element_by_id("identifier_doi")
    logging.debug('waiting for element to be visible')
    WebDriverWait(driver, 10).until(EC.visibility_of(element_doi))
    element_doi.clear()
    logging.debug('insert doi %s', info['doi'])
    element_doi.send_keys(info['doi'])
    driver.find_element_by_id("lookup_idenfifiers").click()

    # second page
    logging.debug('waiting for page with results from doi %s', info['doi'])
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "checkresult0"))).click()
    type_document_selector = driver.find_element_by_id("select-collection0")
    sel = Select(type_document_selector)
    sel.select_by_visible_text("01 - Articolo su periodico")
    logging.debug('ask to import selected records')
    driver.find_element_by_xpath("//button[contains(text(), 'Importa i record selezionati')]").click()

    # third page (licence)
    logging.debug('giving licence')
    driver.find_element_by_name("submit_grant").click()

    # check duplicate
    logging.debug('checking for duplicate box')
    duplicate_box_titles = driver.find_elements_by_id('duplicateboxtitle')
    
    if duplicate_box_titles:
        box = duplicate_box_titles[0]
        logging.debug('sleeping one second')
        time.sleep(1)  # FIXME: the problem is that the page is slow and this will be visible only if there will be a duplicate, which I don't know.
        is_displayed = box.is_displayed()
        if box.is_displayed():
            logging.info("the duplicate box is displayed")
            logging.warning('Trying to insert duplicate')
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'cancelpopup'))).click()
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, 'submit_remove'))).click()
            return ReturnValue.DUPLICATE

    # warning authors
    logging.info("checking if many authors box")
    many_authors = False
    try:
        driver.find_element_by_xpath("//h4[@class='modal-title' and contains(text(), 'Attenzione')]//../..//button[contains(text(), 'Chiudi')]").click()
        many_authors = True
    except NoSuchElementException:
        pass

    page = PageDescrivere2(driver)
    logging.debug('filling page Descrivere 2')
    if not page.get_title():
        logging.debug('set title %s', info['title'])
        page.set_title(info['title'])
    else:
        logging.debug('title already present')

    if not page.get_abstract():
        logging.debug('set abstract "%s"', info['abstract'][0]['summary'])
        page.set_abstract(info['abstract'][0]['summary'])
    else:
        logging.debug('abstract already present')
    if not page.get_keywords():
        keywords = [term["term"] for term in info["thesaurus_terms"] if "term" in term]
        logging.debug('set keywords %s', keywords)
        page.set_keywords(keywords)
    else:
        logging.debug('keywords already present')

    driver.find_element_by_id("widgetContributorEdit_dc_authority_people").click()
    authors_field = driver.find_element_by_id("widgetContributorSplitTextarea_dc_authority_people")
    authors_field.clear()
    authors_field.send_keys('; '.join(info['local_authors']))
    driver.find_element_by_id("widgetContributorParse_dc_authority_people").click()

    page.set_type_contribution()
    page.set_type_referee()
    page.set_type_research()
    page.set_type_publication()

    element_field = driver.find_element_by_id("dc_authority_academicField2000")
    element_field.clear()
    element_field.send_keys("FIS/01")
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//a[text()="Settore FIS/01 - Fisica Sperimentale"]'))).click()

    driver.find_element_by_xpath('//button[@value="Aggiungi ancora"]').click()

    element_field = driver.find_element_by_id("dc_authority_academicField2000")
    element_field.clear()
    element_field.send_keys("FIS/04")
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//a[text()="Settore FIS/04 - Fisica Nucleare e Subnucleare"]'))).click()

    page.next_page()

    page3 = PageDescrivere3(driver)

    if 'imprint' in info and info['imprint']['date']:
        date = datetime.datetime.fromisoformat(info['imprint']['date'])
        if page3.get_year():
            if int(page3.get_year()) != date.year:
                logging.warning('year is different %s != %s', page3.get_year(), date.year)
        else:
            page3.set_year(date.year)

        if page3.get_month():
            if (int(page3.get_month)) != date.month:
                logging.warning('month is different %s != %s', page3.get_month(), date.month)
        else:
            page3.set_month(date.month)
       
        if page3.get_day():
            if (int(page3.get_day()) != date.day):
                logging.warning('day is different %s != %s', page3.get_day(), date.day)
        else:
            page3.set_day(date.day)
        
    page3.set_pub()
    page3.set_rilevanza()
    page3.next_page()

    # page 4
    driver.find_element_by_name("submit_next").click()

    # page 5
    page5 = PageDescrivere5(driver)

    if page5.get_scopus():
        if page5.get_scopus() != info['scopus']:
            logging.warning("scopus reference are different %s != %s", info['scopus'], page5.get_scopus())
    else:
        logging.info('scopus information not found')
        page5.set_scopus(info['scopus'])

    if page5.get_wos():
        if page5.get_wos() != info['wos']:
            logging.warning("wos reference are different %s != %s", info['wos'], page5.get_wos())
    else:
        logging.info("wos information not found")
        page5.set_wos(info['wos'])

    page5.set_open()
    page5.set_url('')  # remove url since the automatic one link to the journal and not to the article
    page5.next_page()

    # page 6
    page6 = PageCarica6()
    page6.send_file(fn_pdf)
    page6.sito_docente(False)
    page6.next_page()

    # page 6/bis
    driver.find_element_by_name("submit_next").click()

    # page7
    driver.find_element_by_name("submit_next").click()
    
    return ReturnValue.SUCCESS


class Page:
    def __init__(self, driver):
        self.driver = driver

    def select_hidden(self, element, value):
        old_class = element.get_attribute('class')
        self.driver.execute_script("arguments[0].setAttribute('class', '')", element)
        sel = Select(element)
        sel.select_by_visible_text(value)
        self.driver.execute_script("arguments[0].setAttribute('class', '%s')" % old_class, element)


class PageDescrivere2(Page):
    def __init__(self, driver):
        super().__init__(driver)

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
        xpath = r'//label[text()="Abstract"]/..//textarea'
        textareas = self.driver.find_elements_by_xpath(xpath)

        for textarea in textareas:
            WebDriverWait(self.driver, 10).until(EC.visibility_of(textarea))
            text = textarea.text
            if text:
                return text

    def set_keywords(self, keywords):
        k = '; '.join(keywords)
        element_keywords = self.driver.find_element_by_id('dc_subject_keywords_id')
        element_keywords.clear()
        element_keywords.send_keys(k)

    def get_keywords(self):
        element_keywords = self.driver.find_element_by_id('dc_subject_keywords_id')
        return element_keywords.text

    def set_type_contribution(self):
        element_type_contribution = self.driver.find_element_by_xpath('//select[@name="dc_type_contribution"]')
        self.select_hidden(element_type_contribution, 'Articolo')

    def set_type_referee(self):
        element_type_referee = self.driver.find_element_by_xpath('//select[@name="dc_type_referee"]')
        self.select_hidden(element_type_referee, 'Esperti anonimi')

    def set_type_research(self):
        element_type_referee = self.driver.find_element_by_xpath('//select[@name="dc_type_research"]')
        self.select_hidden(element_type_referee, 'Ricerca di base')

    def set_type_publication(self):
        element_type_publication = self.driver.find_element_by_xpath('//select[@name="dc_type_publication"]')
        self.select_hidden(element_type_publication, 'Pubblicazione scientifica')

    def next_page(self):
        self.driver.find_element_by_name("submit_next").click()


class PageDescrivere3(Page):
    def __init__(self, driver):
        super().__init__(driver)

    def get_year(self):
        el = self.driver.find_element_by_name("dc_date_issued_year")
        return el.get_attribute('value')
    
    def set_year(self, year):
        el = self.driver.find_element_by_name("dc_date_issued_year")
        el.clear()
        el.send_keys(str(year))

    def get_day(self):
        el = self.driver.find_element_by_name("dc_date_issued_day")
        return el.get_attribute('value')

    def set_day(self, day):
        el = self.driver.find_element_by_name("dc_date_issued_day")
        el.clear()
        el.send_keys(str(day))

    def get_month(self):
        el = self.driver.find_element_by_name('dc_date_issued_month')
        val = el.get_attribute('value')
        if val == '-1':
            return None
        else:
            return int(val)

    def set_month(self, month):
        el = self.driver.find_element_by_name('dc_date_issued_month')
        sel = Select(el)
        sel.select_by_value(str(month))

    def set_pub(self):
        el = self.driver.find_element_by_xpath('//select[@name="dc_type_publicationstatus"]')
        self.select_hidden(el, 'Pubblicato')

    def set_rilevanza(self):
        el = self.driver.find_element_by_xpath('//select[@name="dc_type_circulation"]')
        self.select_hidden(el, 'Periodico con rilevanza internazionale')

    def next_page(self):
        self.driver.find_element_by_name("submit_next").click()


class PageDescrivere5(Page):
    def __init__(self, driver):
        super().__init__(driver)

    def get_scopus(self):
        els = self.driver.find_elements_by_xpath('//label[text()="Codice identificativo in banca dati"]/..//Select/option[@selected="selected"]')
        scopus_select = None
        for el in els:
            if el.text == 'Scopus':
                scopus_select = el
                break
        if not scopus_select:
            return None
        
        scopus_id = el.find_element_by_xpath('../../..//input[@class="form-control"]').get_attribute('value')
        if not scopus_id:
            return None
        return scopus_id

    def set_scopus(self, scopus_id):
        els = self.driver.find_elements_by_xpath('//label[text()="Codice identificativo in banca dati"]/..//Select/option[@selected="selected"]')
        scopus_selected = None
        for el in els:
            if el.text == 'Scopus':
                scopus_selected = el
                break
        if scopus_selected:
            scopus_element = scopus_selected.find_element_by_xpath('../../..//input[@class="form-control"]')
            scopus_element.clear()
            scopus_element.send_keys(scopus_id)
        else:
            el2 = els[0].find_element_by_xpath('../../../../../..//select[@name="dc_identifier_qualifier"]')
            sel = Select(el2)
            sel.select_by_value("scopus")
            el_field = el.find_element_by_xpath('../../../../../..//input[@name="dc_identifier_value"]')
            el_field.clear()
            el_field.send_keys(scopus_id)

    def get_wos(self):
        els = self.driver.find_elements_by_xpath('//label[text()="Codice identificativo in banca dati"]/..//Select/option[@selected="selected"]')
        isi_select = None
        for el in els:
            if el.text == 'ISI':
                isi_select = el
                break
        if not isi_select:
            return None
        
        isi_id = el.find_element_by_xpath('../../..//input[@class="form-control"]').get_attribute('value')
        if not isi_id:
            return None
        return isi_id

    def set_wos(self, isi_id):
        els = self.driver.find_elements_by_xpath('//label[text()="Codice identificativo in banca dati"]/..//Select/option[@selected="selected"]')
        isi_selected = None
        for el in els:
            if el.text == 'ISI':
                isi_selected = el
                break
        if isi_selected:
            isi_element = isi_selected.find_element_by_xpath('../../..//input[@class="form-control"]')
            isi_element.clear()
            isi_element.send_keys(isi_id)
        else:
            el2 = els[0].find_element_by_xpath('../../../../../..//select[@name="dc_identifier_qualifier"]')
            sel = Select(el2)
            sel.select_by_value("isi")
            el_field = els[0].find_element_by_xpath('../../../../../..//input[@name="dc_identifier_value"]')
            el_field.clear()
            el_field.send_keys(isi_id)            

    def next_page(self):
        self.driver.find_element_by_name("submit_next").click()

    def set_open(self):
        el = self.driver.find_element_by_xpath('//select[@name="dc_iris_checkpolicy"]')
        self.select_hidden(el, 'Aderisco')

    def set_url(self, url):
        el = self.driver.find_element_by_id("dc_identifier_url")
        el.clear()
        if url:
            el.send_keys(url)


class PageCarica6(Page):
    def __init__(self, driver):
        super().__init__(driver)

    def send_file(self, fn):
        el = self.driver.find_element_by_id("tfile")
        self.driver.execute_script('arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";', el)
        el.send_keys(fn)

    def sito_docente(self, value):
        el = self.driver.find_element_by_id('sitodoc')
        sel = Select(el)
        sel.select_by_value('true' if value else 'false')

    def next_page(self):
        self.driver.find_element_by_name("submit_upload").click()



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
    upload_from_doi(driver, {'doi': '10.1140/epjc/s10052-018-6374-z'})