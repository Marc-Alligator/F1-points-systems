# -*- coding: utf-8 -*-
"""
F1 scoring systems comparer by Marc Allerheiligen
Calculates how competitive a championship is with different points systems

inspired by article by 538:
https://fivethirtyeight.com/features/forget-last-years-finish-formula-one-is-drama-free-again/
"""

print("Importing libraries...")
import pandas as pd
from tqdm import tqdm

#CURRENT_SCORING = [25,18,15,12,10,8,6,4,2,1]

RACE_SCORING_SYSTEMS = {
        (1950,1959):[8,6,4,3,2],
        (1960,1960):[8,6,4,3,2,1],
        (1961,1990):[9,6,4,3,2,1],
        (1991,2002):[10,6,4,3,2,1],
        (2003,2009):[10,8,6,5,4,3,2,1],
        (2010,9999):[25,18,15,12,10,8,6,4,2,1],
    }
CURRENT_SPRINT_SCORING = [8,7,6,5,4,3,2,1]
PRE_2022_SPRINT_SCORING = [3,2,1]

SIMPLEST_SCORING = [20-place for place in range(20)]

'''Test Scoring Values override the correct value for the year.
        To allow the correct values to be used, assign them to None
'''

TEST_RACE_SCORING = SIMPLEST_SCORING
TEST_RACE_SCORING = None
TEST_SPRINT_SCORING = None
TEST_POINTS_FOR_FASTEST_LAP = None

print("Loading data...")
ALL_RACES = pd.read_csv("archive/races.csv")
ALL_DRIVERS = pd.read_csv("archive/drivers.csv")
ALL_RESULTS = pd.read_csv("archive/results.csv")
ALL_SPRINT_RESULTS = pd.read_csv("archive/sprint_results.csv")
ALL_STANDINGS = pd.read_csv("archive/driver_standings.csv")
print("Data done loading.")

print("Pre-processing data...")
print("Calculating fastest laps...")
FASTEST_LAPS = ALL_RESULTS.sort_values('fastestLapTime').groupby('raceId').nth(0)

columns_to_drop = [column for column in ALL_RACES.columns if 'date' in column or 'time' in column]
columns_to_drop.remove('date')
columns_to_drop.extend(['circuitId','url'])
for column in columns_to_drop:
    ALL_RACES = ALL_RACES.drop(column, axis = 1)

RESULTS_COLUMNS = ['raceId','driverId','position']
ALL_RESULTS = ALL_RESULTS[RESULTS_COLUMNS]
ALL_SPRINT_RESULTS = ALL_SPRINT_RESULTS[RESULTS_COLUMNS]

print("Calculating mean points scored by historical champions...")

LAST_RACES = ALL_RACES.sort_values('raceId',ascending = False).groupby('year').nth(0)
END_OF_SEASON_STANDINGS = ALL_STANDINGS.merge(LAST_RACES)
CHAMPIONS = END_OF_SEASON_STANDINGS.where(END_OF_SEASON_STANDINGS['position'] == 1).dropna()
CHAMPIONS = CHAMPIONS.merge(ALL_RACES)[['driverId','year']]
CHAMPION_MEAN_POINTS = dict() # year:mean

def driver_places(results, driver_id):
    return results.where(results['driverId'] == driver_id).dropna()['position']

def get_score(pos, scoring_system):
    if pos == r'\N': return 0
    if int(pos) > len(scoring_system): return 0
    return scoring_system[int(pos)-1]

def who_had_fastest_lap(race_id):
    return FASTEST_LAPS['driverId'][race_id]

def points_from_fastest_lap(race_id, driver_id, results, POINTS_FOR_FASTEST_LAP):
    if not POINTS_FOR_FASTEST_LAP:
        return 0
    if driver_id != who_had_fastest_lap(race_id):
        return 0
    '''note that the below DataFrame take a surprising amount of time.
        before checking the list first, the whole program took orders of magnitude longer.'''
    race_results = results.where(results['raceId'] == race_id).dropna()
    result = race_results.where(race_results['driverId'] == driver_id).dropna()
    if len(result) == 0:
        return 0
    position = result.reset_index()['position'][0]
    if position == r'\N':
        return 0
    if int(position) > 10: # don't try int() before checking \N case
        return 0
    return 1

