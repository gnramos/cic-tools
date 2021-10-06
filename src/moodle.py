import csv
import json
import os
import re
import unicodedata
import utils


class Grades(utils.Students):
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

    def __init__(self, file, total_only=False):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo CSV a ser lido.
        """

        with open(file) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

            header = [unicodedata.normalize('NFKD', h)
                      for h in next(csvreader)]  # skip header
            if total_only:
                grades_idx = [i for i, col in enumerate(header)
                              if col.endswith(' total (Real)')]
                grades_idx.append(header.index('Nota Final (Real)'))
            else:
                # 6 is the first grade, last column is "last download" info
                grades_idx = range(6, len(header) - 1)

            for row in csvreader:
                s_id = row[5].split('@')[0]  # e-mail
                self[s_id] = {'Name': f'{row[0]} {row[1]}', 'Grades': {}}
                for i in grades_idx:
                    grade = 0 if row[i] == '-' else float(row[i].replace(',', '.'))
                    self[s_id]['Grades'][header[i]] = grade


class Participants(utils.Students):
    """Processa o relatório de participação discente no curso.

    Acrescenta a chave 'Group' que indica os grupos (turma) do discente.

    Para obter o arquivo:
        1. Acesse o relatório via:
            Este Curso > Pessoas
        2. Aperte o botão "Selecionar todos os X usuários".
        3. Salve a página como HTML (completo).

    Apenas o arquivo HTML é necessário.
    """

    def __init__(self, file, group=''):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo HTML a ser lido.
        group -- nome [parcial] do grupo desejado.
        """

        with open(file) as htmlfile:
            html = htmlfile.read()

        pattern = re.compile(r'<label for=.*?user\d+.*?<img.*?>(.*?)</a>.*?'
                             r'(\d+)@aluno.unb.br[.\s\S]*?'
                             r'title="Editar grupos.*?>[\s\S]'
                             r' *(\w.*)[\s\S]')
        for name, s_id, s_group in pattern.findall(html):
            if group in s_group:
                self[s_id] = {'Name': name, 'Group': s_group}


class Progress(utils.Students):
    """Processa o relatório de progresso de discentes no curso.

    Acrescenta "Frequência" e "Faltas" do discente, em termos percentuais.

    Para obter o arquivo:
        1. Acesse o relatório via:
            Administração do curso > Relatórios (aba) > Conclusão de atividades
        2. Selecione o grupo desejado, se for o caso.
        3. Faça o download em formato de planilha (UTF-8. csv).
    """

    def __init__(self, file):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo CSV a ser lido.
        """

        with open(file) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

            header = next(csvreader)  # skip header
            activities = (len(header) - 2) / 2

            for row in csvreader:
                s_id, _ = row[1].split('@')
                frequency = 100 * row.count('Concluído') // activities
                self[s_id] = {'Name': row[0],
                              'Frequência': frequency,
                              'Faltas': 100 - frequency}


class Quiz():
    class Grades(utils.Students):
        def __init__(self, file):
            """Construtor.

            Carrega os dados do arquivo.

            Argumentos:
            file -- o arquivo CSV a ser lido.
            """

            def grade(value, weight):
                if value == '-':
                    return 0

                value = float(value.replace(',', '.'))
                if weight == '1,00':
                    return value
                return value / float(weight.replace(',', '.'))

            def skip_last(iterator):

                prev = next(iterator)
                for item in iterator:
                    yield prev
                    prev = item

            quiz = file.split('.')[-2]

            with open(file) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

                header = [q.split(' /') for q in next(csvreader)]  # skip header
                # weight = float(header[7].split('/')[-1].replace(',', '.'))
                # 8  is the first grade, last column is "last download" info
                grades_idx = range(8, len(header))

                for row in skip_last(csvreader):
                    s_id = row[2].split('@')[0]  # e-mail
                    self[s_id] = {'Name': f'{row[1]} {row[0]}',
                                  'Quiz': {quiz: [grade(row[i], header[i][1])
                                                  for i in grades_idx]}}

    class Responses(utils.Students):
        """Processa o relatório de respostas de um questionário.

        Acrescenta "Quiz", um dicionário cujas chaves são índices das questões no
        questionário e os valores outro dicionário com duas chaves: 'attempt' que
        define a resposta do discente e 'answer' que define a resposta correta.

        Para obter o arquivo:
            1. Acesse o relatório via:
                Questionário > Configurações (engrenagem) > Respostas
            2. Selecione o grupo desejado, se for o caso.
            3. Selecione as 'Tentativas que estão' 'Finalizada'.
            4. Mostre apenas 'resposta' e 'resposta correta'.
            5. Mostre o relatório.
            6. Faça download do arquivo no formato JSON (UTF-8 .json).
        """

        def __init__(self, file):
            """Construtor.

            Carrega os dados do arquivo.

            Argumentos:
            file -- o arquivo JSON a ser lido.
            """

            with open(file) as f:
                data = json.load(f)

            for d in data[0]:
                s_id, _ = d[2].split('@')
                self[s_id] = {'Name': f'{d[1]} {d[0]}',
                              'Quiz': {q: {'attempt': d[i].strip(' \r\n'),
                                           'answer': d[i + 1].strip(' \r\n')}
                                       for q, i in enumerate(range(8, len(d), 2))}}

        def _make_header(self, student_info, ext):
            if ext == 'py':
                return '\n'.join(f'# {i}' for i in student_info)

            if ext in ['c', 'cpp']:
                cmt = '\n   '.join(student_info)
                return f'/* {cmt} */'

            return ' '.join(student_info)

        def _has_response(self, content):
            return content.count('\n') > 1

        def to_files(self, path, ext='py', ignore=[], participants={}):
            """Grava cada resposta em um arquivo específico.

            Argumentos:
            path -- diretório para armazenar os arquivos.
            ext -- extensão do arquivo a conter a resposta.
            ignore -- lista com índices de questões que devem ser ignoradas.
            participants -- dicionário com a informação de turma (veja class
                            Participants)
            """

            for s_id, info in self.items():
                group = participants.get(s_id, {}).get('Group', '?')
                student_info = [info['Name'], s_id, group]
                header = f'{self._make_header(student_info, ext)}\n\n'

                for q, src in info['Quiz'].items():
                    if (q not in ignore and
                            self._has_response(src.get('attempt', ''))):
                        q_dir = os.path.join(path, f'Q{q}')
                        os.makedirs(q_dir, exist_ok=True)
                        response_file = os.path.join(q_dir,
                                                     f'{s_id}.{ext}')
                        with open(response_file, 'w') as f:
                            f.write(f'{header}\n\n{src["attempt"]}')

                        response_file = os.path.join(q_dir, f'CORRECT.{ext}')
                        if not os.path.isfile(response_file):
                            with open(response_file, 'w') as f:
                                f.write(src['answer'])
