#!/usr/bin/env python3

import json
import pdb
import csv
from collections import OrderedDict
import os.path
from pathlib import Path
from datetime import datetime
import re
import pandas as pd
import sys

import settings
import scrape_schedule

def CalcPercent(total, skip, correct):
    try:
        return  round(correct / (total - skip) * 100., 2)
    except ZeroDivisionError:
        return None

def GetPercent(item):
    newstr = item.replace("%", "")
    newstr = newstr.replace("?", "")
    if (newstr.strip()==""):
        return -1
    return float(newstr)

def GetIndex(item):
    filename = os.path.basename(str(item))
    idx = re.findall(r'\d+', str(filename))
    if (len(idx) == 0):
        idx.append("-1")
    return int(idx[0])

def GetFiles(path, templatename):
    A = []
    files = Path(path).glob(templatename)
    for p in files:
        A.append(p)
    file_list = []
    for item in range(0, 19):
        file_list.append("?")
    for item in A:
        idx = GetIndex(item)
        if (len(file_list) > idx):
            file_list[idx] = item
    file_list = [x for x in file_list if x != "?"]
    return file_list

def CurrentScheduleFiles(filename):
    stat = os.path.getmtime(filename)
    stat_date = datetime.fromtimestamp(stat)
    if stat_date.date() < datetime.now().date():
        return False
    return True

def RefreshScheduleFiles():
    now = datetime.now()
    year = int(now.year)
    scrape_schedule.year = year
    scrape_schedule.main(sys.argv[1:])

def GetActualScores(abbra, teama, abbrb, teamb, scores):
    items = re.split(r'(,|\s)\s*', str(scores).lower())
    if (not items):
        return -1, -1
    if (items[0].strip() == "canceled"):
        return -3, -3
    if (items[0].strip() == "postponed"):
        return -2, -2
    if (items[0].strip() == "?"):   # not yet Played Game
        return -1, -1
    ot = -1
    if (len(items) == 9 and "ot)" in items[8]):
        # overtime case
        ot += 1
    elif (len(items) != 7):
        return -1, -1
    if (abbra.lower().strip() not in items and abbrb.lower().strip() not in items):
        return -1, -1
    if (abbra.lower().strip() == items[0].lower().strip()):
        scorea = int(items[2])
        scoreb = int(items[6])
    else:
        scorea = int(items[6])
        scoreb = int(items[2])
    return scorea, scoreb

now = datetime.now()
saved_path = "{0}{1}/{2}".format(settings.predict_root, int(now.year), settings.predict_saved)
sched_path = "{0}{1}/{2}".format(settings.predict_root, int(now.year), settings.predict_sched)
verbose = False
if (len(sys.argv)==2):
    verbose = True

    print ("Measure Actual Results Tool")
    print ("**************************")

Path(sched_path).mkdir(parents=True, exist_ok=True)
RefreshScheduleFiles()

file = '{0}sched1.json'.format(sched_path)
if (not os.path.exists(file)):
    if (verbose):
        print ("schedule files are missing, run the scrape_schedule tool to create")
    exit()

Path(saved_path).mkdir(parents=True, exist_ok=True)
file = '{0}week1.csv'.format(saved_path)
if (not os.path.exists(file)):
    if (verbose):
        print ("Weekly files are missing, run the score_week tool to create")
    exit()

sched_files = GetFiles(sched_path, "sched*.json")
list_sched = []
for file in sched_files:
    with open(file) as sched_file:
        item = json.load(sched_file, object_pairs_hook=OrderedDict)
        item['Week'] = GetIndex(file)
        list_sched.append(item)
week_files = GetFiles(saved_path, "week*.csv")
list_week = []
for file in week_files:
    with open(file) as week_file:
        reader = csv.DictReader(week_file)
        for row in reader:
            row['Week'] = GetIndex(file)
            list_week.append(row)
