"""Processa o relatório de notas discentes no curso.

Acrescenta as notas grades_idx das atividades avaliadas e afinal do discente.

Para obter o arquivo:
    1. Acesse o relatório via:
        Este Curso > Notas > Exportar (aba)
    2. Selecione o formato "Arquivo texto" (aba).
    3. Selecione o grupo desejado, se for o caso.
    4. Selecione os itens que se deseja exportar.
    5. Selecione o formato de exportação "Real" com separador "Vírgula".
"""

import csv
import unicodedata


def read(file, total_only=False):
    """Lê os dados do arquivo e os retorna como um dicionário.

    Argumentos:
    file -- o arquivo CSV a ser lido.
    total_only -- booleano indicando se considera apenas as notas consolidadas
                  (total).
    """
    grades = {}
    with open(file) as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

        header = [unicodedata.normalize('NFKD', h).replace('[Questionário] ', '')
                  for h in next(csvreader)]  # skip header
        header.pop(-1)  # Último download realizado neste curso.

        if total_only:
            grades_idx = [i for i, col in enumerate(header)
                          if col.endswith(' total (Real)')]
            grades_idx.append(header.index('Nota Final (Real)'))
        else:
            grades_idx = range(6, len(header))

        header = [h.replace(' (Real)', '') for h in header]

        for row in csvreader:
            if (s_id := row[5].split('@')[0]).isnumeric(): # e-mail
                grades[s_id] = {'Name': f'{row[0]} {row[1]}', 'Grades': {}}
                for i in grades_idx:
                    grade = 0 if row[i] == '-' else float(row[i].replace(',',
                                                                         '.'))
                    grades[s_id]['Grades'][header[i]] = grade

    return grades


def main():
    """Processa argumentos da linha de comando."""

    from argparse import ArgumentParser

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('file', help='O arquivo CSV a ser lido.')
    parser.add_argument('-t', '--total_only', action='store_true',
                        help='Considerar apenas notas consolidadas (total).')

    args = parser.parse_args()
    grades = read(args.file, args.total_only)
    for info in sorted(grades.values(), key=lambda x: x['Name']):
        print(info['Name'])
        for quiz, grade in info['Grades'].items():
            print(f'\t{quiz}: {grade}')


if __name__ == '__main__':
    main()
