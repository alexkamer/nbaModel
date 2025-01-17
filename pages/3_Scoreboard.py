import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import sqlite3
import re
import panel as pn
import httpx
from datetime import datetime, timedelta


dayCol1, dayCol2 = st.columns([1,5])
with dayCol1:
    day_selected = st.date_input(label='Select a date:', value="today")
day_selected = day_selected.strftime("%Y%m%d")

scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?limit=1000&dates={day_selected}"
scoreboard_data = httpx.get(scoreboard_url).json().get('events',[])


def split_camel_case(word):
    # Use regex to split at transitions from lowercase to uppercase
    return " ".join(re.sub(r'([a-z])([A-Z])', r'\1 \2', word).split()).title()


def display_stats(stat_list):
    """
    Display a list of stats with names and rankDisplayValues in markdown.
    
    Args:
        stat_list (list): A list of dictionaries, each with 'name' and 'rankDisplayValue' keys.
    """
    st.markdown("### Stats and Rankings")
    for stat in stat_list:
        name = stat.get('name', 'Unknown Stat')
        rank = stat.get('rankDisplayValue', 'N/A')
        # Check if the rank is within 1st to 5th
        if 'Tied' in rank:
            real_rank = rank.split('-')[1]
        else:
            real_rank = rank
        if real_rank in ['1st', '2nd', '3rd', '4th', '5th']:
            rank_display = f'<span style="color: green; font-weight: bold;">{rank}</span>'
        elif real_rank in ['6th', '7th', '8th', '9th', '10th', '11th', '12th', '13th', '14th', '15th']:
            rank_display = f'<span style="color: yellow; font-weight: bold;">{rank}</span>'
        elif real_rank == 'N/A':
            rank_display = stat.get('displayValue')
        else:
            rank_display = f'<span style="color: red; font-weight: bold;">{rank}</span>'
        
        st.markdown(f"- **{split_camel_case(name)}:** {rank_display}", unsafe_allow_html=True)



scoreboard_df = []
for event in scoreboard_data:
    time_obj = datetime.strptime(event.get('date',''), "%Y-%m-%dT%H:%MZ")
    adjusted_time = time_obj - timedelta(hours=6)

    start_date = adjusted_time.strftime('%Y-%m-%d')
    start_time = adjusted_time.strftime('%I:%M %p')
    competition_dict = event.get('competitions',[{}])[0]
    odds_dict = [_ for _ in competition_dict.get('odds',[]) if _.get('provider',{}).get('id') == '58']
    base_scoreboard_dict = {
        'event_id' : event.get('id'),
        'start_date' : start_date,
        'start_time' : start_time,
        'event_name' : event.get('name'),
        'event_shortName' : event.get('shortName'),
        'status_displayClock' : event.get('status',{}).get('displayClock'),
        'status_quarter' : event.get('status',{}).get('period'),
        'status_detail' : event.get('status',{}).get('type',{}).get('detail'),
        'status_state' : event.get('status',{}).get('type',{}).get('state'),
        'divisionCompetition' : competition_dict.get('conferenceCompetition'),
        'venue_id' : competition_dict.get('venue',{}).get('id')

    }
    if len(odds_dict) > 0:
        odds_dict = odds_dict[0]
        base_scoreboard_dict['odds_details'] = odds_dict.get('details')
        base_scoreboard_dict['spread'] = abs(odds_dict.get('spread'))

        for oc in ['open', 'current']:
            oc_dict = odds_dict.get(oc,{})

            base_scoreboard_dict[f"{oc}_overUnder"] = oc_dict.get('total',{}).get('american')

    ### Start with competition list tomorrow
    for competitor in competition_dict.get('competitors',[]):
        homeAway = competitor.get('homeAway')
        team_dict = competitor.get('team',{})

        base_scoreboard_dict[f"{homeAway}_id"] = team_dict.get('id')
        base_scoreboard_dict[f"{homeAway}_abbreviation"] = team_dict.get('abbreviation')
        base_scoreboard_dict[f"{homeAway}_displayName"] = team_dict.get('displayName')
        base_scoreboard_dict[f"{homeAway}_color"] = team_dict.get('color')
        base_scoreboard_dict[f"{homeAway}_alternateColor"] = team_dict.get('alternateColor')
        base_scoreboard_dict[f"{homeAway}_logo"] = team_dict.get('logo')
        base_scoreboard_dict[f"{homeAway}_score"] = competitor.get('score')
        base_scoreboard_dict[f"{homeAway}_seasonStats"] = competitor.get('statistics',[])
        base_scoreboard_dict[f"{homeAway}_record"] = competitor.get('records')
        base_scoreboard_dict[f"{homeAway}_leaders"] = competitor.get('leaders')




    scoreboard_df.append(base_scoreboard_dict)

