import csv
import utils


class Teams(utils.Students):
    """Processa o relatório de presença de uma reunião na plataforma Teams.

    Para obter o arquivo:
        1. Acesse a plataforma Teams.
        2. Acesse o calendário disponibilizado e abra os detalhes da reunião.
        3. Na aba "Chat", baixe o arquivo CSV.
    """

    def __init__(self, file, students_only=True):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo CSV a ser lido.
        """

        with open(file, encoding='utf-16') as csvfile:
            csvreader = csv.reader(csvfile, delimiter='\t')

            next(csvreader)  # Meeting Summary
            next(csvreader)  # Total Number of Participants
            next(csvreader)  # Meeting Title
            next(csvreader)  # Meeting Start Time
            next(csvreader)  # Meeting End Time
            next(csvreader)  # Blank line
            next(csvreader)  # Header: Full Name | Join Time | Leave Time | Duration | Email | Role
            for row in csvreader:
                name, s_id = row[0], row[4].split('@')[0]
                if not students_only or s_id.isdigit():
                    self[s_id] = {'Name': name}
