"""Composição de processos para facilitar a análise de relatórios nas
plataformas Moodle e Teams.

Para detalhes de uso, use a opção -h na linha de comando.
"""

from argparse import ArgumentParser
from collections import defaultdict
import locale
import re
import os

import moodle.grades
import moodle.participants
import moodle.progress
import moodle.quiz.grades
import moodle.quiz.responses
import moss
import teams.attendance


def _load(files):
    """Lê os arquivos fornecidos e retorna um dicionário com as informações.

    Assume que o nome do arquivo determina o relatório e, portanto, como obter
    as informações: executando o método "read" específico.

    Assume que os nomes dos arquivos seguem o formato:
    CURSO.AAAA-P.ORIGEM.RELATORIO.EXTRA.EXT

    onde:
        CURSO: sigla da disciplina.
        AAAA-P: período de realização da disciplina no formato ano-semestre
                (P em {0,1,2}).
        ORIGEM: plataforma de origem o relatório.
        RELATORIO: tipo de relatório:
            - attendance: relatório de presença de reunião via Teams. Neste
                          caso, EXTRA deve ser a data da reunião (formato
                          YYYY-MM-DD).
            - grades: relatório de notas do Moodle.
            - participants: página de usuários do Moodle.
            - progress: relatório de atividades completadas do Moodle.
            - quiz.grades: relatório de notas de questionários do Moodle. Neste
                           caso, EXTRA identifica o questionário.
            - quiz.responses: relatório de submissões de questionários do
                              Moodle. Neste caso, EXTRA: identifica o
                              questionário.
        EXTRA: informação adicional sobre o arquivo (opcional),
        EXT: extensão o arquivo.

    A estrutura do dicionário é: [curso][período][info]
    """

    FILE_PATTERN = re.compile(r'([A-Z][0-Z]+)\.'         # CURSO
                              r'(\d{4}-[0-2])\.'         # PERIODO
                              r'(moodle|teams)\.'        # ORIGEM
                              r'(attendance|grades|'     # RELATORIO (abordagem
                              r'participants|progress|'  # gulosa, a ordem faz
                              r'quiz\.grades|'           # diferença)
                              r'quiz\.responses|quiz)(?=\.)'
                              r'\.?(.*)?'                # EXTRA (opcional)
                              r'\.(csv|html|json)')      # EXT

    data, attendance = {}, {}
    for full_path in sorted(files):
        path, file = os.path.split(full_path)

        if m := FILE_PATTERN.match(file):
            print(file)
            course, period, source, report, extra, ext = m.groups()
            current = eval(f'{source}.{report}.read(full_path, extra)')

            if course not in data:
                data[course] = {period: defaultdict(dict)}
                attendance[course] = {period: {'Total': 0}}

            if report == 'attendance':
                attendance[course][period]['Total'] += 1
                for student_id in current:
                    attendance[course][period][student_id] += 1
            else:
                if report not in data[course][period]:
                    data[course][period][report] = current
                elif extra:
                    for student_id, value in current.items():
                        if student_id not in data[course][period][report]:
                            data[course][period][report][student_id] = {}
                        data[course][period][report][student_id].update(value)

    for course, periods in attendance.items():
        for period, info in periods.items():
            data[course][period]['attendance'] = {
                student_id: (100 * info.get(student_id, 0)) // info['Total']
                for student_id in info if student_id != 'Total'}

    return data


def _make_csv(reports, output, num_classes, sep):
    """ Processa os arquivos e grava os resultados em um arquivo CSV.

    O arquivo lista, para cada aluno, identificação, atividades que foram
    avaliadas (notas o Moodle), progresso (atividades completadas no Moodle),
    e frequência (em reuniões do Teams).

    No caso de uma quantidade de aulas ser fornecida, o progresso é substituído
    pela quantidade de "faltas", ou seja, pelo percentual de atividades NÃO
    completadas multiplicado por esta quantidade.
    """

    def full_csv_header():
        return sep.join(['Matrícula', 'Nome', grades_csv_header(),
                         f'Faltas (em {num_classes})'
                         if num_classes else 'Progresso (%)'])

    def grades_csv_header():
        first_key = next(iter(reports['grades'].keys()))
        return sep.join(f'"{key}"'
                        for key in reports['grades'][first_key]['Grades'])

    def grades_csv(id):
        return sep.join(f'{g.replace(".", ",")}'
                        for g in reports['grades'].get(id, {}).get(
                            'Grades', {}).values())

    def progress(id):
        absent = reports.get('progress', {}).get(id, {}).get('Faltas', '?') == '?'

        if absent == '?':
            return '?'

        if num_classes:
            return (int(absent) * num_classes) // 100
        return 100 - int(absent)  # percentual do progresso

    def students_by_group():
        groups = defaultdict(list)
        for id, info in reports['participants'].items():
            if reports['participants'][id]['Role'] == 'Estudante':
                groups[info['Group']].append(id)
        return groups

    def student_csv(id):
        student = sep.join([id, reports['participants'][id]['Name']])
        return sep.join([student, grades_csv(id), str(progress(id))])

    locale.setlocale(locale.LC_ALL, '')

    for group, ids in students_by_group().items():
        if not ids:  # múltiplos grupos são ignorados.
            continue

        file = os.path.join(output,
                            f'{group.replace("/", "-").replace(" ", "_")}.csv')
        print(f'writing {file}')
        with open(file, 'w') as f:
            f.write(f'{full_csv_header()}\n')
            f.write('\n'.join(student_csv(id)
                              for id in sorted(ids,
                              key=lambda k: locale.strxfrm(
                                reports['participants'][k]['Name']))))


