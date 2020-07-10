import csv
import json
import re

import click
import requests
from bs4 import BeautifulSoup

('\n'
 'Variable declaration\n'
 '@DEFAULT_URL\n'
 '@URL_FIELDS\n'
 '@dicionario\n'
 '@letter_href_dict\n'
 '@fieldnames\n'
 '@count\n')

session = requests.Session()
DEFAULT_URL = "http://www.portaldalinguaportuguesa.org"
URL_fields = "/index.php?action=syllables&act=list"
fieldnames = ["word", "division", "syllables", "morphology"]
dicionario = {}
letter_href_dict = {}


'''
Function declaration
'''


def get_count():
    global count
    return count

count = 0


def inc_counter(val):
    global count
    count += val


def build_url(fields):
    return DEFAULT_URL+fields


def get_page(url):
    return session.get(url).text


def get_main_table(soup_object):
    return soup_object.find('table', {'name': 'rollovertable'})


def get_letters_table(soup_object):
    return soup_object.find('table', {'name': 'maintable'})


def get_table_lines(table_object):
    return table_object('td', {'title': 'Palavra'})


def get_table_rows(table_object):
    return table_object.findAll('tr')


def file_put_contents(format, fp, contents):
    if format == 'csv':
        writer = csv.DictWriter(fp, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"', fieldnames=fieldnames)
        for row in contents:
            writer.writerow(row)
        fp.flush()

    elif format == 'json':
        fp.write(json.dumps(contents, encoding='utf-8', ensure_ascii=False, indent=2, sort_keys=True))


def parse_href(element):
    return element['href']


def next_page(element):
    if check_for_next(element):
        href = list(map(parse_href, element.findAll('a', href=True)))
        # Debug:
        # print href
        return href[len(href) - 1]  # always return last element
    return False


def check_for_next(element):
    text = ''.join(element.findAll(text=True))
    # print text.replace(";", " ").replace(",", " ").split()
    if "seguintes" in text.lower():
        return True
    #elif "anteriores" in text.lower():
    else:
        return False
    return False


def count_syllable(div_word):
    pattern = re.compile('[-·]')
    s = pattern.findall(div_word)
    return 1 + len(s)


def parse_string(s):
    # add only text
    text = ''.join(s.findAll(text=True))
    # head = word
    # word's morphology in between '()'
    # head will always contain the word or the syllabic division
    head, sep, tail = text.partition(" (")
    # store text in between ()
    h, s, t = tail.partition(")")
    if len(h):
        return head.strip("\n"), h.strip("\n")
    return head.strip("\n")
    # return text.strip()


def add_to_letter_dict(keys, vals):
    for enum in range(0, len(keys)):
        letter_href_dict[keys[enum]] = vals[enum]


def add_to_dict(index, key, val, syl_count):
    dicionario[index] = (key, val, syl_count)


def find_letters_url(row_object):
    for row in row_object:
        # find all available letters
        data = list(map(parse_string, row.findAll('td')))
        # print data
        # find all hrefs to all letters
        href = list(map(parse_href, row.findAll('a', href=True)))
        # print str(data) + '@' + str(href)
        add_to_letter_dict(data, href)


def find_words(rows):
    # fieldnames : morphology string not implemented yet
    tmp = []
    for row in rows:
        data = list(map(parse_string, row.findAll('td')))
        # DEBUG:
        # print str(i) + ' ' + data[0] + ' @ ' + data[1]
        counter = count_syllable(data[1])
        # add_to_dict(i, data[0], data[1], count)
        tmp.append({"word": data[0][0],
                    "division": data[1],
                    "syllables": counter,
                    "morphology": data[0][1]})
    return tmp


def char_range(c1, c2):
    """Generates the characters from `c1` to `c2`, inclusive."""
    for c in range(ord(c1), ord(c2)+1):
        yield chr(c)


def parse(url_fields, current_letter, end_letter, fp, format, verbose):
    next_ = False
    soup = BeautifulSoup(get_page(DEFAULT_URL + url_fields), "lxml")
    next_link = soup.find('p', {'style': "color: #666666;"})
    if next_link:
        next_ = next_page(next_link)
    main_table = get_main_table(soup)
    # line = get_table_lines(main_table)
    rows = get_table_rows(main_table)[1:]  # [1:] to ignore table headers
    content = find_words(rows)  # content of all rows inside "rollover table"
    if verbose:
        print("writing to file")
    file_put_contents(format, fp, content)
    if next_:
        if verbose:
            print("current URL: "+next_)
        # stat char <- next_
        # parse all instances of words for a given letter
        parse(next_, current_letter, end_letter, fp, format, verbose)
    else:  # in case there are no more 'seguinte'/'next' links to follow
        if verbose:
            print("current URL: "+url_fields)
        inc_counter(1)
        print("end of scraping letter: " + current_letter)
        # move on to different letter/char
        next_char = chr(ord(current_letter) + 1)
        return next_char


def scrape_page(url_fields, start_letter, end_letter, fp, format="csv", verbose=False):

    # only useful on 1st iteration
    # init BeautifulSoup object
    soup = BeautifulSoup(get_page(DEFAULT_URL + url_fields), "lxml")

    # static table for available chars
    letter_table = get_letters_table(soup)

    # static table row with available chars
    letter_row = get_table_rows(letter_table)
    find_letters_url(letter_row)

    # for every letter that user wants
    # debug:
    # range_ = ''.join(char_range(start_letter, end_letter))
    # print range

    for letter in char_range(start_letter, end_letter):
        if letter.lower() in letter_href_dict:  # if available in website

            if verbose:
                print(("Starting letter: " + start_letter + ", on my way to: " + end_letter))

            url_fields = letter_href_dict.get(letter.lower())
            parse(url_fields, letter, end_letter, fp, format, verbose)  # parse all words for a given letter
        else:
            continue_letter = chr(ord(letter) + 1)  # try to use next word in alphabet
            print("URL not found for letter: " + letter)
            print("Continuing my job @ letter: " + continue_letter + "^.^")
            # restart with different start letter
            scrape_page(URL_fields, continue_letter, end_letter, fp, format, verbose)
        print("Scraped " + str(get_count()) + " letters")

    print("\n" \
          "****************************\n" \
          "* Scrapples job is done :) *\n" \
          "****************************\n")


@click.command()
@click.option("--start", default="a", help="Start letter, default A")
@click.option("--end", default="z", help="End letter, default Z")
@click.option("--format", default="csv", help="Define output format -> csv(default) or JSON")
@click.option("--outfile", type=click.Path(), help="Path to specific file")
@click.option("--verbose", is_flag=True, help="Print useful? information while executing")
def main(start, end, format, verbose, outfile):

    if not outfile and format == "json":
        outfile = "dict-silabas-scraper.json"
    elif not outfile and format == "csv":
        outfile = "dict-silabas-scraper.csv"
    if not start and not end:
        start = 'a'
        end = 'z'
    elif not end:
        end = 'z'
    elif not start:
        start = 'a'

    if verbose:
        print("\n" \
              "I will be expressive")
        print("Destination file: "+outfile)
        print("Format: "+format)
        print("Range of scrape, from "+ start + " to " + end)
        print("\n")

    fp = open(outfile, 'w', newline='', encoding='utf-8')
    scrape_page(URL_fields, start, end, fp, format, verbose)
    fp.close()


if __name__ == "__main__":
    main()
