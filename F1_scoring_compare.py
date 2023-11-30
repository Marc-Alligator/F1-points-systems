# -*- coding: utf-8 -*-
"""
F1 scoring systems comparer by Marc Allerheiligen
Calculates how competitive a championship is with different points systems

inspired by article by 538:
https://fivethirtyeight.com/features/forget-last-years-finish-formula-one-is-drama-free-again/
"""

print("Setting user-defined parameters...")
'''Test Scoring Values override the correct value for the year.
        To allow the correct values to be used, assign them to None.
        Only the last assignment will be kept.'''
CURRENT_SCORING = [25,18,15,12,10,8,6,4,2,1]
CURRENT_SPRINT_SCORING = [8,7,6,5,4,3,2,1]
PRE_2022_SPRINT_SCORING = [3,2,1]

SIMPLEST_SCORING = [20-place for place in range(20)]

TEST_RACE_SCORING = CURRENT_SCORING
TEST_SPRINT_SCORING = CURRENT_SPRINT_SCORING
TEST_POINTS_FOR_FASTEST_LAP = 1

TEST_RACE_SCORING = SIMPLEST_SCORING
TEST_SPRINT_SCORING = PRE_2022_SPRINT_SCORING
TEST_POINTS_FOR_FASTEST_LAP = 0

TEST_RACE_SCORING = None
TEST_SPRINT_SCORING = None
TEST_POINTS_FOR_FASTEST_LAP = None

USE_538_CHAMPION_SCORING = False

year_range = None # so that while loop does not throw error
year_range = (2013, 2013)
year_range = (2003, 2022)

while year_range == None:
    first_year, last_year = "", ""
    while not first_year.isnumeric():
        first_year = input("What is the earliest year you would like to use data from? ")
    while not last_year.isnumeric():
        last_year  = input("What is the latest year you would like to use data from? ")
    try:
        year_range = (int(first_year), int(last_year))
    except:
        print("Try typing the numbers differently.200")
    
print("Parameters set.")

'''LIBRARIES'''
import pandas as pd
from tqdm import tqdm

RACE_SCORING_SYSTEMS = {
        (1950,1959):[8,6,4,3,2],
        (1960,1960):[8,6,4,3,2,1],
        (1961,1990):[9,6,4,3,2,1],
        (1991,2002):[10,6,4,3,2,1],
        (2003,2009):[10,8,6,5,4,3,2,1],
        (2010,9999):[25,18,15,12,10,8,6,4,2,1],
    }


print("Loading data...")
ALL_RACES = pd.read_csv("archive/races.csv")
ALL_DRIVERS = pd.read_csv("archive/drivers.csv")
ALL_RACE_RESULTS = pd.read_csv("archive/results.csv")
ALL_SPRINT_RESULTS = pd.read_csv("archive/sprint_results.csv")
ALL_STANDINGS = pd.read_csv("archive/driver_standings.csv")
print("Data done loading.")

print("Pre-processing data...")
first_year, last_year = year_range
ALL_RACES = ALL_RACES.where(ALL_RACES['year'] >= first_year).where(ALL_RACES['year'] <= last_year)#.dropna()
ALL_RACES['has sprint'] = ALL_RACES['sprint_date'].fillna(r'\N') != r'\N'
ALL_RACES['sprints so far'] = ALL_RACES.groupby('year')['has sprint'].cumsum()

print("Calculating fastest laps...")
ALL_RACE_RESULTS['fast lap rank'] = ALL_RACE_RESULTS.groupby('raceId')['fastestLapTime'].rank()

columns_to_drop = [column for column in ALL_RACES.columns if 'date' in column or 'time' in column]
#columns_to_drop.remove('date')
columns_to_drop.extend(['circuitId','url'])
for column in columns_to_drop:
    ALL_RACES = ALL_RACES.drop(column, axis = 1)

RESULTS_COLUMNS = ['resultId','raceId','driverId','position']
ALL_RACE_RESULTS = ALL_RACE_RESULTS[RESULTS_COLUMNS+['fast lap rank']]
ALL_SPRINT_RESULTS = ALL_SPRINT_RESULTS[RESULTS_COLUMNS]

def get_points(pos, scoring_system):
    if type(pos) not in [str,int]:
        pos = pos['position']
    if pos == r'\N':
        return 0
    if int(pos) > len(scoring_system): return 0
    return scoring_system[int(pos)-1]