st.dataframe(scoreboard_df)


st.title("Game Schedule")

for row in scoreboard_df:
    away_team = row['away_displayName']
    home_team = row['home_displayName']
    game_info = f"Time: {row['start_time']} - Date: {row['start_date']}"
    home_logo = row['home_logo']
    away_logo = row['away_logo']
    away_away_record = [_['summary'] for _ in row['away_record'] if _['type'] == 'road'][0]
    home_home_record = [_['summary'] for _ in row['home_record'] if _['type'] == 'home'][0]
    away_total_record = [_['summary'] for _ in row['away_record'] if _['type'] == 'total'][0]
    home_total_record = [_['summary'] for _ in row['home_record'] if _['type'] == 'total'][0]

    away_team_stats = row['away_seasonStats']
    home_team_stats = row['home_seasonStats']

    away_score = row['away_score']
    home_score = row['home_score']

    game_state = row['status_state']

    col1, col2, col3 = st.columns([2,3,2])

    # Left column (Away Team)
    with col1:
        st.markdown(f"""
        <div style="text-align: left;">
            <img src="{away_logo}" alt="{away_team} logo" style="width: 100px;">
            <h3>{away_team}</h4>
            <p>Overall Record: {away_total_record}</p>
            <p>Away Record: {away_away_record}</p>
            <p>Score: {away_score}</p>

        </div>
        """, unsafe_allow_html=True)

        with st.expander('Click to view team stats:'):
            display_stats(away_team_stats)
    
    # Middle column (Game Info)
    with col2:

        if game_state == 'pre':
            st.markdown(f"""
            <div style="text-align: center;">
                        <h4>Game Info</h4>
                        <p>{game_info}</p>
                        <p>Is Division Competition? {row['divisionCompetition']}</p>
                        <h5>Over Under</h5>
                        <p>Open: {row['open_overUnder']} --> Current: {row['current_overUnder']}</p>
                        <p>Spread: {row['odds_details']}</p>
            </div>
            """, unsafe_allow_html=True)


            if st.button(f"Click to view Pre-Game info for {row['event_name']}", use_container_width=True):
                st.switch_page("pages/viewPregame.py")




        elif game_state == 'post':
            st.markdown(f"""
            <div style="text-align: center;">
                        <h4>Game Info</h4>
                        <p>{game_info}</p>
                        <p>Is Division Competition? {row['divisionCompetition']}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Click to view Post-Game info for {row['event_name']}", use_container_width=True):
                st.write('hello')

        else:
            st.markdown(f"""
            <div style="text-align: center;">
                        <h4>Game Info</h4>
                        <p>{game_info}</p>
                        <p>Is Division Competition? {row['divisionCompetition']}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Click to view In-Game info for {row['event_name']}", use_container_width=True):
                ss['inGame_dict'] = row
                st.switch_page("pages/viewInGame.py")


    
    # Right column (Home Team)
    with col3:
        st.markdown(f"""
        <div style="text-align: right;">
            <img src="{home_logo}" alt="{home_team} logo" style="width: 100px;">
            <h3>{home_team}</h4>
            <p>Overall Record: {home_total_record}</p>
            <p>Home Record: {home_home_record}</p>
            <p>Score: {home_score}</p>

        </div>
        """, unsafe_allow_html=True)
        with st.expander('Click to view team stats:'):
            display_stats(home_team_stats)
    
    st.markdown("---")  # Add a horizontal divider between games