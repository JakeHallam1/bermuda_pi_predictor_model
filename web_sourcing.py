import console_output as c
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import time
import sys
from time import sleep

debug = True

BWS_t1_url = "http://www.weather.bm/climateReportHourly/climateReportHourly.asp#jsAnchor"


###CONSTANTS###

SEARCH_WINDOW_SOUNDINGS = 1  # hours
SEARCH_WINDOW_ERDDAP = 24  # hours
SEARCH_ITERATION_ERDDAP = 1  # hours


###GENERAL###

def check_for_content(soup):
    try:
        text = soup.text
        return text, True
    except AttributeError:
        return "", False


def get_text_from_URL(url):
    content = requests.get(url).text
    soup = BeautifulSoup(content, "lxml")
    return soup.text


def URL_check_404(URL):
    if requests.get(URL).status_code == 404:
        return False
    else:
        return True


###UWYO DATA###

def extract_UWYO_timestamp(content):
    words = content.split(" ")
    z_time = words[len(words) - 4]
    time = z_time[0:len(z_time) - 1]
    return int(time)


def get_url_content(url):
    requested_page = requests.get(url)
    content = requested_page.text
    present = True
    return content


def fetch_UWYO_data(rq_region, rq_station, rq_datetime):
    c.status("Requesting atmospheric sounding data from http://weather.uwyo.edu")
    initial_datetime = rq_datetime
    present = False
    while present != True:
        (url, timestamp) = build_UWYO_URL(
            rq_region, rq_station, initial_datetime)
        UWYO_content = get_url_content(url)
        UWYO_soup = BeautifulSoup(UWYO_content, "lxml")
        (payload, present) = check_for_content(UWYO_soup.pre)
        initial_datetime -= timedelta(hours=1, minutes=0)
    timestamp = timestamp.replace(timestamp.year, timestamp.month,
                                  timestamp.day, extract_UWYO_timestamp(UWYO_soup.h2.text), 0)
    return payload, timestamp


def build_UWYO_URL(region, station, dt):
    root = "http://weather.uwyo.edu/cgi-bin/sounding?"
    area = "region=" + region + "&"
    formatting = "TYPE=TEXT%3ALIST&"
    year_month = "YEAR=" + str(dt.year) + "&MONTH=" + \
        "{:0>2d}".format(dt.month) + "&"
    start_hour = int(dt.hour - SEARCH_WINDOW_SOUNDINGS)
    time_frame = "FROM=" + "{:0>2d}".format(dt.day) + "{:0>2d}".format(
        start_hour) + "&TO=" + "{:0>2d}".format(dt.day) + "{:0>2d}".format(dt.hour + 1) + "&"
    station = "STNM=" + str(station)
    return root + area + formatting + year_month + time_frame + station, dt


def fetch_BWS_data():
    BWS_t1_content = requests.get(BWS_t1_url).text
    BWS_t1_soup = BeautifulSoup(BWS_t1_content, "lxml")


###BIOS DATA###

# returns BIOS ocean temperature data from the web
def fetch_BIOS_data(rq_datetime):
    directory_URL = "http://batsftp.bios.edu/Hydrostation_S/prelim/ctd/?C=N;O=D"
    BIOS_content_list = requests.get(directory_URL).text
    BIOS_content_list_soup = BeautifulSoup(BIOS_content_list, "lxml")
    c.status(
        "Requesting ocean profile data from http://batsftp.bios.edu/Hydrostation_S")
    (webpage, present) = check_for_content(BIOS_content_list_soup)
    if present == False:
        c.message("Main directory at " + directory_URL + " missing...")
    (identified_URL, timestamp) = find_closest_dataset(
        identify_start_file(webpage), rq_datetime)
    BIOS_data_payload = requests.get(identified_URL).text
    return BIOS_data_payload, timestamp


def find_closest_dataset(start_file, rq_datetime):
    file_ID = int(start_file[0:5])
    file_ending = 1
    file_extention = start_file[7:11]

    extracted_datetime = 10000
    while extracted_datetime > rq_datetime:
        filename = str(file_ID) + "c" + str(file_ending) + file_extention
        url = construct_BIOS_dataset_URL(filename)
        if URL_check_404(url):
            extracted_datetime = extract_date_from_file(get_text_from_URL(url))
            while URL_check_404(url) and extracted_datetime < rq_datetime:
                closest_url = url
                extracted_datetime = extract_date_from_file(
                    get_text_from_URL(closest_url))
                closest_datetime = extracted_datetime
                file_ending += 1
                filename = str(file_ID) + "c" + \
                    str(file_ending) + file_extention
                url = construct_BIOS_dataset_URL(filename)
        file_ID -= 1
    return closest_url, closest_datetime


def identify_start_file(script):
    rows = script.split("\n")
    filtered_rows = list(filter(None, rows))
    top_line = filtered_rows[4].split(" ")
    target_file_name = ""
    for i in range(1, len(top_line[0])):
        target_file_name += top_line[0][i]
    return target_file_name


def extract_date_from_file(script):
    rows = script.split("\n")
    filtered_rows = list(filter(None, rows))
    top_line = filtered_rows[4].split(" ")
    top_line.remove("")
    return float(top_line[3])


def construct_BIOS_dataset_URL(filename):
    root = "http://batsftp.bios.edu/Hydrostation_S/prelim/ctd/"
    return root + filename

###ERDDAP DATA###


def find_depth_temp_data(institution, rq_datetime, min_latitude, max_latitude, min_longitude, max_longitude, max_depth):
    (filenames, timestamp) = find_relevant_files(institution, rq_datetime,
                                                 min_latitude, max_latitude, min_longitude, max_longitude)
    depth_temp = []
    for file in filenames:
        target_url = build_data_filter_url(
            file, rq_datetime, min_latitude, max_latitude, min_longitude, max_longitude, max_depth)
        page = requests.get(target_url)
        if page.status_code == 200:
            depth_temp += extract_depthTemperature(target_url)
        elif page.status_code == 404:
            print(
                "No dataset found for {0} meeting search criteria".format(file))
        else:
            print("Server error")
    return depth_temp, timestamp


