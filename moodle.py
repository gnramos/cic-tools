import locale
import os


class Progress():
    """Handle participants activity completion information.

    Processes a Moodle report data to extract participants activity completion
    information.

    To get the data file:
        1. Access the Activity Completion report via:
            Course administration > Reports > Activity completion.'
        2. Select the desired group.
        3. Download spreadsheet format (UTF-8 .csv).
    """

    def __init__(self, file):
        """Constructor.

        Loads the data from the file in a dict ("data") with the following
        structure" {Student_ID: {'Name': (str - student full name),
                                'Frequência': (int - student participation (%)),
                                'Faltas':  (int - student absence (%))
                                }
                   }

        Arguments:
        file -- the CSV file to read from.
        """

        with open(file) as csvfile:
            import csv
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

            header = next(csvreader)  # skip header
            activities = (len(header) - 2) / 2

            self.data = {self._get_id(row): self._get_info(row, activities)
                         for row in csvreader}

            self._sorted_keys = [k
                                 for k in sorted(self.data,
                                                 key=lambda s: locale.strxfrm(
                                                     self.data[s]['Name']))]

    def _get_id(self, row):
        return row[1].split('@')[0]

    def _get_info(self, row, activities):
        frequency = 100 * row.count('Concluído') // activities
        return {'Name': row[0],
                'Frequência': frequency,
                'Faltas': 100 - frequency}

    def __str__(self):
        return '\n'.join(f'{self.data[k]["Name"]}, {k}, '
                         f'{self.data[k]["Frequência"]}'
                         for k in self._sorted_keys)


class QuizResponse():
    """Handles quiz responses.

    Processes a Moodle report data to extract quiz responses information.

    To get the data file:
       1. Access the quiz response report via:
           Quiz > Cog (Settings) > Results > Responses.
       2. Select the desired respondent group.
       3. Select only "attempts that are finished".
       4. Select only the "response" and the "right answer".
       5. Show the report.
       6. Download the JSON file (UTF-8 .json).
    """

    def __init__(self, file, ignore_list=[]):
        import json

        self.data = {}
        with open(file) as f:
            data = json.load(f)

        self.data = {self._get_id(data): self._get_info(data, ignore_list)
                     for data in data[0]}

    def _get_id(self, data):
        return data[2].split('@')[0]

    def _get_info(self, data, ignore_list):
        return {'Name': f'{data[1]} {data[0]}',
                'Quiz': {q: {'attempt': data[(2 * q) + 8].strip(' \r\n'),
                             'answer': data[(2 * q) + 9].strip(' \r\n')}
                         for q in range(len(data[8::2]))
                         if q not in ignore_list}}

    def _make_header(self, student_info, file_type):
        if file_type == 'py':
            return '\n'.join(f'# {i}' for i in student_info)

        if file_type in ['c', 'cpp']:
            cmt = '\n   '.join(student_info)
            return f'/* {cmt} */'

        return ' '.join(student_info)

    def _has_response(self, content):
        return content[-1] != '-' or content.count('\n') > 2

    def to_files(self, path, file_type):
        for student_id, info in self.data.items():
            student_info = [info["Name"], f'{student_id}']
            header = f'{self._make_header(student_info, file_type)}\n\n'

            for q, src in info['Quiz'].items():
                if self._has_response(src.get('attempt', '-')):
                    q_dir = os.path.join(path, f'Q{q}')
                    os.makedirs(q_dir, exist_ok=True)
                    response_file = os.path.join(q_dir,
                                                 f'{student_id}.{file_type}')
                    with open(response_file, 'w') as f:
                        f.write(f'{header}\n\n{src["attempt"]}')

                    response_file = os.path.join(q_dir, f'CORRECT.{file_type}')
                    if not os.path.isfile(response_file):
                        with open(response_file, 'w') as f:
                            f.write(src['answer'])

    def __str__(self):
        return '\n'.join(f'{self.data[k]["Name"]}, {k}'
                         for k in sorted(self.data,
                                         key=lambda s: locale.strxfrm(
                                            self.data[s]["Name"])))


locale.setlocale(locale.LC_ALL, '')


# if __name__ == '__main__':
#     import sys

#     # Check progress.
#     progress = Progress(sys.argv[1])
#     print(progress)

#     # Check responses & write to files.
#     responses = QuizResponse((sys.argv[2]))
#     print(responses)
#     responses.to_files('ResponseDir', 'py')

#     # Crosse reference.
#     progress = Progress(sys.argv[1])
#     responses = QuizResponse((sys.argv[2]), [0])  # ignore first
#     for student_id in progress.data:
#         if student_id in responses.data:
#             print(progress.data[student_id]['Name'])
#             print(responses.data[student_id]['Name'])
