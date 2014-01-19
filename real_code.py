"""command line utility which automatically googles for today's date
and prints out URLs of the first page of search results."""
import datetime
import requests
from bs4 import BeautifulSoup
from urlparse import urlparse, parse_qs

# "Sunday, January 1st 2014"
# since python date format does not support ordinal numbers (1st, 2nd, 3rd,
# etc.) we calculate that seperately and merge it in with .format()
DATE_SEARCH_FORMAT = r'%A %B {ordinal_day} %Y'

# oddly, strftime() doesn't have this built in. It's a bit of a pain because
# the teens are an exception, which means it's easier to list out the 7
# exceptions between 1 and 31 then to implement the full rule.
ORDINAL_SUFFIXES = {1:"st", 2:"nd", 3:"rd", 21:"st", 22:"nd", 23:"rd", 31:"st"}

def format_date_for_search(date):
    """date is formated "Sunday, January 1st 2014" so that google will see the
    relevant parts."""
    ordinal_day = str(date.day) + ORDINAL_SUFFIXES.get(date.day, 'th')
    date_search = DATE_SEARCH_FORMAT.format(ordinal_day=ordinal_day)
    return date.strftime(date_search)


def format_today_for_search():
    """shortcut for formatting today's date for the search."""
    return format_date_for_search(datetime.date.today())


def google_for_today():
    """yields the URL of every result on the first page of a google search for
    today's date."""
    date = datetime.date.today()
    response = requests.get('http://google.com/search', params={
        'q':format_date_for_search(date)
    })

    # "handle" the error
    if response.status_code != 200:
        print response.headers
        print response.text
        raise ValueError("bad google")

    # parse the search results links out of the page
    google_soup = BeautifulSoup(response.content)
    search_results = google_soup.select('li.g h3.r a')

    for link in search_results:
        # strip off the google tracking link
        query_string = urlparse(link['href']).query
        urls = parse_qs(query_string).get('q')

        if urls:
            actual_url = urls[0]
            if actual_url.startswith('http'):
                yield actual_url


if __name__ == '__main__':
    for search_result in google_for_today():
        print search_result

