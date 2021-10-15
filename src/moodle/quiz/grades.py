"""Processa o relatório de notas de discentes no curso.

Para obter o arquivo:
    1. Acesse o relatório via:
        Questionário > Configurações (engrenagem) > Resultados > Notas
    2. Selecione o grupo desejado, se for o caso.
    3. Selecione as 'Tentativas que estão' 'Finalizada'.
    4. Mostre o relatório.
    5. Faça download do arquivo no formato CSV.
"""

import csv
import unicodedata


def read(file, quiz, total_only=False):
    """Lê os dados do arquivo e os retorna como um dicionário.

    Argumentos:
    file -- o arquivo CSV a ser lido.
    quiz -- nome do questionário sendo processado.
    total_only -- booleano indicando se considera apenas as notas consolidadas
                  (total).
    """
    def parse(header, grade_info):
        question, weight = header.split(' /')
        if grade_info == '-':
            grade = 0
        else:
            grade = (float(grade_info.replace(',', '.')) /
                     float(weight.replace(',', '.')))
        return question.split()[-1], grade

    grades = {}
    with open(file) as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

        header = [unicodedata.normalize('NFKD', h)
                  for h in next(csvreader)]  # skip header
        if total_only:
            grades_idx = [i for i, col in enumerate(header)
                          if col.endswith(' total (Real)')]
            grades_idx.append(header.index('Nota Final (Real)'))
        else:
            grades_idx = range(8, len(header))  # 8 is 1st occurrence of grade.

        for row in csvreader:
            if (s_id := row[2].split('@')[0]).isnumeric():
                grades[s_id] = {'Name': f'{row[1]} {row[0]}', quiz: {}}
                for i in grades_idx:
                    question, grade = parse(header[i], row[i])
                    grades[s_id][quiz][question] = grade
    return grades


def main():
    """Processa argumentos da linha de comando."""

    from argparse import ArgumentParser

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('file', help='O arquivo CSV a ser lido.')
    parser.add_argument('-q', '--quiz', default='Questionário',
                        help='O nome do questionário.')
    parser.add_argument('-t', '--total_only', action='store_true',
                        help='Considerar apenas notas consolidadas (total).')

    args = parser.parse_args()
    grades = read(args.file, args.quiz, args.total_only)
    for info in grades.values():
        grades_list = ', '.join(str(g) for g in info[args.quiz].values())
        print(f'{info["Name"]}: {args.quiz} ({grades_list})')


if __name__ == '__main__':
    main()
