from collections import defaultdict
from json import load as load_json
import os
import argparse


def _argparser():
    def file_exists(file):
        if not os.path.isfile(file):
            raise argparse.ArgumentTypeError(f'{file} does not exist')
        return file

    parser = argparse.ArgumentParser(
        description="Processes a Moodle quiz's file and extracts "
                    'all responses into separate files.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='To get the responses in a file:\n'
               '1. Access the quiz response report via:\n   Moodle > Course >'
               'Quiz > Cog (Settings) > Results > Responses.\n'
               '2. Select the desired respondent group.\n'
               '3. Select only "attempts that are finished".\n'
               '4. Select only the "response" and the "right answer".\n'
               '5. Show the report.\n'
               '6. Download the file.')

    parser.add_argument('file', type=file_exists,
                        help='file with quiz data')
    parser.add_argument('-t', '--type', default='txt',
                        choices=['c', 'cpp', 'py', 'txt'],
                        help='response file type')
    parser.add_argument('-i', '--ignore', nargs='*', type=int, default=[],
                        help='ignore questions with the given indexes')
    parser.add_argument('--no-overwrite', action='store_true',
                        help='do not overwrite existing files')

    return parser


def _format_respondant_id(id_info, file_type):
    if file_type == 'py':
        return '\n'.join(f'# {i}' for i in id_info)

    if file_type in ['c', 'cpp']:
        cmt = '\n   '.join(id_info)
        return f'/* {cmt} */'

    return ' '.join(id_info)


def _has_response(content):
    return content[-1] != '-' or content.count('\n') > 2


def _make_file_name(email):
    address, domain = email.lower().replace('.', '').split('@')
    return f'{address}'


def _make_files(quiz_dir, quiz, file_type, no_overwrite):
    u"""Processes a quiz, creating a file per user response per question.

    For the given quiz, creates the directory quiz_id and a subdirectory for
    each question, in which all user responses for that question are stored
    along a single copy of the expected correct answer.

    Args:
        quiz_dir: path to store the created file in.
        quiz: dict of questions to process.
        file_type: extension for created response files.
        no_overwrite: if false, overwrites existing files.

    Raises:
        FileExistsError: in case of no_overwrite being true and there is and
        attempt to overwrite an existing file.
    """

    for question, student_info in quiz.items():
        question_dir = os.path.join(quiz_dir, f'Q{question}')
        os.makedirs(question_dir, exist_ok=True)
        for student, response in student_info.items():
            if _has_response(response['attempt']):
                response_file = os.path.join(question_dir,
                                             f'{student}.{file_type}')
                if no_overwrite and os.path.isfile(response_file):
                    raise FileExistsError(f'File exists: "{response_file}"')
                _write_file(response_file, response['attempt'])

            response_file = os.path.join(question_dir, f'CORRECT.{file_type}')
            if not os.path.isfile(response_file):
                _write_file(response_file, response['answer'])


def _parse_json(file, file_type, ignore_list):
    u"""Extracts information from a Moodle quiz's JSON response file.

    Args:
        file: path to file with quiz data.
        file_type: extension for created response files.
        ignore_list: list of question indexes to ignore (default []).

    Returns:
        Returns a tuple (str, dict) where the string has the given file's root
        for id and the dict is {int: dict} with question index as key and
        values as {str: dict}. The key is the respondent's id and the value a
        dict with the attempt and correct answers to the question.
    """

    def subparse(data):
        respondant_id = [f'{data[1]} {data[0]}', data[2]]
        header = f'{_format_respondant_id(respondant_id, file_type)}\n\n'
        return (_make_file_name(data[2]),
                {x: {'attempt': (header.lstrip() +
                                 data[(2 * x) + 8].strip(' \r\n')),
                     'answer': data[(2 * x) + 9].strip(' \r\n')}
                 for x in range(len(data[8::2]))})

    with open(file) as f:
        file_data = load_json(f)

    quiz = defaultdict(defaultdict)
    for student_data in file_data[0]:
        student_id, questions = subparse(student_data)
        for question, src_code in questions.items():
            if question not in ignore_list:
                quiz[question][student_id] = src_code

    root, _ = os.path.splitext(file)
    return root.replace(' ', ''), quiz


def _write_file(name, content):
    with open(name, 'w', encoding='utf-8') as f:
        f.writelines(content)


def argparse_json():
    u"""Parses command line and processes the options for a JSON file."""
    parser = _argparser()
    parser.__dict__['epilog'] = parser.__dict__['epilog'].replace(
        'Download the file.', 'Download the JSON file.')
    args = parser.parse_args()

    if not args.file.lower().endswith('.json'):
        raise argparse.ArgumentTypeError(f'{args.file} is not JSON')

    json(args.file, args.type, args.ignore, args.no_overwrite)


def json(file, file_type, ignore_list=[], no_overwrite=False):
    u"""Writes a Moodle quiz's responses into separate files.

    Parses the quiz's JSON response file and processes the information,
    creating a file per user response per question.
    """

    quiz_dir, quiz = _parse_json(file, file_type, ignore_list)
    _make_files(quiz_dir, quiz, file_type, no_overwrite)


if __name__ == '__main__':
    argparse_json()