def year_scoring_system(year):        
    year = int(year)
    # Race
    for time_range in RACE_SCORING_SYSTEMS.keys():
        first_year, last_year = time_range
        year_after = last_year + 1
        if year in range(first_year, year_after):
            scoring = RACE_SCORING_SYSTEMS[time_range]
    # Sprint
    if year > 2021:
        sprint_scoring = CURRENT_SPRINT_SCORING
    else:
        sprint_scoring = PRE_2022_SPRINT_SCORING
    
    # Fastest Lap
    points_for_fastest_lap = 1 if (year < 1959 or year > 2019) else 0
    
    # Test Scoring (override)
    if TEST_RACE_SCORING != None:
        scoring = TEST_RACE_SCORING
    if TEST_SPRINT_SCORING != None:
        sprint_scoring = TEST_SPRINT_SCORING
    if TEST_POINTS_FOR_FASTEST_LAP != None:
        points_for_fastest_lap = TEST_POINTS_FOR_FASTEST_LAP
    
    return (scoring, sprint_scoring, points_for_fastest_lap)

def build_race_points_columns(race_results, scoring_system):
    race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
    race_results  ['race points']     =   race_results.apply(get_points, args=[race_scoring],axis = 1)
        
    race_results['fast lap points'] = (race_results['fast lap rank'] == 1
                                            ) * (race_results['race points'] > 0
                                                 ) * points_for_fastest_lap
    return race_results

def build_sprint_points_column(sprint_results, scoring_system, cum_points = True):
    race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
    if len(sprint_results) > 0:
        sprint_results['sprint points'] = sprint_results.apply(get_points, args=[sprint_scoring],axis=1)
    else:
        sprint_results['sprint points'] = pd.Series(dtype = int)
    return sprint_results

if not USE_538_CHAMPION_SCORING:
    print("""Calculating mean points that would have been scored by historical champions 
          under different points systems""")
    LAST_RACES = ALL_RACES.sort_values('raceId',ascending = False).groupby('year').nth(0)
    END_OF_SEASON_STANDINGS = ALL_STANDINGS.merge(LAST_RACES)
    CHAMPIONS = END_OF_SEASON_STANDINGS.where(END_OF_SEASON_STANDINGS['position'] == 1).dropna()
    CHAMPIONS = CHAMPIONS.merge(ALL_RACES)[['driverId','year']]
    CHAMPION_MEAN_POINTS = dict() # year_of_scoring_system:mean
    previous_year_system = ()
    '''TODO: 
        calculate champion avg score using Pandas operations
        '''
    champ_race_results   =   ALL_RACE_RESULTS.merge(ALL_RACES).merge(CHAMPIONS)[['raceId','year','position','fast lap rank']]
    champ_sprint_results = ALL_SPRINT_RESULTS.merge(ALL_RACES).merge(CHAMPIONS)[['raceId','year','position']]
    for year in tqdm(range(1950,2050)):
        scoring_system = year_scoring_system(year)
        if scoring_system == previous_year_system:
            champion_mean_points = CHAMPION_MEAN_POINTS[year-1]
        else:
            race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
            champ_race_results = build_race_points_columns(champ_race_results, scoring_system)
            if len(champ_sprint_results) > 0:
                champ_sprint_results['sprint points']=champ_sprint_results.apply(get_points, args=[sprint_scoring],axis=1)
            else:
                champ_sprint_results['sprint points']=pd.Series(dtype = int)
            champ_race_results['fast lap points'] = (champ_race_results['fast lap rank'] == 1
                                                    ) * (champ_race_results['race points'] > 0
                                                         ) * points_for_fastest_lap
            total_points = sum([champ_race_results['race points'].sum(),
                                champ_sprint_results['sprint points'].sum(),
                                champ_race_results['fast lap points'].sum()
                                ])
            champion_mean_points = total_points/len(champ_race_results)
        CHAMPION_MEAN_POINTS[year] = champion_mean_points

print("Data pre-processing complete.\n")

def driver_surname(driver_id_or_ids):
    if type(driver_id_or_ids) in [float,int,str]:
        driver_id = driver_id_or_ids
    else:
        driver_ids = driver_id_or_ids
        return [driver_surname(one_driver) for one_driver in driver_ids]
    return ALL_DRIVERS.where(ALL_DRIVERS['driverId'] == driver_id).dropna().reset_index()['surname'][0]


