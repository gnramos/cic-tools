import locale
import os


class Progress(dict):
    """Handle participants activity completion information.

    Processes a Moodle report data to extract participants activity completion
    information. Extends dict, so keys are the student IDs and each item has
    the following structure:
        {'Name': (str - student full name),
         'Frequência': (int - student participation (%)),
         'Faltas':  (int - student absence (%))}

    To get the data file:
        1. Access the Activity Completion report via:
            Course administration > Reports > Activity completion.'
        2. Select the desired group.
        3. Download spreadsheet format (UTF-8 .csv).
    """

    def __init__(self, file):
        """Constructor.

        Loads the data from the file into instance.

        Arguments:
        file -- the CSV file to read from.
        """

        with open(file) as csvfile:
            import csv
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

            header = next(csvreader)  # skip header
            activities = (len(header) - 2) / 2

            for row in csvreader:
                student_id, _ = row[1].split('@')
                frequency = 100 * row.count('Concluído') // activities
                self[student_id] = {'Name': row[0],
                                    'Frequência': frequency,
                                    'Faltas': 100 - frequency}

        self._sorted_keys = [k
                             for k in sorted(self.keys(),
                                             key=lambda x: locale.strxfrm(
                                                 self[x]['Name']))]

    def __str__(self):
        return '\n'.join(f'{self[k]["Name"]}, {k}, '
                         f'{self[k]["Frequência"]}'
                         for k in self._sorted_keys)


class QuizResponse(dict):
    """Handles quiz responses.

    Processes a Moodle report data to extract quiz responses information.
    Extends dict, so keys are the student IDs and each item has the following
    structure:
        {'Name': (str - student full name),
         'Quiz': (dict)
            {q: (int - question number in quiz)
                {'attempt': (str - attempt value),
                 'answer': (str - correct answer value)}}}

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
        """Constructor.

        Loads the data from the file into instance.

        Arguments:
        file -- the JSON file to read from.
        """

        import json

        self.data = {}
        with open(file) as f:
            data = json.load(f)

        for d in data[0]:
            student_id, _ = d[2].split('@')
            self[student_id] = {'Name': f'{d[1]} {d[0]}',
                                'Quiz': {q: {'attempt': d[(2 * q) + 8].strip(' \r\n'),
                                             'answer': d[(2 * q) + 9].strip(' \r\n')}
                                         for q in range(len(d[8::2]))
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
        for student_id, info in self.items():
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
        return '\n'.join(f'{self[k]["Name"]}, {k}'
                         for k in sorted(self.keys(),
                                         key=lambda x: locale.strxfrm(
                                            self[x]['Name'])))


locale.setlocale(locale.LC_ALL, '')


# if __name__ == '__main__':
#     import sys

#     # Check progress.
#     progress = Progress(sys.argv[1])
#     print(progress)
#     print(progress['180110730'])

#     # Check responses & write to files.
#     responses = QuizResponse(sys.argv[2])
#     print(responses)
#     print(responses['180110730'])
#     responses.to_files('ResponseDir', 'py')

#     # Crosse reference.
#     progress = Progress(sys.argv[1])
#     responses = QuizResponse((sys.argv[2]), [0])  # ignore first
#     for student_id in progress:
#         print(progress[student_id]['Name'])
#         if student_id in responses:
#             print(responses[student_id]['Name'])
