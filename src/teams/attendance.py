"""Processa o relatório de presença de uma reunião na plataforma Teams.

Para obter o arquivo:
    1. Acesse a plataforma Teams.
    2. Acesse o calendário disponibilizado e abra os detalhes da reunião.
    3. Na aba "Chat", baixe o arquivo CSV.
"""
import csv


def read(file, students_only=True):
    """Lê os dados do arquivo e os retorna como um dicionário.

    Argumentos:
    file -- o arquivo CSV a ser lido.
    students_only -- booleano indicando se considera apenas as notas
                     consolidadas (total).
    """
    attendance = {}

    with open(file, encoding='utf-16') as csvfile:
        csvreader = csv.reader(csvfile, delimiter='\t')
        try:
            while ['Full Name'] != next(csvreader)[:1]:
                pass
            for row in csvreader:
                name, s_id = row[0], row[4].split('@')[0]
                if not students_only or s_id.isdigit():
                    attendance[s_id] = {'Name': name}
        except StopIteration:
            pass

    return attendance


def main():
    """Processa argumentos da linha de comando."""

    from argparse import ArgumentParser

    parser = ArgumentParser(read.__doc__.split('\n')[0])
    parser.add_argument('files', nargs='+', help='Arquivos CSV a serem lidos.')
    parser.add_argument('-s', '--students_only', action='store_true',
                        help='Considerar apenas alunos.')

    args = parser.parse_args()

    attendance, num_files = {}, 0
    for file in args.files:
        if att := read(file, args.students_only):
            for s_id, info in att.items():
                if s_id not in attendance:
                    attendance[s_id] = {'Name': info['Name'], 'Attendance': 0}
                attendance[s_id]['Attendance'] += 1
            num_files += 1
    for info in sorted(attendance.values(), key=lambda x: x['Name']):
        print(f'{info["Name"]} {100 * info["Attendance"] // num_files}%')


if __name__ == '__main__':
    main()
