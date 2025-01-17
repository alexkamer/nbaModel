import streamlit as st
import pandas as pd
import sqlite3


st.set_page_config(layout="wide")


conn = sqlite3.connect("nbaDatasets/nba_database.db")
existing_sched = pd.read_sql_query("SELECT * FROM Schedule", conn)
playerBoxScores_thisYear = pd.read_sql_query("""
                                             SELECT 
                                                b.athlete_displayName,
                                                SUM(b.points) as total_points
                                             FROM
                                                playerBoxScores b
                                             JOIN
                                                Schedule s ON b.event_id = s.event_id
                                             WHERE
                                                s.event_season = 2025
                                             GROUP BY
                                                b.athlete_displayName
                                                
                                             """, conn)



existing_sched = pd.DataFrame(existing_sched)
playerBoxScores_thisYear = pd.DataFrame(playerBoxScores_thisYear)
st.dataframe(playerBoxScores_thisYear)

st.dataframe(existing_sched)

conn.close()
