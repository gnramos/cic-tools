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
        PERÍODO: período de realização da disciplina no formato ano-semestre
                (P em {0,1,2}),
        ORIGEM: plataforma de origem o relatório,
        RELATORIO: tipo de relatório:
                   - attendance: relatório de presença de reunião via Teams:
                       - EXTRA:  data da reunião (formato YYYY-MM-DD).
                   - grades: relatório de notas do Moodle.
                   - participants: página de usuários do Moodle.
                   - progress: relatório de atividades completadas do Moodle.
                   - quiz.grades: relatório de notas de questionários do
                                  Moodle. Neste caso, EXTRA identifica o
                                  questionário.
                   - quiz.responses: relatório de submissões de questionários
                                     do Moodle. Neste caso, EXTRA: identifica o
                                     questionário.
        EXTRA: informação adicional sobre o arquivo (opcional),
        EXT: extensão o arquivo,

    A estrutura do dicionário é: [curso][período][info]
    """

    FILE_PATTERN = re.compile(r'([A-Z][0-Z]+)\.'         # CURSO
                              r'(\d{4}-[0-2])\.'         # PERIODO
                              r'(moodle|teams)\.'        # ORIGEM
                              r'(attendance|grades|'     # RELATORIO (abordagem
                              r'participants|progress|'  # gulosa, a ordem faz
                              r'quiz\.grades|'           # diferença)
                              r'quiz\.responses|quiz)'
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
                data[course] = {period: {}}
                attendance[course] = {period: {}}
                attendance[course][period]['Total'] = 0

            if report == 'attendance':
                attendance[course][period]['Total'] += 1
                for id in current:
                    attendance[course][period][id] += 1
            else:
                if report not in data[course][period]:
                    data[course][period][report] = current
                elif extra:
                    for id, value in current.items():
                        if id not in data[course][period][report]:
                            data[course][period][report][id] = {}
                        data[course][period][report][id].update(value)

    for course, periods in attendance.items():
        for period, info in periods.items():
            data[course][period]['attendance'] = {
                id: (100 * info.get(id, 0)) // info['Total']
                for id in info if id != 'Total'}

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
        return sep.join(['Matrícula', 'Nome', grades_header,
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
        absent = reports['progress'].get(id, {}).get("Faltas", "?") == '?'

        if absent == '?':
            return '?'

        if num_classes:
            return (int(absent) * num_classes) // 100
        return 100 - int(absent)  # percentual do progresso

    def students_by_groups():
        groups = defaultdict(list)
        for id, info in reports['participants'].items():
            groups[info['Group']].append(id)
        return groups

    def student_csv(id):
        student = sep.join([id, reports['participants'][id]['Name']])
        return sep.join([student, grades_csv(id), str(progress(id))])

    locale.setlocale(locale.LC_ALL, '')

    groups = students_by_groups()
    grades_header = grades_csv_header()

    for group, ids in groups.items():
        file = os.path.join(output,
                            f'{group.replace("/", "-").replace(" ", "_")}.csv')
        with open(file, 'w') as f:
            f.write(f'{full_csv_header()}\n')

            for id in sorted(ids, key=lambda k: locale.strxfrm(
                                      reports['participants'][k]['Name'])):
                if reports['participants'][id]['Role'] != 'Estudante':
                    continue

                f.write(f'{student_csv(id)}\n')


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
    def call_and_get_report(path):
        """Retorna uma tupla com a url com o relatório oficial do MOSS e o
        nome do arquivo local onde o relatório foi salvo."""
        basename, question = os.path.split(path)
        basename, quiz = os.path.split(basename)
        moss_report = os.path.join(output, f'moss.quiz.{quiz}.{question}.html')
        shell_options = ['-x', '-l python' if ext == 'py' else '']

        print(f'Calling MOSS... ({path})')
        if url := moss.call(shell_options, path, ext):
            if moss.get_report(url, moss_report):
                return url, moss_report

        return url, ''

    def print_similar_groups(moss_report, path):
        """Agrupa estudantes com similaridade maior ou igual ao limiar
        fornecido, acrescentando informações de turma e nota obtida, se
        disponíveis.
        """
        groups = []
        for group in moss.similar(moss_report, threshold):
            similar_group = []
            for id in sorted(group):
                file = os.path.join(path, f'{id}.{ext}')
                with open(file, 'r') as f:
                    name = next(f).strip()
                    next(f)  # id
                    group = next(f).strip()
                    grade = next(f).strip()
                similar_group.append((name, group, grade))
            groups.append(similar_group)

        for i, group in enumerate(groups):
            info = [f'Grupo {i + 1}):'] + [', '.join(i for i in student)
                                           for student in sorted(group)]
            print('\n\t'.join(info))

        return groups

    def write_quiz_responses():
        def extra(id):
            def grade(id, quiz, question):
                if (grade := quiz_grades.get(id, {}).get(quiz, {}).get(
                        question, '?')) != '?':
                    grade = f'{100 * float(grade):.2f}%'
                return grade

            group = participants.get(id, {}).get('Group', 'Turma ?')
            return {key: {q: [group, grade(id, key, q)]
                          for q in questions}
                    for key, questions in quiz_responses[id].items()
                    if key != 'Name'}

        header_extra = {id: extra(id)
                        for id in quiz_responses}
        return moodle.quiz.responses.write(quiz_responses, output, ext,
                                           ignore, header_extra)

    participants, quiz_grades, quiz_responses = (reports['participants'],
                                                 reports['quiz.grades'],
                                                 reports['quiz.responses'])
    for path in write_quiz_responses():
        url, moss_report = call_and_get_report(path)
        print(url if url else 'Unable to get URL from MOSS...')

        if moss_report:
            print_similar_groups(moss_report, path)


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

            _make_csv(reports, output, args.aulas, args.sep)

            if args.moss:
                _run_MOSS(reports, output, args.ext, args.ignore,
                          args.threshold)


if __name__ == '__main__':
    main()