IDX=[]
A=[]
B=[]
C=[]
D=[]
E=[]
index = 0
alltotal = 0
allskip = 0
allcorrect = 0
count = 0
for idx in range(len(list_sched)):
    total = 0
    skip = 0
    correct = 0
    week = list_sched[idx]["Week"]
    for item in list_sched[idx].values():
        if (item == week):
            break
        total += 1
        chancea = -1
        abbra = ""
        abbrb = ""
        teama = ""
        teamb = ""
        if (index < len(list_week) and list_week[index]["Week"] == week):
            chancea = GetPercent(list_week[index]["ChanceA"])
            chanceb = GetPercent(list_week[index]["ChanceB"])
            abbra = list_week[index]["AbbrA"]
            abbrb = list_week[index]["AbbrB"]
            teama = list_week[index]["TeamA"]
            teamb = list_week[index]["TeamB"]
        index += 1
        scorea, scoreb = GetActualScores(abbra, teama, abbrb, teamb, item["Score"])
        if ((int(chancea) == 0 and int(chanceb) == 0) or scorea < 0 or scoreb < 0):
            if (teama != "" and teamb != "" and "tickets" not in item["Score"]):
                if (item["Score"].lower() == "canceled"):
                    print ("***\nGame skipped\n\n\t[{0} vs {1}] \n\tabbreviation(s) [{2}] [{3}] Score {4}\n\tcanceled\n***\n"
                        .format(teama, teamb, abbra, abbrb, item["Score"]))
                elif (item["Score"].lower() == "postponed"):
                    print ("***\nGame skipped\n\n\t[{0} vs {1}] \n\tabbreviation(s) [{2}] [{3}] Score {4}\n\tpostponed\n***\n"
                        .format(teama, teamb, abbra, abbrb, item["Score"]))
                else:
                    if (item["Score"] != "?"):
                        print ("***\nGame skipped\n\n\t[{0} vs {1}] \n\tabbreviation(s) [{2}] [{3}] Score {4}\n\treview your merge files\n***\n".format(teama, teamb, abbra, abbrb, item["Score"]))
            skip += 1
        else:
            if (chancea >= 50 and (scorea >= scoreb)):
                correct += 1
            if (chancea < 50 and (scorea < scoreb)):
                correct += 1
    count += 1
    IDX.append(count)
    A.append(week)
    B.append(total)
    C.append(skip)
    D.append(correct)
    E.append(CalcPercent(total, skip, correct))
    print ("week{0} total={1}, skip={2}, correct={3} Percent={4}%".format(week, total, skip, correct, CalcPercent(total, skip, correct)))
    alltotal = alltotal + total
    allskip = allskip + skip
    allcorrect = allcorrect + correct
count += 1
IDX.append(count)
A.append(99)
B.append(alltotal)
C.append(allskip)
D.append(allcorrect)
E.append(CalcPercent(alltotal, allskip, allcorrect))

print ("====================================================================")
print ("Totals total={0}, skip={1}, correct={2} Percent={3}%".format(alltotal, allskip, allcorrect, CalcPercent(alltotal, allskip, allcorrect)))
print ("====================================================================")

df=pd.DataFrame(IDX,columns=['Index'])
df['Week']=A
df['Total Games']=B
df['Count Unpredicted']=C
df['Count Correct']=D
df['Percent Correct']=E

file = "{0}results.json".format(saved_path)
with open(file, 'w') as f:
    f.write(df.to_json(orient='index'))

with open(file) as results_json:
    dict_results = json.load(results_json, object_pairs_hook=OrderedDict)

file = "{0}results.csv".format(saved_path)
results_sheet = open(file, 'w', newline='')
csvwriter = csv.writer(results_sheet)
count = 0
for row in dict_results.values():
    if (count == 0):
        header = row.keys()
        csvwriter.writerow(header)
        count += 1
    csvwriter.writerow(row.values())
results_sheet.close()
print ("done.")
