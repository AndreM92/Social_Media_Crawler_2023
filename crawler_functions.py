from pytesseract import pytesseract
from PIL import Image

from datetime import datetime, timedelta
import time
import os

import re


# Say Hello
def printhello(name):
    print(f'Hello {name}')

# Start the driver and open a new page
def start_browser(webdriver, Service, chromedriver_path):
    # Open the Browser with a service object and an user agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'user-agent={user_agent}')
#    chrome_options.add_argument('--headless')
    service = Service(chromedriver_path)
    # Create a WebDriver instance using the Service and options
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    return driver

def go_to_page(driver, startpage):
    driver.get(startpage)
    time.sleep(3)
    # Click through the first Cookie Banner
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'ablehnen') or contains(text(), 'Ablehnen')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass

def start_pw_browser(sync_playwright, loginpage):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(loginpage)
    time.sleep(1)
    try:
        decline_cookies = page.get_by_role("button", name="Ablehnen")
        decline_cookies.click()
        time.sleep(1)
    except:
        pass
    return pw, browser, page

# Login functions and further cookie banner decline functions are in the individual files

########################################################################################################################
# Text parsing functions
# Get all text elements from the page
def get_visible_text(Comment, soup):
    def tag_visible(element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True
    texts = soup.find_all(string=True)
    visible_texts = filter(tag_visible, texts)
    pagetext = u" ".join(t.strip() for t in visible_texts)
    pagetext = re.sub('\n', ' ', pagetext).replace('\\xa0', ' ')
    pagetext = re.sub('\s+', ' ', pagetext).strip()
    return pagetext


# Extract text from elements
def extract_text(element):
    if element:
        if not isinstance(element,(str,int,float)):
            element = element.text.strip()
        element = str(element)
        if element == '':
            return element
        elif len(element) >= 1:
            repl_element = element.replace('\u200b','').replace('\xa0', ' ').replace('\\xa0', ' ').replace('\n',' ')
            new_element = re.sub('\s+', ' ', repl_element).strip()
            return new_element
        else:
            return element

def extract_number(element):
    if element:
        if not isinstance(element,(str,int,float)):
            element = element.text.strip()
        element = str(element)
        if len(element) < 1:
            return element
        element = str(re.sub(r'[^0-9]', '', element)).strip()
        try:
            element = int(element)
        finally:
            return element

def extract_big_number(element):
    if element:
        if not isinstance(element,(str,int,float)):
            element = element.text.strip()
        if not element:
            return element
        if len(element) == 0:
            return element
        element = str(element).replace('\n', ' ').replace('\xa0', ' ').replace('!', '').replace('#', '').replace('\s+',' ').strip()
        if 'M' in element:
            try:
                element = str(int(float(element.replace("Mio", " ").replace("M", " ").split(' ')[0].replace(",", ".").strip()) * 1000000))
            except:
                return element
        elif 'Tsd.' in element or str(element)[-1] == 'K':
            try:
                element = float(str(re.sub(r'[^0-9,]', '', element)).strip().replace(',','.')) * 1000
            except:
                return element
        elif ',' in element:
            if len(element.split(',')[1]) >= 3:
                element = element.replace(',','')
        else:
            element = element.split(' ')[0].replace('.','').replace(',','.').strip()
        if '.' in str(element):
            if str(element)[-2:] != '.0':
                try:
                    element = float(element)
                    return element
                except:
                    pass
            else:
                element = str(element).split('.')[0]
        element = re.sub(r'[^0-9]', '', element)
        try:
            element = int(element)
        except:
            pass
        return element

########################################################################################################################
# Filter functions
# Filter for company name parts
def get_company_keywords(company, row, col_list):
    comp_l1 = company.replace('-','').replace('.','').split()
    comp_l2 = company.replace('-','').replace('.','').split()
    comp_l3 = company.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').split()
    comp_l4 = company.split()
    comp_l = list(set(comp_l1 + comp_l2 + comp_l3 + comp_l4))
    comp_keywords_f = [str(e).lower() for e in comp_l if len(str(e).lower()) >= 3]
    comp_keywords = [e for e in comp_keywords_f if not '.mbh' in e and not 'gmbh' in e]
    sm_names = ['Facebook', 'Instagram']
    for n in sm_names:
        if n in col_list:
            addkey = str(row[n])
            sm_linkpart = n.lower() + '.com'
            if sm_linkpart in addkey:
                sm_name = addkey.split(sm_linkpart)[1].replace('/', '').strip().lower()
                comp_keywords.append(sm_name.lower())
    comp_keywords = list(set(comp_keywords))
    return comp_keywords

# Get all the links from the page
def get_links_and_soup(driver, BeautifulSoup):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    linklist = [str(l['href']) for l in soup.find_all('a', href=True) if ('http' in l['href'] and not 'google' in l['href'])]
    linklist.sort(key=len)
    return linklist, soup

def sm_filter(linklist):
    platforms = ['facebook.com', 'instagram.com', 'twitter.com', 'youtube.com', 'tiktok.com', 'linkedin.com']
    sm_links_all = [l for l in linklist if any(p in l for p in platforms)]
    not_profile = ['/post', 'hashtag', 'sharer','/status', 'photo/', 'photos', 'watch?', '/video/', 'discover', '.help',
                    'reels', 'story', 'explore', 'playlist', 'sharer', 'policy', 'privacy', 'instagram.com/p/',
                   '/tag/','/embed/']
    sm_links = [l for l in sm_links_all if not any(e in l for e in not_profile)]
    sm_links = list(set(sm_links))
    sm_links.sort(key=len)
    pos = 0
    for l in sm_links_all:
        if '/status' in l:
            l = l.split('/status')[0]
            if l not in sm_links:
                sm_links.insert(pos,l)
                pos += 1
    return sm_links

def order_sm_link_results(sm_links, comp_keywords, selected_platform):
    lp = selected_platform.lower() + '.com'
    other = [l for l in sm_links if not lp in l]
    sel_links = [l for l in sm_links if lp in l]
    main_links = [l for l in sel_links if any(k in l.lower() for k in comp_keywords)]
    result_list = [main_links, sel_links, other]
    results = []
    for e in result_list:
        if len(e) == 0:
            e = ''
        elif len(e) == 1:
            e = [0]
        results.append(e)
    return results

########################################################################################################################
# Date functions
# Extract the dates
def getDates(dt_str):
    # Date Dictionaries
    mDictEng = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, \
                'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
    mDictGer = {'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, \
                'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12}
    datelist = []
#    pattern_std = r'\b(?:[1-9]|1\d|2[0-4]) Std\.\b'
#    pattern_std = r'(\d+ Std)\b'
    pattern_std = r'\b\d+\s*Std\.\s*-?\s*@?\b'
    pattern_days = r'\b(?:\d+ Tage?)\b'

    # Convert the German month names to a regex pattern
    german_months_pattern = '|'.join(mDictGer.keys())
    # Define the regex pattern to match days and German month names (dd. Month) with optional time (um HH:MM)
    pattern_months = r'\b((?:(?:0?[1-9]|[12]\d|3[01])\. (' + german_months_pattern + r')(?: \d{4})?(?: um \d{1,2}:\d{2})?)|(?:(?:0?[1-9]|[12]\d|3[01])\. (' + german_months_pattern + r')))\b'
    # Use regex to find all occurrences of the pattern

    # Find the dates
    dates_first = re.findall(pattern_std, dt_str)
    dates_second = re.findall(pattern_days, dt_str)
    dates_months_d = re.findall(pattern_months, dt_str, re.IGNORECASE)
    dates_months = [date[0] for date in dates_months_d]
    # pattern_months = r'\b(?:\d{1,2}\. (?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)(?: \d{4})?|(?:(?:0?[1-9]|[12]\d|3[01])\. (?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember))(?: um \d{1,2}:\d{2}))\b'
###
    if 'std' in dt_str.lower() or 'min' in dt_str.lower():
        curr_dt = datetime.now().date()
        curr_dt_str = curr_dt.strftime('%Y-%m-%d')
        dates_first.append(curr_dt_str)
###
    datelist = [elem for sublist in [dates_first, dates_second, dates_months] if sublist for elem in sublist]
    return datelist

# Function to reformat the date
def dateFormat(d):
    if not d:
        return ''
    # Date Dictionaries
    mDictEng = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, \
                'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
    mDictGer = {'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, \
                'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12}
    day = datetime.now().day
    month = datetime.now().month
    year = datetime.now().year
    rest = ''
    if d[-1] == '.':
        d = d[:-1].strip()
    if 'Std' not in d:
        if 'Gestern' in d:
            day = datetime.now().day - 1
        elif 'Tag' in d:
            delta = int(re.sub(r'\D', '', d.split()[0]))
            day = datetime.now().day - delta
            if int(day) <= 0:
                new_date = datetime.now() - timedelta(days=delta)
                day = new_date.day
                month = new_date.month
                year = new_date.year
        else:
            date_ls = d.split('.')
            if len(date_ls) == 2:
                day, rest = date_ls
            date_ls2 = d.split(' ')
            if len(date_ls) == 3:
                month, day, rest = date_ls2
                day = day.replace(',','')
                for key, value in mDictEng.items():
                    if key in month.lower():
                        month = value
            for key,value in mDictEng.items():
                if key[:3] in rest.lower():
            #            month = '{:02d}'.format(value)
                    month = value
            for key,value in mDictGer.items():
                if key[:3] in rest.lower():
                    month = value
            if 'um' in rest:
                rest.split('um')[0]
            if '202' in rest or '201' in rest or '200' in rest:
                year = re.sub(r'\D', '', rest)[:4]
            if not str(year).isdigit():
                year = datetime.now().year

    day = str(day).replace('-','')
    day = str(day).zfill(2)
    month = str(month).zfill(2)
    date_string = f'{year}-{month}-{day}'
    dt_format = datetime.strptime(date_string, '%Y-%m-%d')
    return dt_format


def get_approx_date(crawl_date_dt, date_text):
    if not date_text or date_text == '':
        return [crawl_date_dt,'']
    if 'Tag' in date_text:
        delta = int(re.sub(r'[^0-9]', '', date_text))
        post_date_dt = crawl_date_dt - timedelta(days=delta)
    elif 'Woche' in date_text:
        delta = int(re.sub(r'[^0-9]', '', date_text))
        post_date_dt = crawl_date_dt - timedelta(weeks=delta)
    elif 'Monat' in date_text:
        delta = int(re.sub(r'[^0-9]', '', date_text))
        post_date_dt = crawl_date_dt - timedelta(days=delta*30)
        post_date_dt = post_date_dt.replace(day=1)
    elif 'Jahr' in date_text:
        delta = int(re.sub(r'[^0-9]', '', date_text))
        if delta == 1:
            post_date_dt = crawl_date_dt - timedelta(days=365)
            post_date_dt = post_date_dt.replace(day=1)
        else:
            post_date_dt = crawl_date_dt - timedelta(days=730)
            post_date_dt = post_date_dt.replace(day=1)
    else:
        post_date_dt = crawl_date_dt
    post_date = post_date_dt.strftime("%d.%m.%Y")

    return [post_date_dt, post_date]


########################################################################################################################
# Special Functions
#Take a screenshot and extract the text
def get_text_from_screenshot(driver, p_name):
    path_tes = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pytesseract.tesseract_cmd = path_tes
    forbidden_chars = ['|','.',',','-']
    for c in forbidden_chars:
        p_name = p_name.replace(c,'_')
    saving_path = os.getcwd() + '/Screenshots/' + p_name + '.png'
    driver.save_screenshot(saving_path)
    time.sleep(1)
    img = Image.open(saving_path)
    raw_text = pytesseract.image_to_string(img)
    scr_text = extract_text(raw_text)
    return scr_text


if __name__ == "__main__":
    pass