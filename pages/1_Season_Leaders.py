import streamlit as st
import pandas as pd
import sqlite3
import re
import panel as pn

st.title("Current Season Leaders")

conn = sqlite3.connect("nbaDatasets/nba_database.db")

def split_camel_case(word):
    # Use regex to split at transitions from lowercase to uppercase
    return " ".join(re.sub(r'([a-z])([A-Z])', r'\1 \2', word).split()).title()

def fetch_player_stats(stat_name, minimum_games):
    conn = sqlite3.connect("nbaDatasets/nba_database.db")

    query = f"""
                            SELECT 
                                b.athlete_displayName,
                                COUNT(DISTINCT b.event_id) AS games_played,
                                SUM(b.{stat_name}) as total_{stat_name},
                                ROUND(AVG(b.{stat_name}),1) as {stat_name}PerGame
                            FROM
                                playerBoxScores b
                            JOIN
                                Schedule s ON b.event_id = s.event_id
                            WHERE
                                s.event_season = 2025 AND b.athlete_didNotPlay = 0
                            GROUP BY
                                b.athlete_displayName
                            HAVING
                                games_played > {minimum_games}
                                
                            """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df



# all_playerBoxScores = pd.read_sql_query("SELECT * FROM playerBoxScores", conn)
stat_categories = ["minutes","fieldGoalsMade","fieldGoalsAttempted","threePointFieldGoalsMade","threePointFieldGoalsAttempted","freeThrowsMade","freeThrowsAttempted","offensiveRebounds","defensiveRebounds","rebounds","assists","steals","blocks","turnovers","fouls","plusMinus","points"]
split_words = [split_camel_case(word) for word in stat_categories]

filter_col1, filter_col2 = st.columns([1,1])
with filter_col1:
    stat_selected = st.selectbox(label='Select the Stat to view:', options= split_words, index=0)
with filter_col2:
    minimum_games = st.select_slider(label="Select the minimum number of games played:", options=range(0,83))

df_stat_selected = stat_categories[split_words.index(stat_selected)]

playerBoxScores_thisYear = fetch_player_stats(df_stat_selected, minimum_games)


# st.dataframe(all_playerBoxScores.head())

st.dataframe(playerBoxScores_thisYear.sort_values(by=f"{df_stat_selected}PerGame", ascending=False), hide_index=True)

