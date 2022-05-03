import numpy
import math
import sys
import os
from sys import exit
import csv
import argparse
from math import sqrt
import web_sourcing as ws
import email_sourcing as es
import console_output as c
from pyPI import pi
from datetime import datetime
from time import sleep
import date_conversion as dc
import pytz
import classes

debug = False


###STATION LIST###
BWS = 78016

###REGION CODES UWYO###
n_america = "naconf"

###ERDDAP INSTITUTIONS###
ERDDAP_BIOS = "bermuda_institute_of_ocean_sciences_"

###BERMUDA WPR CONSTANTS###
coefficient_A = -0.0034
coefficient_B = -1.17
y_intercept = 1027

###TIMEZONES###
time_zone = pytz.timezone('UTC')

###MULTIPLE CHOICE LISTS###
soundings_source_list = ["Bermuda Naval Station Kindley"]
temperature_type_list = ["T50m Layer Average", "Sea Surface"]
ocean_profile_source_list = ["Hydrostation S",
                             "Ocean Gliders",
                             "Dataman",
                             "Manual Override"]


###MISC###
program_location = "Bermuda"
s_region_gliders = classes.Region(31, 33, -65.5, -63.5)
ocean_profile_max_depth = 50
earliest_records = datetime(2007, 1, 1)
temp_data_sources = 3
csv_number_dp = 3


###SYSTEM ARGUMENTS###
parser = argparse.ArgumentParser()
parser.add_argument("-s", type=int, dest='date_digits',
                    help="Sounding date and time (format YYYYMMDDHH)")
parser.add_argument("-t", type=str, dest='t_profile',
                    choices=['t50', 'sst'], help="""Temperature profile 't50' or 'sst' """)
parser.add_argument("-p", type=float, dest='slp',
                    help="Sea level Pressure (mb)")
parser.add_argument("-o", type=str, dest='output_path', help="Output path")
args = parser.parse_args()


# validates integers
def validate_int(raw_input):
    try:
        int(raw_input)
        return True
    except ValueError:
        return False

# validates floats


def validate_float(raw_input):
    try:
        float(raw_input)
        return True
    except ValueError:
        return False

# validates boolean inputs


def validate_bool_input(y_or_n):
    if "y" in y_or_n.lower() or "yes" in y_or_n.lower():
        return True
    else:
        return False

# converts datetime format to year.fraction format


def to_year_fraction(date):
    return (float(date.strftime("%j"))-1) / 366 + float(date.strftime("%Y"))


def validate_date(year, month, day, hour):
    try:
        dt = datetime(year, month, day, hour)
        return True
    except ValueError:
        return False


def year_fraction_to_date(year_fraction):
    return dc.decimalYearGregorianDate(year_fraction, "datetime")


def check_date(dt):
    if dt > datetime.now():
        c.message("Cannot lookup data from the future, enter existing date")
        return False
    elif dt < earliest_records:
        c.message("Data records only exist from {0}, enter more recent date".format(
            earliest_records.strftime("%d/%m/%Y")))
    else:
        return True


def find_sounding_data(rq_datetime):
    data_present = False
    c.status("Finding atmospheric sounding reports")
    (UWYO_payload, timestamp) = ws.fetch_UWYO_data(n_america, BWS, rq_datetime)
    return UWYO_payload, timestamp


def find_T50_data_BIOS(rq_datetime):
    data_present = False
    rq_datetime_decimal = to_year_fraction(rq_datetime)
    c.status("Finding ocean temperature profile reports")
    # try:
    (payload, timestamp) = ws.fetch_BIOS_data(rq_datetime_decimal)
    # except:
    #     c.error("Bad connection to server")
    #     c.status("Restart program")
    #     quit()
    return (payload, timestamp)


def find_T50_data_BATS(rq_datetime):
    payload, timestamp = es.find_depth_temp_data(
        rq_datetime)
    return payload, timestamp


def select_ERDDAP_temperature_data(unsorted_list):
    return sorted(unsorted_list, key=lambda x: x[0], reverse=False)


def select_dataman_temperature_data(data):
    filtered_data = []
    for row in data:
        if float(row[7]) < 50:
            filtered_data.append(float(row[8]))
    return filtered_data

# calculates mean value of a sorted list