def _parse_args():
    """Retorna os argumentos da linha de comando, devidamente processados."""

    parser = ArgumentParser()
    parser.add_argument('files', nargs='+',
                        help='Arquivos a serem processados no formato '
                             'CURSO.AAAA-P.ORIGEM.RELATORIO.EXTRA.EXT')

    parser.add_argument('-o', '--output', default='.',
                        help='diretório para armazenar os arquivos')
    parser.add_argument('-s', '--sep', default=';',
                        help='separador de elementos para arquivo')
    parser.add_argument('-a', '--aulas', type=int, default=0,
                        help='quantidade de aulas do semestre')

    # MOSS
    parser.add_argument('-m', '--moss', action='store_true',
                        help='executar  MOSS.')
    parser.add_argument('-e', '--ext', default='py',
                        help='extensão dos arquivos de programa (MOSS)')
    parser.add_argument('-i', '--ignore', nargs='+', default=[],
                        help='índices de questões em questionários que '
                             'devem ser ignoradas (MOSS)')
    parser.add_argument('-t', '--threshold', default=30,
                        help='limiar de similaridade percentual (MOSS)')

    return parser.parse_args()


def _run_MOSS(reports, output, ext, ignore, threshold):
    """Processa os arquivos para chamar o script MOSS."""
    def call_moss(path):
        shell_options = ['-x', '-l python' if ext == 'py' else '']
        print(f'Calling MOSS... ({path})')
        return moss.call(shell_options, path, ext)

    def report(path, url):
        basename, question = os.path.split(path)
        basename, quiz = os.path.split(basename)
        moss_report = os.path.join(output, f'moss.quiz.{quiz}.{question}.html')
        return moss_report if moss.get_report(url, moss_report) else ''

    # def call_and_get_report(path):
    #     """Retorna uma tupla com a url com o relatório oficial do MOSS e o
    #     nome do arquivo local onde o relatório foi salvo."""
    #     basename, question = os.path.split(path)
    #     basename, quiz = os.path.split(basename)
    #     moss_report = os.path.join(output, f'moss.quiz.{quiz}.{question}.html')
    #     shell_options = ['-x', '-l python' if ext == 'py' else '']

    #     print(f'Calling MOSS... ({path})')
    #     if url := moss.call(shell_options, path, ext):
    #         if moss.get_report(url, moss_report):
    #             return url, moss_report

    #     return url, ''

    def print_similar_groups(moss_report, path):
        """Agrupa estudantes com similaridade maior ou igual ao limiar
        fornecido, acrescentando informações de turma e nota obtida, se
        disponíveis.
        """
        def get_info(student_id):
            file = os.path.join(path, f'{student_id}.{ext}')
            with open(file, 'r') as f:
                name = next(f).strip()
                next(f)  # student_id
                group = next(f).strip()
                grade = next(f).strip()
            return name, group, grade

        groups = [[get_info(student_id) for student_id in sorted(group)]
                  for group in moss.similar(moss_report, threshold)]
        for i, group in enumerate(groups):
            info = [', '.join(student_id for student_id in students)
                    for students in sorted(group)]
            print('\n\t'.join([f'Grupo {i + 1}):'] + info))

    def write_quiz_responses(reports):
        def extra(student_id):
            def grade(student_id, quiz, question):
                if (grade := quiz_grades.get(student_id, {}).get(quiz, {}).get(
                        question, '?')) != '?':
                    grade = f'{100 * float(grade):.2f}%'
                return grade

            group = participants.get(student_id, {}).get('Group', 'Turma ?')
            return {key: {q: [group, grade(student_id, key, q)]
                          for q in questions}
                    for key, questions in quiz_responses[student_id].items()
                    if key != 'Name'}

        participants, quiz_grades, quiz_responses = (reports['participants'],
                                                     reports['quiz.grades'],
                                                     reports['quiz.responses'])
        header_extra = {student_id: extra(student_id)
                        for student_id in quiz_responses}
        return moodle.quiz.responses.write(quiz_responses, output, ext,
                                           ignore, header_extra)

    for path in write_quiz_responses(reports):
        if url := call_moss(path):
            print(url)
            if moss_report := report(path, url):
                print_similar_groups(moss_report, path)
        else:
            print('Unable to get URL from MOSS...')


def main():
    """Processa os argumentos.

    Para cada disciplina/período, lê relatórios específicos para gerar uma
    planilha por turma com as notas e o progresso das atividades.

    Caso especificado, processa o MOSS para os questionários envolvidos.
    """
    args = _parse_args()
    data = _load(args.files)
    for course, periods in data.items():
        for period, reports in periods.items():
            output = os.path.join(args.output, course, period)
            os.makedirs(output, exist_ok=True)

            try:
                _make_csv(reports, output, args.aulas, args.sep)
            except Exception as e:
                print(f'{e} while making CSV  report, skipping...')

            if args.moss:
                _run_MOSS(reports, output, args.ext, args.ignore,
                          args.threshold)


if __name__ == '__main__':
    main()