def find_relevant_files(institution, rq_datetime, min_latitude, max_latitude, min_longitude, max_longitude):
    c.status("Requesting ocean profile data from https://gliders.ioos.us/erddap")
    dateset_found = False
    start_time = rq_datetime - timedelta(hours=SEARCH_WINDOW_ERDDAP)
    end_time = rq_datetime
    while dateset_found != True:

        target_url = build_file_filter_url(
            institution, start_time, end_time, min_latitude, max_latitude, min_longitude, max_longitude)
        (table_contents, present) = check_ERDDAP_records_exist(target_url)

        if present:
            filenames = extract_ERDDAP_foldernames(table_contents)
            dateset_found = True
        else:
            start_time = start_time - timedelta(hours=SEARCH_ITERATION_ERDDAP)
            end_time = end_time - timedelta(hours=SEARCH_ITERATION_ERDDAP)
            dateset_found = False
    return filenames, end_time


def build_file_filter_url(institution, start_time, end_time, min_latitude, max_latitude, min_longitude, max_longitude):
    url = ""
    ANY = "%28ANY%29"
    root = "https://gliders.ioos.us/erddap/search/advanced.html?"
    page_layout = "page=1&itemsPerPage=1000"
    search_bar = "&searchFor="
    protocol = "&protocol=tabledap"
    cdm_data_type = "&cdm_data_type=" + ANY
    institution = "&institution=" + institution
    ioos_catagory = "&ioos_category=%28ANY%29"
    keywords = "&keywords=" + ANY
    long_name = "&long_name=" + ANY
    standard_name = "&standard_name=" + ANY
    variable_name = "&variableName=" + ANY
    max_lat = "&maxLat=" + str(max_latitude)
    min_long = "&minLon=" + str(min_longitude)
    max_long = "&maxLon=" + str(max_longitude)
    min_lat = "&minLat=" + str(min_latitude)
    min_time = "&minTime=" + start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    max_time = "&maxTime=" + end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    url += root + page_layout + search_bar + protocol
    url += cdm_data_type + institution + ioos_catagory
    url += keywords + long_name + standard_name + variable_name
    url += max_lat + min_long + max_long + min_lat
    url += min_time + max_time
    url = url.replace("\n", "")
    return url


def build_data_filter_url(filename, rq_datetime, min_latitude, max_latitude, min_longitude, max_longitude, max_depth):
    start_time = rq_datetime - timedelta(days=SEARCH_WINDOW_ERDDAP)
    end_time = rq_datetime
    url = ""
    colon = "%3A"
    root = "https://gliders.ioos.us/erddap/tabledap/{}.htmlTable?".format(
        filename)
    # shows time, latitude, longitude, depth and temperature
    variables = "time%2Clatitude%2Clongitude%2Cdepth%2Ctemperature"

    time_constraints = ""
    time_constraints += "&time>=" + start_time.strftime("%Y-%m-%d") + "T"
    time_constraints += start_time.strftime("%H") + colon + start_time.strftime(
        "%M") + colon + start_time.strftime("%S") + "Z"
    time_constraints += "&time<=" + end_time.strftime("%Y-%m-%d") + "T"
    time_constraints += end_time.strftime("%H") + colon + end_time.strftime(
        "%M") + colon + end_time.strftime("%S") + "Z"

    lat_constraints = "&latitude>=" + \
        str(min_latitude) + "&latitude<=" + str(max_latitude)
    long_constraints = "&longitude>=" + \
        str(min_longitude) + "&longitude<=" + str(max_longitude)

    depth_constraints = "&depth<=" + str(max_depth)

    url += root + variables + time_constraints + \
        lat_constraints + long_constraints + depth_constraints
    url = url.replace("\n", "")
    return url


def check_ERDDAP_records_exist(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    table_data = soup.find('table', class_='erd nowrap commonBGColor')
    if table_data != None:
        glider_IDs = []
        table_rows = table_data.find_all('tr')
        for tr in table_rows:
            td = tr.find_all('td')
            row = [i.text for i in td]
            glider_IDs.append(row)
        return glider_IDs, True
    else:
        return None, False


def extract_ERDDAP_foldernames(table):
    foldernames = []
    for i in range(1, int((len(table) - 1)), 2):
        foldernames.append(table[i][15])
    return foldernames


def strip_string(string):
    string_value = string.replace("\n", "")
    string_value = string.strip()
    return string_value


def string_to_float(string):
    try:
        float_string = float(string)
        return float_string
    except:
        return None


def extract_depthTemperature(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    table_data = soup.find('table', class_='erd commonBGColor nowrap')
    if table_data != None:
        table = []
        table_rows = table_data.find_all('tr')
        i = 0
        for tr in table_rows:
            td = tr.find_all('td')
            row = [strip_string(i.text) for i in td]
            table.append(row)
            if debug != True:
                sys.stdout.write("\r{0} ocean temperatures found.".format(i))
                sys.stdout.flush()
            i += 1

        c.status("Cleaning up data")
        table = filter(None, table)
        depth_temp = []
        i = 0
        for row in table:
            if not any(value == "" for value in row):
                depth_temp.append(
                    [string_to_float(row[3]), string_to_float(row[4])])
            else:
                if debug != True:
                    sys.stdout.write("\rRemoving {0} null points.".format(i))
                    sys.stdout.flush()
                i += 1
        print("")
        return depth_temp
    else:
        print("No dataset found at URL")
        return []
