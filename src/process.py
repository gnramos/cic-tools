import argparse
import moodle
import teams
import os
import pandas as pd
import re
import utils

# Nome de arquivo: COURSE.YYYY-P.SOURCE.REPORT.INFO.EXT
#        exemplos: IEM.2020-2.teams.attendance.2021-03-19.csv
#                   ED.2020-2.moodle.grades.csv
#                   ED.2020-2.moodle.participants.html
#                  APC.2020-2.moodle.progress.csv
#                  APC.2020-2.moodle.responses.Projeto1.json
#
# COURSE: sigla da disciplina
# PERIOD: período de realização da disciplina no formato YYYY-P  (P em {0,1,2})
# SOURCE: plataforma de origem o relatório
# REPORT: tipo de relatório
#           - attendance: relatório de presença de reunião via Teams:
#               - INFO:  data da reunião (formato YYYY-MM-DD).
#           - grades: relatório de notas do Moodle.
#           - participants: página de usuários do Moodle.
#           - progress: relatório de atividades completadas do Moodle.
#           - responses: relatório de submissões de questionários do Moodle.
#               - INFO: identificador do questionário.
#   INFO: informação do arquivo (opcional)
#    EXT: extensão o arquivo


parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='*', help='Arquivos com os dados.')
parser.add_argument('-o', '--output',
                    help='Diretório para armazenar os resultados.')
parser.add_argument('-l', '--language',
                    help='Linguagem de programação de arquivos de respostas.')
args = parser.parse_args()

pattern = re.compile(r'([A-Z][0-Z]+)\.'   # course
                     r'(\d{4}-[0-2])\.'   # period
                     r'(teams|moodle)\.'  # source
                     r'(attendance|grades|participants|progress|responses)\.'
                     r'(.*?\.)?'          # info
                     r'(csv|html|json)')  # ext

data = {}
for full_path in args.files:
    path, file = os.path.split(full_path)

    if m := pattern.match(file):
        course, period, source, report, info, ext = m.groups()
        current = eval(f'{source}.{report.capitalize()}(file)')

        if course not in data:
            data[course] = {period: {}}
        if period not in data[course]:
            data[course][period] = {report: utils.Students()}
        if report not in data[course][period]:
            data[course][period][report] = utils.Students()

        if 'responses' in file.lower():
            out_path = os.path.join(course, period, info)
            if args.output is not None:
                out_path = os.path.join(args.output, out_path)
            ignore_list = []
            current.to_files(out_path, 'py', ignore_list)
        else:
            if report == 'attendance':
                for s_id in current:
                    if s_id not in current:
                        current[s_id] = current[s_id]
                        current[s_id]['Meetings'] = 0
                    current[s_id]['Meetings'] += 1

            data[course][period][report] = current



# exit(0)



# pattern = re.compile(r'[A-Z]{2,}\.\d{4}-\d\.(.*?\.)?(attendance\.csv|grades\.csv|participants\.html|progress\.csv|responses\.json)')

# args.files = [file for file in args.files if pattern.match(file)]

# data = {}
# for file in args.files:
#     course, period, *dados = file.split('.')
#     info = dados[0] if len(dados) > 2 else None
#     report = dados[-2]

#     if course not in data:
#         data[course] = {period: {}}
#     if period not in data[course]:
#         data[course][period] = {report: utils.Students()}
#     if report not in data[course][period]:
#         data[course][period][report] = utils.Students()

#     if report == 'attendance':
#         attendance = data[course][period][report]
#         att = teams.Attendance(file)
#         for s_id in att:
#             if s_id not in attendance:
#                 attendance[s_id] = att[s_id]
#                 attendance[s_id]['Meetings'] = 0
#             attendance[s_id]['Meetings'] += 1
#     elif 'grades' in file.lower():
#         data[course][period][report] = moodle.Grades(file)
#     elif 'participants' in file.lower():
#         data[course][period][report] = moodle.Participants(file)
#     elif 'progress' in file.lower():
#         data[course][period][report] = moodle.Progress(file)
#     elif 'responses' in file.lower():
#         data[course][period][report] = moodle.QuizResponse(file)
#         path = os.path.join(course, period, info)
#         ignore_list = []
#         data[course][period][report].to_files(path, 'py', ignore_list)
#         # run moss?

for course, periodos in data.items():
    for period, reports in periodos.items():
        t = utils.Students()
        for report, info in reports.items():
            if report not in ['responses']:
                for s_id, s_info in info.items():
                    if s_id not in t:
                        t[s_id] = {}
                    t[s_id].update(s_info)

        df = pd.DataFrame.from_dict(t, orient='index')
        df.index.name = 'Matrícula'

        sort_order = ['Name']
        if 'Group' in df.columns:
            df = df.reset_index()
            df = df.set_index(['Group', 'Matrícula'])
            # columns = list(df.columns)
            # group_idx = columns.index('Group')
            # columns = ['Group'] + columns[:group_idx] + columns[group_idx + 1:]
            # df = df[columns]

            sort_order = ['Group'] + sort_order

        df = df.sort_values(by=sort_order)
        # # # r = progress_df.loc[['200028880']]
        # # # print(df.head())
        df.to_csv(f'{course}.{period}.csv')


exit(0)
# for p_values in data.values():
#     print(p_values)
#     for report in p_values.values():
#         print(type(report))
#         for s_id in report.sorted_keys():
#             if s_id not in t:
#                 t[s_id] = r_values
#             else:
#                 t.update(r_values)

df = pd.DataFrame.from_dict(t, orient='index')
# # r = progress_df.loc[['200028880']]
# # print(df.head())
df.index.name = 'Matrícula'
df.to_csv('out.csv')
# print(data)
exit(0)

# attendance = utils.Students()
# grades = participants = progress = responses = None

# for file in args.files:
#     print(file)
#     continue
#     if 'attendance' in file.lower():
#         date = file.split('.')[-2]
#         att = microsoft.Teams.Attendance(file)
#         for s_id in att:
#             if s_id not in attendance:
#                 attendance[s_id] = att[s_id]
#                 attendance[s_id]['Meetings'] = 0
#             attendance[s_id]['Meetings'] += 1
#     elif 'grades' in file.lower():
#         grades = moodle.Grades(file)
#     elif 'participants' in file.lower():
#         participants = moodle.Participants(file)
#     elif 'progress' in file.lower():
#         progress = moodle.Progress(file)
#     elif 'responses' in file.lower():
#         responses = moodle.QuizResponse(file)
#         path = file.split('.')[0]
#         ignore_list = []
#         # responses.to_files(path, 'py', ignore_list)

for k in attendance.sorted_keys():
    pass
    # print(attendance[k])

for k in progress.sorted_keys():
    pass
    # print(progress[k])
# t = {}
# for d in [progress, grades]:
#     for k in d.sorted_keys():
#         if k in t:
#             t[k].update(d[k])
#         else:
#             t[k] = d[k]
# df = pd.DataFrame.from_dict(t, orient='index')
# # r = progress_df.loc[['200028880']]
# # print(df.head())
# df.to_csv('out.csv')
