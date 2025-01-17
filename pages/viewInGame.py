import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import sqlite3
import re
import panel as pn
import httpx
from datetime import datetime, timedelta
import time


from bs4 import BeautifulSoup
import asyncio



game_dict = ss['inGame_dict']

all_box_urls = {
    'Basketball': "https://www.nbabox.me/watch-baketball-online"
}

async def fetch_and_parse(client, box_name, url):
    """Fetch and parse the webpage."""
    response = await client.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    a_tags = soup.find_all('a')
    # Filter tags with "aria-controls" in them
    filtered_a_tags = [str(tag) for tag in a_tags if "aria-controls" in str(tag)]
    return box_name, filtered_a_tags

async def fetch_all_box_a_tags():
    """Main asynchronous function to fetch all URLs."""
    all_box_a_tags = {}
    async with httpx.AsyncClient() as client:
        # Create tasks for fetching all URLs
        tasks = [fetch_and_parse(client, name, url) for name, url in all_box_urls.items()]
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        # Populate the results into the dictionary
        for box_name, a_tags in results:
            all_box_a_tags[box_name] = a_tags
    return all_box_a_tags

@st.cache_data(show_spinner=True)
def get_cached_dataframe():
    """Fetch, parse, and cache the DataFrame."""
    all_box_a_tags = asyncio.run(fetch_all_box_a_tags())
    allBox_df = []

    for sport in all_box_a_tags:
        for tag in all_box_a_tags[sport]:
            game_name = tag.split('title="')[1].split('"')[0]
            href = tag.split('href="/')[1].split('"')[0]
            # href = f"{href.split('/')[1]}/{href.split('/')[0]}"
            href = f"{min(href.split('/'), key=len)}/{max(href.split('/'), key=len)}"

            try:
                start_date = tag.split('content="')[1].split('"')[0]
                # Parse the string into a datetime object
                start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
                # Subtract 6 hours
                start_date = start_date - timedelta(hours=6)
                # Convert back to string if needed
                start_date = start_date.strftime("%Y-%m-%dT%H:%M")
            except Exception as e:
                start_date = None
            allBox_df.append({
                'sport': sport,
                "game_name": game_name,
                'href': href,
                'start_date': start_date
            })

    allBox_df = pd.DataFrame(allBox_df)
    return allBox_df.sort_values(by='start_date', na_position='first')
# Fetch the cached DataFrame
allBox_df = get_cached_dataframe()

def format_start_date(row):
    if row["start_date"] is None:
        return "Live Television"
    return row["start_date"]
def extract_date_and_time_with_label(start_date):
    if start_date is None:
        return None, "Live Television"
    else:
        dt = datetime.fromisoformat(start_date)
        date = dt.strftime("%Y-%m-%d")  # Extract only the date
        time = dt.strftime("%I:%M %p")  # 12-hour format with AM/PM
        
        # Calculate relative day (Today, Tomorrow, etc.)
        today = datetime.now().date()
        game_date = dt.date()
        if game_date == today:
            day_label = "Today"
        elif game_date == today + timedelta(days=1):
            day_label = "Tomorrow"
        else:
            day_label = game_date.strftime("%A")  # Day of the week
        
        return date, f"{time} ({day_label})"

# Apply function to split start_date and add labels
allBox_df[["start_date", "start_time"]] = allBox_df["start_date"].apply(
    lambda x: pd.Series(extract_date_and_time_with_label(x))
)
allBox_df["display_date"] = allBox_df.apply(format_start_date, axis=1)
allBox_df_row = allBox_df[allBox_df['game_name'].str.contains(game_dict['away_displayName']) | allBox_df['game_name'].str.contains(game_dict['home_displayName'])]

def create_iframe_html(urls):
    iframe_html = f"""
        <style>
            .stApp {{
                background-color: black;
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(45%, 1fr));
                gap: 10px;
                width: 100%;
            }}
            .iframe-container {{
                position: relative;
                width: 100%;
                padding-bottom: 56.25%; /* 16:9 aspect ratio */
                height: 0;
                overflow: hidden;
            }}
            .iframe-container iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: 0;
            }}
        </style>
        <div class="grid-container">
        """

    for url in urls:
        iframe_html += f"""
        <div class="iframe-container">
            <iframe src='{url}' 
                    scrolling='no' 
                    allowfullscreen 
                    allowtransparency 
                    referrerpolicy='unsafe-url'>
            </iframe>
        </div>
        """

    iframe_html += "</div>"
    return iframe_html
# urls = [f"https://embedsports.me/{allBox_df_row['href'].iloc[0]}-{_}" for _ in range(1,4)]
urls = [f"https://embedsports.me/{game}-1" for game in [allBox_df_row['href'].iloc[0]]]


def get_inGame_Data(game_id):
    url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()

    game_data = []
    try:
        data = response.json()
        playerBoxscore_data = data.get('boxscore',{}).get('players',[])

        for team in playerBoxscore_data:
            team_name = team.get('team',{}).get('displayName')
            stats_dict = team.get('statistics',[{}])[0]

            key_names = stats_dict.get('names',[])

            for athlete in stats_dict.get('athletes',[]):
                base_athlete_dict = athlete.get('athlete',{})
                athlete_dict = {
                'Team' : team_name,
                'Name' : base_athlete_dict.get('displayName'),
                'Position' : base_athlete_dict.get('position',{}).get('abbreviation'),
                'isStarter' : athlete.get('starter'),
                'didNotPlay' : athlete.get('didNotPlay'),
                'ejected' : athlete.get('ejected')
                }
                for index, stat in enumerate(athlete.get('stats',[])):


                    athlete_dict[f"{key_names[index]}"] = stat

                # st.write(athlete_dict)
                game_data.append(athlete_dict)

        st.write(url)
        return game_data
    except:
        return game_data


streamCol1, streamCol2 = st.columns([2,1])
with streamCol1:
    stream_html = create_iframe_html(urls)
    st.markdown(stream_html, unsafe_allow_html=True)


with streamCol2:
    stats_placeholder = st.empty()
    for _ in range(5):  # Loop for real-time updates (stop condition should match your use case)
        with stats_placeholder.container():
            st.write("### Player Stats (Updating in Real-Time)")

            game_data = get_inGame_Data(game_dict['event_id'])
            st.dataframe(game_data)
        time.sleep(2)  # Simulate a 2-second delay for updates

st.dataframe(game_dict)