def calculate_weighted_mean(sorted_list):
    total = 0
    length = len(sorted_list)
    delta_depth = sorted_list[length - 1][0]
    c.status("Calculating average temperature for top {0}m".format(
        round(delta_depth, 1)))

    depth_step = sorted_list[0][0]
    product = sorted_list[0][1] * depth_step
    total += product

    for i in range(1, length - 1):
        depth_step = sorted_list[i][0] - sorted_list[i - 1][0]
        product = sorted_list[i][1] * depth_step
        total += product
    average_temperature = total / delta_depth

    return average_temperature


def calculate_mean_average(temperature_data):
    return numpy.mean(temperature_data)


def find_SST(temperature_data):
    return temperature_data[0]


def VMAX_quadratic(a, b, c):
    discriminant = (math.pow(b, 2)) - (4*a*c)
    top_positive = sqrt(discriminant) - b
    top_negative = 0 - (b + sqrt(discriminant))
    v1 = top_positive / (2*a)
    v2 = top_negative / (2*a)
    if v1 >= 0:
        return v1
    else:
        return v2

# converts dates given in digit form to date object


def get_datetime_from_digits(digits):
    str_digits = str(digits)
    year = int(str_digits[0:4])
    month = int(str_digits[4:6])
    day = int(str_digits[6:8])
    hour = int(str_digits[8:10])
    if validate_date(year, month, day, hour) == True:
        dt = datetime(year, month, day, hour)
        if check_date(dt) == True:
            return dt
        else:
            argument_error([dt])
    else:
        argument_error([str_digits])
    return None


def check_slp(slp):
    if slp > 0 and slp < y_intercept:
        return True
    else:
        return False


def get_slp(input_slp):
    if check_slp(input_slp) == True:
        return input_slp
    else:
        argument_error([input_slp])
    return None


def validate_path(output_path):
    if output_path.endswith(".csv"):
        return None
    else:
        argument_error([output_path])


def argument_error(bad_arguments):
    for argument in bad_arguments:
        print(str(argument) + " is not valid")
        exit()


def fetch_all_data():
    # gets requested datetime from system arguments
    requested_datetime = get_datetime_from_digits(args.date_digits)

    # gets sea level pressure from system args
    SLP = get_slp(args.slp)

    # gets temperature profile from system args
    temperature_profile = args.t_profile

    # validates output path
    validate_path(args.output_path)

    # retrieves atmospheric sounding data
    (sounding_payload, sounding_timestamp) = find_sounding_data(requested_datetime)

    # splits information into matrix array
    dataSetAR_sounding = UWYOtext_to_matrix(sounding_payload)

    # retrieves top 50m layer date for certain datetime
    (BIOS_payload, BIOS_timestamp) = find_T50_data_BIOS(requested_datetime)
    # sets timestamp from data recorded
    BIOS_ocean_profile_timestamp = year_fraction_to_date(BIOS_timestamp)

    (dataman_payload, dataman_ocean_profile_timestamp) = find_T50_data_BATS(
        requested_datetime)

    (ERDDAP_payload, ERDDAP_ocean_profile_timestamp) = ws.find_depth_temp_data(ERDDAP_BIOS,
                                                                               requested_datetime,
                                                                               s_region_gliders.min_lat,
                                                                               s_region_gliders.max_lat,
                                                                               s_region_gliders.min_long,
                                                                               s_region_gliders.max_long,
                                                                               ocean_profile_max_depth)
    # creates list of timestamps from data sources
    timestamps = [
        BIOS_ocean_profile_timestamp,
        ERDDAP_ocean_profile_timestamp,
        dataman_ocean_profile_timestamp]
    # sorts timestamps in data order (newest to oldest)
    timestamps.sort(reverse=True)

    if timestamps[0] == BIOS_ocean_profile_timestamp:

        temperature_data = select_BIOS_temperature_data(BIOS_payload)
        if temperature_profile == "t50":
            Temperature = calculate_mean_average(temperature_data[:, 6])
        elif temperature_profile == "sst":
            Temperature = find_SST(temperature_data[:, 6])
        else:
            argument_error([temperature_profile])
        ocean_profile_timestamp = BIOS_ocean_profile_timestamp
        ocean_profile_source = ocean_profile_source_list[0]

    elif timestamps[0] == ERDDAP_ocean_profile_timestamp:

        temperature_data = select_ERDDAP_temperature_data(ERDDAP_payload)
        if temperature_profile == "t50":
            Temperature = calculate_weighted_mean(temperature_data)
        elif temperature_profile == "sst":
            Temperature = temperature_data[0][1]
        else:
            argument_error([temperature_profile])
        ocean_profile_timestamp = ERDDAP_ocean_profile_timestamp
        ocean_profile_source = ocean_profile_source_list[1]

    elif timestamps[0] == dataman_ocean_profile_timestamp:

        temperature_data = select_dataman_temperature_data(dataman_payload)
        if temperature_profile == "t50":
            Temperature = calculate_weighted_mean(temperature_data)
        elif temperature_profile == "sst":
            Temperature = find_SST(temperature_data)
        else:
            argument_error([temperature_profile])
        ocean_profile_timestamp = dataman_ocean_profile_timestamp
        ocean_profile_source = ocean_profile_source_list[2]

    P = dataSetAR_sounding[:, 0]
    T = dataSetAR_sounding[:, 2]
    R = dataSetAR_sounding[:, 5]
    return Temperature, temperature_profile, SLP, P, T, R, requested_datetime, sounding_timestamp, ocean_profile_timestamp, ocean_profile_source