def driver_points(results, sprint_results, driver_id, scoring_system):
    race_scoring_system, sprint_scoring_system, points_for_fastest_lap = scoring_system
    normal_points = sum(get_score(place, race_scoring_system) for place in driver_places(results, driver_id))
    part_year_race_ids = results['raceId'].unique()
    fastest_lap_points = sum([points_from_fastest_lap(race_id, driver_id, results, points_for_fastest_lap)
                              for race_id in part_year_race_ids])
    sprints_points = sum(get_score(place, sprint_scoring_system) for place in driver_places(sprint_results, driver_id))
    return normal_points + fastest_lap_points + sprints_points

def end_of_season_score(row, scoring_system):
    driver_id = row['driverId']
    year = row['year']
    year_races = ALL_RACES.where(ALL_RACES['year'] == year).dropna()
    year_races = year_races.rename(columns = {'time':'time of day'})
    year_results = ALL_RESULTS.merge(year_races)
    year_sprint_results = ALL_SPRINT_RESULTS.merge(year_races)
    return driver_points(year_results, year_sprint_results, driver_id, scoring_system)

def year_scoring_system(year):        
    year = int(year)
    
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
    
    # Fast Lap
    points_for_fastest_lap = 1 if (year < 1959 or year > 2019) else 0
    
    # Test Scoring (override)
    if TEST_RACE_SCORING != None:
        scoring = TEST_RACE_SCORING
    if TEST_SPRINT_SCORING != None:
        sprint_scoring = TEST_SPRINT_SCORING
    if TEST_POINTS_FOR_FASTEST_LAP != None:
        points_for_fastest_lap = TEST_POINTS_FOR_FASTEST_LAP
    return (scoring, sprint_scoring, points_for_fastest_lap)

previous_year_system = ()
for year in tqdm(range(1950,2050)):
    scoring_system = year_scoring_system(year)
    if scoring_system == previous_year_system:
        all_time_all_champion_points = CHAMPION_MEAN_POINTS[year-1]
    else:
        all_time_all_champion_points = CHAMPIONS.apply(end_of_season_score, args = [scoring_system], axis = 1).sum()
    champion_mean_points = all_time_all_champion_points / len(ALL_RACES)
    CHAMPION_MEAN_POINTS[year] = champion_mean_points
    previous_year_system = scoring_system

print("Data pre-processing complete.\n")



def driver_surname(driver_id):
    return ALL_DRIVERS.where(ALL_DRIVERS['driverId'] == driver_id).dropna().reset_index()['surname'][0]

def brief_outcome(driver1, driver2, final_score1, final_score2):
    if final_score1 == final_score2:
        print("Then they would tie.")
    elif final_score1 > final_score2:
        print("Then the #1 driver, "+driver_surname(driver1)+" would still win.")
    else:
        print("Then the #2 driver, "+driver_surname(driver2)+" would win.")
        

