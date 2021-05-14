import locale


class Students(dict):
    """Classe base para manipulação de dados de alunos.

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


locale.setlocale(locale.LC_ALL, '')
