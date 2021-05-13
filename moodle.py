import csv
import json
import locale
import os
import re


class MoodleBase(dict):
    """Classe base para manipulação de dados de relatórios do Moodle.

    Funciona como um dicionário, de modo que as chaves são as matrículas e cada
    item é um dicionário com pelo menos a chave 'Name' contendo o nome do
    discente.

    """

    def __str__(self):
        return '\n'.join(f'{self[k]["Name"]}, {k}' for k in self.sorted_keys())

    def sorted_keys(self):
        """Itera pelas chaves do dicionário em ordem alfabética."""
        for k in sorted(self.keys(),
                        key=lambda x: locale.strxfrm(self[x]['Name'])):
            yield k


class Grades(MoodleBase):
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

    def __init__(self, file):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo CSV a ser lido.
        """

        with open(file) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')

            header = next(csvreader)  # skip header
            grades_idx = [i for i, col in enumerate(header)
                          if col.endswith(' total (Real)')]
            grades_idx.append(header.index('Nota Final (Real)'))

            for row in csvreader:
                first_name, last_names, s_id = row[:3]
                self[s_id] = {'Name': f'{first_name} {last_names}'}
                for i in grades_idx:
                    self[s_id][header[i]] = float(row[i])


class Participants(MoodleBase):
    """Processa o relatório de participação discente no curso.

    Acrescenta a chave 'Group' que indica os grupos (turma) do discente.

    Para obter o arquivo:
        1. Acesse o relatório via:
            Este Curso > Pessoas
        2. Aperte o botão "Selecionar todos os X usuários".
        3. Salve a página como HTML (completo).

    Apenas o arquivo HTML é necessário.
    """

    def __init__(self, file):
        """Construtor.

        Carrega os dados do arquivo.

        Argumentos:
        file -- o arquivo HTML a ser lido.
        """

        with open(file) as htmlfile:
            html = htmlfile.read()

        pattern = (r'<label for=.*?user\d+.*?<img.*?>(.*?)</a>.*?'
                   r'(\d+)@aluno.unb.br[.\s\S]*?title="Editar grupos.*?>[\s\S]'
                   r' +(\w.*)[\s\S]')
        for name, s_id, group in re.findall(pattern, html):
            self[s_id] = {'Name': name, 'Group': group}


class Progress(MoodleBase):
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


class QuizResponse(MoodleBase):
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

    def to_files(self, path, ext='py', ignore_list=[]):
        """Grava cada resposta em um arquivo específico.

        Argumentos:
        path -- diretório para armazenar os arquivos.
        ext -- extensão do arquivo a conter a resposta.
        ignore_list -- lista com índices de questões que devem ser ignoradas.
        """

        for s_id, info in self.items():
            student_info = [info["Name"], f'{s_id}']
            header = f'{self._make_header(student_info, ext)}\n\n'

            for q, src in info['Quiz'].items():
                if q not in ignore_list and self._has_response(src.get('attempt', '')):
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


locale.setlocale(locale.LC_ALL, '')
