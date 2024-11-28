# -*- coding: utf-8 -*-
import os
import datetime
import calendar
import subprocess
import requests
import csv
import ephem
import pytz
import locale
from io import StringIO
from xml.etree import ElementTree as ET
import math, decimal, datetime
dec = decimal.Decimal

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--year', type=int, required=True)
parser.add_argument('--country', type=str, required=True)
parser.add_argument('--timezone', type=str, required=True)
parser.add_argument('--locale', type=str, required=True)
args = parser.parse_args()

year = args.year
country = args.country
timezone = pytz.timezone(args.timezone)

locale.setlocale(locale.LC_ALL, args.locale)

holidays = []

with requests.get(f'https://date.nager.at/PublicHoliday/Country/{country}/{year}/CSV') as req:
    for row in csv.DictReader(StringIO(req.text)):
        holiday_date = tuple(map(int, row['Date'].split('-')))
        holidays.append([holiday_date[2], holiday_date[1], row['LocalName']])


full_moon_schedule = []
new_moon_schedule = []

d = datetime.datetime(year, 1, 1, tzinfo=timezone)
while True:
    nnm = ephem.next_new_moon(d)
    d = nnm.datetime()
    if d.year != year:
        break
    new_moon_schedule.append((d.day, d.month))

d = datetime.datetime(year, 1, 1, tzinfo=timezone)
while True:
    nfm = ephem.next_full_moon(d)
    d = nfm.datetime()
    if d.year != year:
        break
    full_moon_schedule.append((d.day, d.month))

template_path = 'monthly-calendar-planner.svg'
output_path_tpl = 'monthly-calendar-planner-{year:04d}-{month:02d}-{country}.svg'
output_path_merged_tpl = 'monthly-calendar-planner-{year:04d}-{country}.pdf'

tmpl = ET.parse(open(template_path, 'rt'))

month_el = None
for text in tmpl.findall('.//{http://www.w3.org/2000/svg}text'):
    label = text.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
    if label == '#month':
        month_el = text

day_no_els = []
holiday_els = []
for text in tmpl.findall('.//{http://www.w3.org/2000/svg}text'):
    label = text.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
    if label == '#dayno':
        day_no_els.append(text)
    if label == '#holiday':
        holiday_els.append(text)

def week_elem_key(text):
    return float(text.attrib['y']), float(text.attrib['x'])

day_no_els.sort(key=week_elem_key)
holiday_els.sort(key=week_elem_key)

cal = calendar.Calendar(0)

month_names = list(calendar.month_name[i][:3].upper() for i in range(1, 13))

parent_map = dict((c, p) for p in tmpl.iter() for c in p)

cal_data = []
for month in range(1, 13):
    month_cal_data = cal.monthdays2calendar(year, month)
    for week in month_cal_data:
        for i in range(len(week)):
            week[i] = (month, week[i][0], week[i][1])
    if len(month_cal_data) == 6:
        first_week = month_cal_data.pop(0)
        for i, (month, day, week_day) in enumerate(first_week):
            if day:
                if cal_data:
                    cal_data[-1][-1][i] = (month, day, week_day)
    cal_data.append(month_cal_data)

month_files_svg = []
month_files_pdf = []
for month_idx, month_cal_data in enumerate(cal_data):
    month = month_idx + 1
    output_path = output_path_tpl.format(year=year, month=month, country=country)
    month_el.find('{http://www.w3.org/2000/svg}tspan').text = month_names[month_idx]
    i = 0
    for week in month_cal_data:
        for month_no, day_no, week_day_no in week:
            holiday = ''
            for h_day, h_month, h_name in holidays:
                if h_month == month_no and h_day == day_no:
                    holiday = h_name
            day_no_els[i].find('{http://www.w3.org/2000/svg}tspan').text = str(day_no or '')
            holiday_els[i].find('{http://www.w3.org/2000/svg}tspan').text = holiday
            for g in parent_map[day_no_els[i]].find('{http://www.w3.org/2000/svg}g'):
                label = g.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
                if label == '#newmoon':
                    if (day_no, month_no) not in full_moon_schedule:
                        g.attrib['style'] += ';display:none'
                    else:
                        g.attrib['style'] = g.attrib['style'].replace(';display:none', '')
                if label == '#fullmoon':
                    if (day_no, month_no) not in new_moon_schedule:
                        g.attrib['style'] += ';display:none'
                    else:
                        g.attrib['style'] = g.attrib['style'].replace(';display:none', '')
            i += 1
    with open(output_path, 'wb') as fp:
        tmpl.write(fp)
    subprocess.check_call([
        'inkscape',
        '--batch-process',
        '--export-area-page',
        '--export-type', 'pdf',
        '--export-filename', output_path + '.pdf',
        output_path,
    ])
    month_files_svg.append(output_path)
    month_files_pdf.append(output_path + '.pdf')

subprocess.check_call(['pdfunite'] + month_files_pdf + [output_path_merged_tpl.format(year=year, country=country)])

for name in month_files_svg + month_files_pdf:
    os.remove(name)

#week_texts_by_month = {}
#for i, text in enumerate(week_texts):
#    row = (i // 5) + 1
#    col = i % 5
#    if row not in week_texts_by_month:
#        week_texts_by_month[row] = {}
#    week_texts_by_month[row][col] = text
#
#week_boxes_by_month = {}
#for i, box in enumerate(week_boxes):
#    row = (i // 5) + 1
#    col = i % 5
#    if row not in week_boxes_by_month:
#        week_boxes_by_month[row] = {}
#    week_boxes_by_month[row][col] = box
#
#last_month = -1
#last_week = -1
#while week_start.year <= year:
#    week_end = week_start + one_week - one_day
#
#    if week_end.year > year and week_end.month == 1:
#        month = 12
#    else:
#        month = week_end.month
#
#    if last_month != month:
#        if last_month != -1:
#            for i in range(last_week, 5):
#                text = week_texts_by_month[last_month][i]
#                text.attrib['style'] += ';display:none'
#                box = week_boxes_by_month[last_month][i]
#                box.attrib['style'] += ';display:none'
#        last_month = month
#        last_week = 0
#
#    print(last_month, last_week, week_start, week_end)
#
#    if last_month == 12 and last_week > 4:
#        break
#
#    text = week_texts_by_month[last_month][last_week]
#    text.find('{http://www.w3.org/2000/svg}tspan').text = '{} - {}'.format(week_start.strftime('%d.%m.'), week_end.strftime('%d.%m.'))
#
#    week_start += one_week
#    last_week += 1
#
#tmpl.write(open(output_path, 'wt'))

#

#e = ET.parse(open('/home/lukas/Documents/tyzdenny-kalendar-sablona.svg'))

#start_date = datetime.date(2019, 12, 29)
#for text in e.findall('.//{http://www.w3.org/2000/svg}text'):
#    week_label = text.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
#    if week_label.startswith('#week'):
#        week = int(week_label[5:])
#        week_start_date = start_date + datetime.timedelta(days=7) * (week - 1)
#        week_end_date = week_start_date + datetime.timedelta(days=6)
#        text.find('.//{http://www.w3.org/2000/svg}tspan').text = '{} - {}'.format(week_start_date.strftime('%d.%m.'), week_end_date.strftime('%d.%m.'))

#e.write(open('/home/lukas/Documents/tyzdenny-kalendar-out.svg', 'wt'))
