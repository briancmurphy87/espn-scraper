from bs4 import BeautifulSoup
from urllib.request import urlopen

import requests
import json

import numpy as np
import pandas as pd

'''
url examples: 
main page with all teams: 
https://www.espn.com/mens-college-basketball/teams

the duke men's basketball roster (selected from the above url): 
https://www.espn.com/mens-college-basketball/team/roster/_/id/150

'''




def get_url_of_team(_team_espn_id):
    assert isinstance(_team_espn_id, int)
    assert _team_espn_id > 0
    return "https://www.espn.com/mens-college-basketball/team/roster/_/id/{}".format(_team_espn_id)


def get_content_from_soup(_url):
    assert isinstance(_url, str)
    assert _url.startswith("https://www.espn.com/mens-college-basketball/team/roster")

    page = urlopen(_url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    # return the portion of html output that contains athlete roster
    # (b/c of the clutter on espn's page this is nearly impossible to navigate to programmatically)
    return soup.find('body').findAll('script')[0].text


def get_roster_from_html(_espn_team_id):

    espn_team_url = get_url_of_team(_espn_team_id)
    content = get_content_from_soup(espn_team_url)

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


def output_excel_file_name():
    return 'ncaa.rosters.mens_basketball'


def output_excel_file_path():
    return '{}.{}'.format(output_excel_file_name(), excel_file_extentsion())


def do_scrape_for_school(_school, _espn_team_id):

    player_roster = get_roster_from_html(_espn_team_id)
    assert isinstance(player_roster, list)

    # build a data frame for this roster
    df_entries = []

    # define the roster attributes we wish to include in output
    html_roster_keys = ["name", "jersey", "position", "experience", "height", "weight", "birthDate", "birthPlace"]

    for player_entry in player_roster:
        # add player entry into output data frame
        df_entry = dict()
        for key in html_roster_keys:
            if key not in player_entry:
                assert key in ["birthPlace", "jersey", "height", "weight"], key
            else:
                df_entry[key] = player_entry[key]
            df_entries.append(df_entry)
        # df_entries.append({key: player_entry[key] for key in html_roster_keys})

    # finally, init data frame
    df = pd.DataFrame(df_entries)[html_roster_keys]
    # add a header for the school
    df.loc[:, 'school'] = _school

    # then output to excel
    output_file_path = output_excel_file_path()

    # write to excel
    with pd.ExcelWriter(output_file_path, engine=excel_writer_engine(), mode='a') as excel_writer:
        # write school sheet
        df.to_excel(excel_writer, sheet_name=_school)

    print('scraping complete')


def do_scrape():

    # read team mappings
    team_mappings_file_name = 'espn_team_mappings'
    # TODO: xlsx failing b/c of dependency issue ? just use csv
    # team_mappings_df = pd.read_excel(open('espn_team_mappings.xlsx', 'rb'), sheet_name='espn_team_mappings')
    team_mappings_df = pd.read_csv('{}.csv'.format(team_mappings_file_name))
    assert isinstance(team_mappings_df, pd.DataFrame)
    assert not team_mappings_df.empty
    team_mappings_df['EspnID'] = team_mappings_df['EspnID'].astype(int)

    # index entries from mappings to test
    start_index = 0
    finish_index = 24
    current_index = start_index
    while current_index <= finish_index:
        school = team_mappings_df.iloc[current_index]['School']
        school = school.strip()

        espn_id = team_mappings_df.iloc[current_index]['EspnID']
        assert np.issubdtype(espn_id, np.integer)
        assert espn_id > 0
        espn_id = int(espn_id)

        print("current_index[{}] school[{}] espn_id[{}]".format(current_index, school, espn_id))

        # do scrape for school
        do_scrape_for_school(school, espn_id)

        # next iter
        current_index += 1

    print('all done')


def consolidate_all_rosters():

    # read from excel
    in_file_path = output_excel_file_path()
    reader = pd.read_excel(in_file_path, engine=excel_writer_engine(), sheet_name=None)
    # should return a dict where
    # <key=school, value=roster df>
    # -> produce a consolidated df for all roster info across all schools
    consolidated_df = pd.concat(reader.values())
    # drop this garbage column
    cols_to_remove = [item for item in consolidated_df.columns.tolist() if 'Unnamed' in item]
    if cols_to_remove:
        consolidated_df.drop(cols_to_remove, axis=1, inplace=True)

    # TODO:
    # jersey (player #) is double-type b/c some players did not have numbers on website

    output_file_name = '{}.all'.format(output_excel_file_name())
    output_file_path = '{}.{}'.format(output_file_name, excel_file_extentsion())
    with pd.ExcelWriter(output_file_path, engine=excel_writer_engine()) as excel_writer:
        consolidated_df.to_excel(excel_writer, sheet_name='ALL')

    print('finished with fn: consolidate_all_rosters')


if __name__ == '__main__':
    # do_scrape()
    consolidate_all_rosters()