def get_season_status(year, year_races, year_sprints, year_results, race):
    last_race = race
    
    scoring_system = year_scoring_system(year)
    
    #last_race_index = last_race - 1
    #last_race_date = year_races.sort_values('date').reset_index()['date'][last_race_index]
    #last_race_id = year_races.where(year_races['round'] == last_race).dropna().reset_index()['raceId'][0]
    
    part_year_races = year_races.where(year_races['round'] <= last_race)
    #part_year_races = year_races.sort_values('date')[:last_race]
    part_year_races_ids = part_year_races[['raceId']]
    part_year_results = part_year_races_ids.merge(year_results)
    part_year_sprint_results = part_year_races_ids.merge(ALL_SPRINT_RESULTS)
    
    VERBOSE = False
    if VERBOSE:
        print("Calculating points for first {} races in {} season...".format(last_race,year))
    driver_ids = list()
    driver_points_values = list()
    for driver_id in part_year_results['driverId'].unique():
        driver_ids.append(driver_id)
        driver_points_values.append(driver_points(part_year_results, part_year_sprint_results, 
                                                  driver_id, scoring_system))
    ranking = pd.DataFrame(data = {'driverId':driver_ids,'points':driver_points_values})
    ranking = ranking.sort_values('points', ascending = False).reset_index()[['driverId','points']]
    driver1 = ranking['driverId'][0]
    driver2 = ranking['driverId'][1]
    
    real_points = dict()
    for driver in [driver1, driver2]:
        real_points[driver] = ranking.where(ranking['driverId'] == driver).dropna().reset_index()['points'][0]

    num_races = len(year_races)
    races_remaining = num_races - last_race
    #remaining_sprints = year_sprints.where(year_sprints['date'] > last_race_date).dropna()
    remaining_sprints = year_sprints.where(year_sprints['round'] > last_race).dropna()
    sprints_remaining = len(remaining_sprints)
    
    if VERBOSE:
        print("")
        
        for driver in [driver1, driver2]:
            print(driver_surname(driver),"has {} points".format(real_points[driver]))
        print(races_remaining,"races remaining")
        print(sprints_remaining,"sprints remaining")
        print("")
    
    
    '''different cases in order from most optimistic to least optimistic'''
    '''Possible if #2 drives like champ and #1 scores normally?'''
    driver1_mean_points = real_points[driver1] / num_races
    champion_mean_points = CHAMPION_MEAN_POINTS[year]
    final_score1 = sum([real_points[driver1],
                        races_remaining * driver1_mean_points
                        ])
    
    final_score2 = sum([real_points[driver2],
                        races_remaining * champion_mean_points
                        ])
    if final_score2 > final_score1:
        return "possible if #2 drives like champ and #1 scores normally."
    
    '''Possible if #2 drives perfectly, #1 scores normally?'''
    race_scoring, sprint_scoring, points_for_fastest_lap = scoring_system
    final_score2 = sum([real_points[driver2],
                       races_remaining*get_score(1,race_scoring),
                       races_remaining, # 1 for every fastest lap
                       sprints_remaining*get_score(1,sprint_scoring)])
    if final_score2 > final_score1:
        return "possible if #2 drives perfectly and #1 scores normally"
    
    '''Possible if #2 drives perfectly, #1 scores 0 points'''
    final_score1 = real_points[driver1]
    if final_score2 > final_score1:
        return "possible if #2 drives perfectly and #1 scores 0 points"
    return 'decided'

def is_season_decided(year, year_races, year_sprints, year_results, race):
    season_status = get_season_status(year, year_races, year_sprints, year_results, race)
    if season_status == 'decided':
        return True
    return False

def when_season_decided(year):
    year = int(year)
    
    year_races = ALL_RACES.where(ALL_RACES['year'] == year).dropna()
    year_races = year_races.rename(columns = {'time':'time of day'})
    year_results = ALL_RESULTS.merge(year_races)
    year_sprint_results = ALL_SPRINT_RESULTS.merge(year_races)
    year_sprints = year_sprint_results[['raceId']].drop_duplicates().merge(year_races)
    num_races = len(year_races)
    
    # binary search for when season was decided
    earliest_possible = 1
    latest_possible = num_races
    
    while earliest_possible != latest_possible:
        race =  earliest_possible + (latest_possible - earliest_possible) // 2
        if is_season_decided(year, year_races, year_sprints, year_results, race):
            latest_possible = race
        else:
            earliest_possible = race + 1
    assert earliest_possible == latest_possible
    race = earliest_possible
    return race

'''
If 2nd place driver in championship places 1st for every race for the rest of the season,
but the 1st place driver still places with their average number of points,
'''

results = list()
for year in tqdm(range(1994,2023+1)):
    result = when_season_decided(year)
    results.append(result)
    
    def race_name(race_id):
        return ALL_RACES.where(ALL_RACES['raceId'] == race_id).dropna().reset_index()['name'][0]
    
    #print("The",year,"Season was decided after race number,",str(result)+", which was the",race_name(result))
mean_result = sum(results) / len(results)
print("\n"+"The average season was decided after",mean_result,"races")




'''
TODO LIST:
    -Get output for last 20 years and compare against 538
    -Write code that can access when seasons are reasonably close
            as opposed to when it's technically possible
        Specifically for if #2 drives like champ and #1 scores IAW average
    
'''








