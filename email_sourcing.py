from datetime import datetime
from distutils.command.clean import clean
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
import datetime


from numpy import double, ma

# feeder email address
feeder_email_address = '"Samantha.Hallam@mu.ie"'

# email credentials
EMAIL = 'samantha.hallam.bats.data@gmail.com'
PASSWORD = 'bats.data'
SERVER = 'imap.gmail.com'

# email manipulation
delimiter = "Time(GMT), Day, Month, Year, Latitude, Longitude, Station Number, Depth(db), Temperature (degC), Salinity"

# logs into email
mail = imaplib.IMAP4_SSL(SERVER)
mail.login(EMAIL, PASSWORD)

# selects all emails from feeder email address
mail.select('inbox')
filters = "(FROM %s)" % feeder_email_address
status, data = mail.search(None, filters)
mail_ids = []

for block in data:
    mail_ids += block.split()


def extract_date_from_row(row):
    year = int(row[3])
    month = int(row[2])
    day = int(row[1])

    time = float(row[0])
    hours = int(time)
    minutes = int((time*60) % 60)
    seconds = int((time*3600) % 60)

    return datetime.datetime(year, month, day, hours, minutes, seconds)


def find_depth_temp_data(rq_datetime):
    return find_closest_data_batch(rq_datetime)


def find_closest_data_batch(rq_datetime):
    found = False
    closest_mail_id = 0
    # change to iterate from top to bottom
    for i in reversed(mail_ids):
        status, data = mail.fetch(i, '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_from = message['from']
                mail_subject = message['subject']
                if message.is_multipart():
                    mail_content = ''
                    for part in message.get_payload():
                        if part.get_content_type() == 'text/plain':
                            mail_content += part.get_payload(decode=True)
                else:
                    mail_content = message.get_payload(decode=True)
        mail_content_str = str(mail_content)
        # removes additional text from email
        chunks = mail_content_str.split(delimiter)
        try:
            data_chunks = chunks[1]
            # separates data string by line
            data_list = data_chunks.split('\\r\\n')
            data_list.remove('')
            data_list.remove('\'')

            data_list = list(filter(None, data_list))
            data_array = []

            # separates and cleans first line of data row
            row_list = data_list[0].split(',')
            for j in range(0, len(row_list)):
                row_list[j] = row_list[j].strip()

            # extracts datetime object from row
            extracted_date = extract_date_from_row(row_list)

            if (extracted_date < rq_datetime):
                for row in data_list:
                    row_list = row.split(',')
                    for j in range(0, len(row_list)):
                        row_list[j] = row_list[j].strip()
                    data_array.append(row_list)
                return data_array, extracted_date
        except:
            None
