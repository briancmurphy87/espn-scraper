from bs4 import BeautifulSoup
from urllib.request import urlopen

import requests
import json

import os
import numpy as np
import pandas as pd

'''
url examples: 
main page with all teams: 
https://www.espn.com/mens-college-basketball/teams

the duke men's basketball roster (selected from the above url): 
https://www.espn.com/mens-college-basketball/team/roster/_/id/150

'''


def get_espn_team_roster_url_pattern(_is_mens_basketball):
    assert isinstance(_is_mens_basketball, bool)
    return "https://www.espn.com/{}-college-basketball/team/roster/_/id".format('mens' if _is_mens_basketball else 'womens')


def get_url_of_team(_team_espn_id, _is_mens_basketball):
    assert isinstance(_team_espn_id, int)
    assert _team_espn_id > 0
    return '{}/{}'.format(
        get_espn_team_roster_url_pattern(_is_mens_basketball)
        , _team_espn_id
    )
    # return "https://www.espn.com/mens-college-basketball/team/roster/_/id/{}".format(_team_espn_id)


def get_content_from_soup(_url):
    assert isinstance(_url, str)
    # assert _url.startswith("https://www.espn.com/mens-college-basketball/team/roster")
    assert _url.startswith("https://www.espn.com/")
    assert '-college-basketball/team/roster' in _url

    page = urlopen(_url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    # return the portion of html output that contains athlete roster
    # (b/c of the clutter on espn's page this is nearly impossible to navigate to programmatically)
    return soup.find('body').findAll('script')[0].text


OTHER_SCHOOL_LOOKUPS = \
    {
        'Norfolk St.': 'Norfolk State'
        , 'Central Florida': 'UCF'
        , 'Washington St.': 'Washington State'
        , 'Iowa St.': 'Iowa State'
    }


def get_roster_from_html(_school, _espn_team_id, _is_mens_basketball):

    espn_team_url = get_url_of_team(_espn_team_id, _is_mens_basketball)
    content = get_content_from_soup(espn_team_url)
    school_lookup = _school if _school not in OTHER_SCHOOL_LOOKUPS else OTHER_SCHOOL_LOOKUPS[_school]
    assert school_lookup in content

    # have text of html portion that contains roster
    # athletes roster is a list where each entry is a dict of a player's attributes
    dict_opener = r'"athletes":'
    athletes_start_index = content.find(dict_opener) + len(dict_opener)
    trimmed_content = content[athletes_start_index:]
    trimmed_content = trimmed_content[:(trimmed_content.find("]")+1)]

    return json.loads(trimmed_content)


# b/c of https://stackoverflow.com/questions/65250207/pandas-cannot-open-an-excel-xlsx-file
def excel_writer_engine():
    return 'openpyxl'


def excel_file_extentsion():
    return 'xlsx'


def ncaa_descriptor():
    return 'ncaa'


def basketball_descriptor(_is_mens):
    assert isinstance(_is_mens, bool)
    return '{}_basketball'.format('mens' if _is_mens else 'womens')


def csv_espn_team_mappings_descriptor():
    return 'espn_team_mappings.complete'


def get_team_mappings_csv_file_name(_is_mens):
    return '{}.{}.{}'.format(ncaa_descriptor(), basketball_descriptor(_is_mens), csv_espn_team_mappings_descriptor())


def output_excel_file_name(_is_mens_basketball):
    return '{}.{}.rosters'.format(
        ncaa_descriptor()
        , basketball_descriptor(_is_mens_basketball)
    )


def output_excel_file_path(_is_mens_basketball):
    assert isinstance(_is_mens_basketball, bool)
    return '{}.{}'.format(
        output_excel_file_name(_is_mens_basketball)
        , excel_file_extentsion()
    )
    # return '{}.{}'.format(output_excel_file_name(), excel_file_extentsion())


def do_scrape_for_school(_school, _espn_team_id, _is_mens_basketball):
    assert isinstance(_school, str)
    assert isinstance(_espn_team_id, int)
    assert isinstance(_is_mens_basketball, bool)

    # get player roster
    player_roster = get_roster_from_html(_school, _espn_team_id, _is_mens_basketball)
    assert isinstance(player_roster, list)

    # build a data frame for this roster
    df_entries = []

    # define the roster attributes we wish to include in output
    if _is_mens_basketball:
        html_roster_keys = ["name", "jersey", "position", "experience", "height", "weight", "birthDate", "birthPlace"]
    else:
        # womens roster does not have weight
        html_roster_keys = ["name", "jersey", "position", "experience", "height", "birthDate", "birthPlace"]

    # there may be duplicate entries for a player in the roster
    for player_entry in player_roster:
        # add player entry into output data frame
        df_entry = dict()
        for key in html_roster_keys:
            key_not_found = key not in player_entry
            if key_not_found and key == 'jersey':
                df_entry['key'] = '0'
            elif key_not_found:
                # assert key in ["birthPlace", "jersey", "height", "weight"], key
                assert key in ["birthPlace", "height", "weight"], key
            else:
                df_entry[key] = player_entry[key]
        # end: inner for
        df_entries.append(df_entry)
    # end: outer for

    # reasonable bounds on roster size
    assert 8 <= len(df_entries) <= 22, len(df_entries)

    # finally, init data frame
    df = pd.DataFrame(df_entries)[html_roster_keys]
    # add a header for the school
    df.loc[:, 'school'] = _school

    # then output to excel
    output_file_path = output_excel_file_path(_is_mens_basketball)
    append_mode = os.path.exists(output_file_path)
    print('output_file_path[{}] append_mode[{}]'.format(output_file_path, append_mode))

    # write to excel
    excel_writer_mode = 'a' if append_mode else 'w'
    with pd.ExcelWriter(output_file_path, engine=excel_writer_engine(), mode=excel_writer_mode) as excel_writer:
        # write school sheet
        df.to_excel(excel_writer, sheet_name=_school)

    print('scraping complete')


def do_scrape(_is_mens_basketball):
    assert isinstance(_is_mens_basketball, bool)
    print('_is_mens_basketball[{}]'.format(_is_mens_basketball))

    # read team mappings
    team_mappings_file_name = get_team_mappings_csv_file_name(_is_mens_basketball)
    team_mappings_file_path = '{}.xlsx'.format(team_mappings_file_name)

    # TODO: DEBUG: EXPERIMENTAL
    team_mappings_df = pd.read_excel(team_mappings_file_path, engine=excel_writer_engine(), sheet_name='bracket-flat')
    assert isinstance(team_mappings_df, pd.DataFrame)
    assert not team_mappings_df.empty

    col_header_school = 'SCHOOL'
    col_header_espn_id = 'FINAL ID'

    # TODO: when i was using the top 25 rankings
    # team_mappings_df = pd.read_csv(team_mappings_file_path)
    # assert isinstance(team_mappings_df, pd.DataFrame)
    # assert not team_mappings_df.empty
    # team_mappings_df['EspnID'] = team_mappings_df['EspnID'].astype(int)

    # index entries from mappings to test
    start_index = 22
    finish_index = 32
    current_index = start_index
    while current_index <= finish_index:
        school = team_mappings_df.iloc[current_index][col_header_school]
        school = school.strip()

        espn_id = team_mappings_df.iloc[current_index][col_header_espn_id]
        if isinstance(espn_id, str):
            assert espn_id.strip().lower() == 'dne'
            print("SKIP: current_index[{}] school[{}] espn_id[{}]".format(current_index, school, espn_id))
            current_index += 1
            continue

        if not isinstance(espn_id, int):
            assert np.issubdtype(espn_id, np.integer)
            espn_id = int(espn_id)
        assert espn_id > 0

        print("current_index[{}] school[{}] espn_id[{}]".format(current_index, school, espn_id))

        # do scrape for school
        do_scrape_for_school(school, espn_id, _is_mens_basketball)

        # next iter
        current_index += 1

    print('all done')


def consolidate_all_rosters(_is_mens_basketball):
    assert isinstance(_is_mens_basketball, bool)

    # read from excel
    in_file_path = output_excel_file_path(_is_mens_basketball)
    print("reading from: {}".format(in_file_path))
    assert os.path.exists(in_file_path)

    # get reader
    reader = pd.read_excel(in_file_path, engine=excel_writer_engine(), sheet_name=None)

    # should return a dict where
    # <key=school, value=roster df>
    # -> produce a consolidated df for all roster info across all schools
    consolidated_df = pd.concat(reader.values())

    # drop garbage column(s)
    cols_to_remove = [item for item in consolidated_df.columns.tolist() if 'Unnamed' in item]
    if cols_to_remove:
        consolidated_df.drop(cols_to_remove, axis=1, inplace=True)

    # produce output file path
    output_file_name = '{}.all'.format(output_excel_file_name(_is_mens_basketball))
    output_file_path = '{}.{}'.format(output_file_name, excel_file_extentsion())
    print('output_file_path: {}'.format(output_file_path))
    assert not os.path.exists(output_file_path), "path already exists: {}".format(output_file_path)

    with pd.ExcelWriter(output_file_path, engine=excel_writer_engine()) as excel_writer:
        consolidated_df.to_excel(excel_writer, sheet_name='ALL')

    print('finished with fn: consolidate_all_rosters')


if __name__ == '__main__':
    is_mens_basketball = False
    do_scrape(is_mens_basketball)
    # consolidate_all_rosters(is_mens_basketball)