import streamlit as st
import pandas as pd
import sqlite3
import re
import panel as pn

conn = sqlite3.connect("nbaDatasets/nba_database.db")

teams_df = pd.read_sql_query("""
                             SELECT 
                                t.team_id,
                                t.team_displayName,
                                t.conference_id
                             FROM 
                                Teams t
                             """, conn)

seasonSched = pd.read_sql_query("""
                            SELECT 
                                *
                            FROM 
                                Schedule s
                            WHERE
                                s.event_season = 2025
                             """, conn)


query = """
SELECT 
    t.team_displayName AS Team,
    d.division_name AS Division,
    d.conference_name AS Conference,
    SUM(CASE 
        WHEN s.home_id = t.team_id AND s.home_score > s.away_score THEN 1
        WHEN s.away_id = t.team_id AND s.away_score > s.home_score THEN 1
        ELSE 0 END) AS Wins,
    SUM(CASE 
        WHEN s.home_id = t.team_id AND s.home_score < s.away_score THEN 1
        WHEN s.away_id = t.team_id AND s.away_score < s.home_score THEN 1
        ELSE 0 END) AS Losses,
    SUM(CASE 
        WHEN s.home_id = t.team_id AND s.home_score > s.away_score THEN 1
        ELSE 0 END) AS HomeWins,
    SUM(CASE 
        WHEN s.home_id = t.team_id AND s.home_score < s.away_score THEN 1
        ELSE 0 END) AS HomeLosses,
    SUM(CASE 
        WHEN s.away_id = t.team_id AND s.away_score > s.home_score THEN 1
        ELSE 0 END) AS AwayWins,
    SUM(CASE 
        WHEN s.away_id = t.team_id AND s.away_score < s.home_score THEN 1
        ELSE 0 END) AS AwayLosses,
    ROUND(
        CAST(SUM(CASE 
            WHEN s.home_id = t.team_id AND s.home_score > s.away_score THEN 1
            WHEN s.away_id = t.team_id AND s.away_score > s.home_score THEN 1
            ELSE 0 END) AS FLOAT) /
        (SUM(CASE 
            WHEN s.home_id = t.team_id OR s.away_id = t.team_id THEN 1
            ELSE 0 END)),
    3) AS WinPercentage
FROM 
    Teams t
JOIN 
    Divisions d ON t.conference_id = d.division_id
JOIN 
    Schedule s ON t.team_id = s.home_id OR t.team_id = s.away_id
WHERE 
    s.status_completed = 1 AND s.event_season = 2025
GROUP BY 
    t.team_id
ORDER BY 
    WinPercentage DESC, Wins DESC, Losses ASC;
"""





standings_df = pd.read_sql_query(query, conn)

standing_tabs = ['All'] + list(standings_df['Conference'].unique())

conference_tabs = st.tabs(standing_tabs)
for index, tab in enumerate(conference_tabs):
    with tab:
        conference_selected = standing_tabs[index]
        if index == 0:
            division_tabs = ['All'] + list(standings_df['Division'].unique())
        else:
            division_tabs = ['All'] + list(standings_df[standings_df['Conference'] == conference_selected]['Division'].unique())

        for i, sub_tab in enumerate(st.tabs(division_tabs)):
            with sub_tab:
                division_selected = division_tabs[i]
                if conference_selected != 'All':
                    if division_selected != 'All':
                        display_standings_df = standings_df[(standings_df['Conference'] == conference_selected) & (standings_df['Division'] == division_selected)]
                    else:
                        display_standings_df = standings_df[(standings_df['Conference'] == conference_selected)]
                else:
                    if division_selected != 'All':
                        display_standings_df = standings_df[(standings_df['Division'] == division_selected)]
                    else:
                        display_standings_df = standings_df
                
                st.dataframe(display_standings_df, hide_index=True, use_container_width=True)







conn.close()