def get_season_status(row, num_races, num_sprints, scoring_system):
    round_no= row['round']
    sprint_no = row['sprints so far']
    #driver1, driver2 = row['driverId #1'], row['driverId #2']
    points1, points2 = row['cum points #1'], row['cum points #2']
    
    races_remaining = num_races - round_no
    sprints_remaining = num_sprints - sprint_no
    
    '''different cases in order from most optimistic to least optimistic'''
    '''Possible if #2 drives like champ and #1 scores normally?'''
    driver1_mean_points = points1 / num_races
    champion_mean_points = 11.7 if USE_538_CHAMPION_SCORING else CHAMPION_MEAN_POINTS[year]
    final_score1 = sum([points1,
                        races_remaining * driver1_mean_points
                        ])
    
    final_score2 = sum([points2,
                        races_remaining * champion_mean_points
                        ])
    if final_score2 > final_score1:
        return "comeback possible if #2 drives like champ and #1 scores normally."
    
    '''Possible if #2 drives perfectly, #1 scores normally?'''
    race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
    final_score2 = sum([points2,
                       races_remaining*get_points(1,race_scoring),
                       races_remaining, # 1 for every fastest lap
                       sprints_remaining*get_points(1,sprint_scoring)])
    if final_score2 > final_score1:
        return "comeback possible if #2 drives perfectly and #1 scores normally"
    
    '''Possible if #2 drives perfectly, #1 scores 0 points'''
    final_score1 = points1
    if final_score2 > final_score1:
        return "comeback possible if #2 drives perfectly and #1 scores 0 points"
    return 'comeback impossible'

def get_season_statuses(year):
    year_races = ALL_RACES.where(ALL_RACES['year'] == year).dropna()
    year_races = year_races.rename(columns = {'time':'time of day'})
    year_sprint_results = ALL_SPRINT_RESULTS.merge(year_races)
    year_sprints = year_sprint_results[['raceId']].drop_duplicates().merge(year_races)
    scoring_system = year_scoring_system(year)
    race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
    
    year_race_ids = year_races[['raceId','round','sprints so far']]
    # Race
    year_race_results = ALL_RACE_RESULTS.merge(year_race_ids)
    year_sprint_results = ALL_SPRINT_RESULTS.merge(year_race_ids)
    
    year_race_results = build_race_points_columns(year_race_results, scoring_system)
    year_sprint_results = build_sprint_points_column(year_sprint_results, scoring_system)
    
    year_results = pd.merge(year_race_results,year_sprint_results,how = 'left', 
                            on = ['raceId','driverId','round','sprints so far'], 
                            suffixes = ('_(race)','_(sprint)'))
    year_results['sprint points'].fillna(0, inplace = True)
    
    year_results[ 'cum race points'   ] = year_results.groupby('driverId')['race points'].cumsum()
    year_results['cum sprint points'  ] = year_results.groupby('driverId')['sprint points'].cumsum()
    year_results['cum fast lap points'] = year_results.groupby('driverId')['fast lap points'].cumsum()
    
    year_results['cum points'] = sum([year_results['cum race points'],
                                      year_results['cum sprint points'],
                                      year_results['cum fast lap points']])
    year_results = year_results[['raceId','driverId','round','cum points', 'sprints so far']]
    no1s = year_results.sort_values('cum points',ascending = False).groupby('round', as_index=False).nth(0)
    no2s = year_results.sort_values('cum points',ascending = False).groupby('round', as_index=False).nth(1)
    rounds = pd.merge(no1s,no2s, on = ['raceId','round','sprints so far'], suffixes = (' #1',' #2'))
    
    num_rounds = len(year_race_ids)
    num_sprints = len(year_sprints)
    rounds['status'] = rounds.apply(get_season_status, args=[num_rounds, num_sprints, scoring_system], axis = 1)
    rounds = rounds.drop('sprints so far',axis = 1)
    return rounds

statuses = pd.DataFrame()
for year in tqdm(range(first_year,last_year+1)):
    year_statuses = get_season_statuses(year)
    year_statuses['year'] = year
    statuses = pd.concat([statuses, year_statuses])

columns_to_group_on = ['year','status']
groups = statuses[['year','status','round']].groupby(columns_to_group_on, as_index=False)
first_races = groups.min().sort_values(['year','round']).rename(columns={'round':'first race'})
last_races  = groups.max().sort_values(['year','round']).rename(columns={'round':'last race'})
first_and_last_races = pd.merge(first_races, last_races, on = columns_to_group_on)
def race_range(row):
    return "{}-{}".format(row['first race'], row['last race'])
race_ranges = first_and_last_races.apply(race_range, axis = 1)

avg_first_races = first_races[['status','first race']].groupby(['status'], as_index=False
                                             ).mean().sort_values('first race')

'''
    TODO Get output for last 20 years and compare against 538
'''
print("")
print(avg_first_races)

Round14 = statuses.where(statuses['round'] == 14).dropna()