# converts text into data matrix (specific to UWYO)


def UWYOtext_to_matrix(text):
    dataSetLS = []
    rows = text.split("\n")
    for i in range(5, len(rows) - 2):
        stringValues = rows[i].split(" ")
        filteredValues = list(filter(None, stringValues))
        filteredValues = [float(j) for j in filteredValues]
        dataSetLS.append(filteredValues)
    return numpy.asarray(dataSetLS)

# selects temperature values from top 50m depth


def select_BIOS_temperature_data(text):
    dataSetLS = []
    rows = text.split("\n")
    for i in range(4, 28):
        stringValues = rows[i].split(" ")
        filteredValues = list(filter(None, stringValues))
        filteredValues = [float(j) for j in filteredValues]
        dataSetLS.append(filteredValues)
    return numpy.asarray(dataSetLS)


def output_csv(path, headers, data):
    if os.path.isfile(path) == True:
        with open(path) as csv_file:
            row_count = sum(1 for line in csv_file)
            if row_count == 0:
                with open(path, 'w', encoding='UTF8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(headers)
                    writer.writerow(data)
            else:
                with open(path, 'a', encoding='UTF8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(data)
    else:
        with open(path, 'w', encoding='UTF8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            writer.writerow(data)


def export_outputs(T50, t_profile, SLP, VMAX, PMIN, TO, rq_datetime, sounding_timestamp, ocean_profile_timestamp, ocean_profile_source):
    if t_profile == "t50":
        temp_type = 0
    elif t_profile == "sst":
        temp_type = 1
    else:
        temp_type = 0

    csv_headers = ["Date Run", "Date Input", "Potential Maximum Wind Velocity (m/s)", "Minimum Pressure At Eye (mb)", "Outflow Temperature (K)", "Temperature Recording Source",
                   "Temperature Recording Date", "Temperature Profile", "Ocean Temperature", "Atmospheric Sounding Station", "Atmospheric Sounding Date", "Sea Level Pressure (mb)", "", ""]
    csv_data = [datetime.now().strftime("%Y-%m-%d %H:%M"), rq_datetime.strftime("%Y-%m-%d %H:%M"), round(VMAX, csv_number_dp), round(PMIN, csv_number_dp),
                round(TO, csv_number_dp), ocean_profile_source, ocean_profile_timestamp, temperature_type_list[temp_type], round(T50, csv_number_dp), soundings_source_list[0], sounding_timestamp, SLP]
    path = args.output_path
    output_csv(path, csv_headers, csv_data)
    print("Output to CSV complete.")


def calculate_fancy_numbers(T50, SLP, P, T, R):
    c.status("Checking SSTs")
    c.status("Checking temperature profiles")
    c.status("Calculating minimum pressure at eye")
    (VMAX, PMIN, IFL, TO, LNB) = pi(T50, SLP, P, T, R)
    c.status(
        "Calculating maximum wind velocity using wind pressure relationship model")
    c.status("Calculating outputs")
    coefficient_C = y_intercept - PMIN
    corrected_VMAX = VMAX_quadratic(
        coefficient_A, coefficient_B, coefficient_C)
    c.message("Process complete.")
    return corrected_VMAX, PMIN, IFL, TO, LNB


def run_main():

    (T50, t_profile, SLP, P, T, R, rq_datetime, sounding_timestamp,
     ocean_profile_timestamp, ocean_profile_source) = fetch_all_data()
    (VMAX, PMIN, IFL, TO, LNB) = calculate_fancy_numbers(T50, SLP, P, T, R)

    export_outputs(T50, t_profile, SLP, VMAX, PMIN, TO, rq_datetime,
                   sounding_timestamp, ocean_profile_timestamp, ocean_profile_source)


run_main()
