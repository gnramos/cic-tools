import re
import xml.etree.ElementTree as ET


#######################################################################
def _CDATA(content):
    # https://docs.moodle.org/310/en/Moodle_XML_format
    # HTML fragments should be within CDATA section
    content = re.sub(r']]>', r']]&gt;', content).strip()
    element = ET.Element('![CDATA[')
    element.text = content
    return element


# Reference to original function.
_serialize_xml = ET._serialize_xml


def _serialize_xml_with_CDATA(write, elem, qnames, namespaces,
                              short_empty_elements, **kwargs):
    if elem.tag == '![CDATA[':
        write(f'<{elem.tag}{elem.text}]]>\n')
    else:
        return _serialize_xml(write, elem, qnames, namespaces,
                              short_empty_elements, **kwargs)


ET._serialize_xml = ET._serialize['xml'] = _serialize_xml_with_CDATA
#######################################################################


class CheckList():
    """Checks (and updates) questions according to expected values.

    Uses a specific static method per setting, if available.
    """

    UNFIXABLE = ['tags', 'testcases']
    DEFAULTS = {
        'coderunnertype': 'python3_try_except',
        'defaultgrade': ['1.0000000', '1'],
        'displayfeedback': '0',  # [Set by quiz, Force Show, Force hide]
        'allornothing': '0',
        'penaltyregime': '0, 0, 10, 20, ...',
        'precheck': '2',  # [Disabled, Empty, Examples, Selected, All]
        'validateonsave': '1',
        'testcases': {'example': ('1', '0.0010000', 'SHOW', 3),
                      'visible': ('0', '1.0000000', 'SHOW', 3),
                      'hidden': ('0', '1.0000000', 'HIDE', 4)}
        }

    @staticmethod
    def _add_CDATA(question):
        # Tags with possible special characters
        html_fragments = ('answer', 'answerpreload', 'generalfeedback/text',
                          'questiontext/text', 'template', 'templateparams',
                          'testcases/expected/text', 'testcases/extra/text',
                          'testcases/stdin/text', 'testcases/testcode/text')

        # for element in question.findall('.//*[@format="html"]'):
        for tag in html_fragments:
            element = question.find(tag)
            if element is not None and element.text:
                text = element.text
                element.clear()
                element.append(_CDATA(CheckList._clean_html(text)))

    # _check_SETTING methods
    @staticmethod
    def _check_answer(question, value):
        return None if question.find('answer').text else 'ausente'

    @staticmethod
    def _check_coderunnertype(question, value):
        question_type = question.find('coderunnertype').text
        issues = ''
        if question_type != 'python3_try_except':
            issues = f'tipo de questão é {question_type}'
        if question.find('template'):
            if issues:
                issues = f'{issues} e '
            issues = f'{issues}já tem template de correção'

        return issues

    @staticmethod
    def _check_default(question, setting, default):
        text = question.find(setting).text
        if text == default:
            return None
        if isinstance(default, list):
            if text in default:
                return None
            return f'é "{text}" (deveria estar em "{default}")'
        return f'é "{text}" (deveria ser "{default}")'

    @staticmethod
    def _check_generalfeedback(question, value):
        if question.find('generalfeedback/text').text:
            return None
        return 'ausente'

    @staticmethod
    def _check_questiontext(question, values):
        name = question.find('name/text').text
        questiontext = question.find('questiontext/text').text
        issues = ''
        if f'<h3>{name}</h3>' not in questiontext:
            issues = 'não apresenta título no formato previsto'
        if '<span' in questiontext:
            if issues:
                issues = f'{issues} e '
            issues = f'{issues}tem tag <span>'
        return issues

    @staticmethod
    def _check_setting(question, setting, value=None):
        if hasattr(CheckList, f'_check_{setting}'):
            if issues := eval(f'CheckList._check_{setting}(question, value)'):
                return f'[{setting}] {issues}'
        elif value is not None:
            if issues := CheckList._check_default(question, setting, value):
                return f'[{setting}] {issues}'
        return None

    @staticmethod
    def _check_tags(question, value):
        tags = [test.text for test in question.findall('tags/tag/text')]
        if num_tags := sum(tag.lower() in ('fácil', 'médio', 'difícil')
                           for tag in tags):
            if num_tags > 1:
                return 'múltiplos níveis de dificuldade'
        else:
            return 'nível de dificuldade ausente'

    @staticmethod
    def _check_testcases(question, value):
        def check(useasexample, mark_value, display_value, num_cases):
            cases = [test for test in question.findall(
                f'testcases/testcase[@useasexample="{useasexample}"]')
                if test.find('display/text').text == display_value]

            issues = ''
            for t, test in enumerate(cases):
                if has_issue := (mark_value != test.attrib['mark']):
                    if issues:
                        issues = f'{issues}. '

                    issues = (f'Caso {t} tem pontuação '
                              f'{test.attrib["mark"]} '
                              f'(deveria ser {mark_value})')

                display = test.find('display/text').text
                if display != display_value:
                    issues = f'{issues} e' if has_issue else f'Caso {t}'
                    issues = (f'{issues} tem visibilidade {display} '
                              f'(deveria ser "{display_value}")')

            if len(cases) != num_cases:
                if useasexample == '1':
                    test_type = 'exemplos'
                elif display_value == 'SHOW':
                    test_type = 'visíveis'
                else:
                    test_type = 'escondidos'
                issues = f'{issues} e são' if issues else 'São'
                issues = (f'{issues} {len(cases)} testes {test_type} '
                          f'(deveriam ser {num_cases})')

            return issues

        issues = [check(*value[case])
                  for case in ('example', 'visible', 'hidden')]

        return '. '.join(x for x in issues if x)

    @staticmethod
    def _clean_html(html):
        def replace_empty_span(matchobj):
            return matchobj.group(0)[6:-7]

        replacements = (  # (r'(<(?!\/)[^>]+>)+(<\/[^>]+>)+', ''),
                        (r'( style="font-size: \d+\.\d+rem;"?)', ''),
                        (r'( style="")', ''),
                        (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                        (r'&nbsp;', ' '),
                        (r'<([^ ]*?)><br></(\1)>', ''),
                        (r'<([^ ]*?)></(\1)>', ''),
                        # Tentanto eliminar <span> vazios aninhados.
                        (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                        (r'(<span>[.\s\S]*?</span>)', replace_empty_span))

        for pattern, repl in replacements:
            html = re.sub(pattern, repl, html)

        return html

    @staticmethod
    def _fix_default(question, setting, value):
        if value is not None and question.find(setting).text != value:
            question.find(setting).text = value

    @staticmethod
    def _fix_questiontext(question, value=None):
        name = question.find('name/text').text
        questiontext = question.find('questiontext/text')

        # Handle regex characters.
        name = ''.join(f'\\{c}' if c in r'\{[()]}.' else c for c in name)
        pattern = f'<h(\\d)>(.*?)({name})(.*?)</h\\d>'
        if m := re.search(pattern, questiontext.text, flags=re.IGNORECASE):
            if (m.group(1) != '3' or
                    any(p for p in m.group(2, 4)) or
                    name != m.group(3)):
                questiontext.text = re.sub(pattern, '', questiontext.text,
                                           flags=re.IGNORECASE)
        questiontext.text = f'<h3>{name}</h3>\n{questiontext.text.lstrip()}'

    @staticmethod
    def _fix_setting(category, question, setting, value, sep=' > '):
        if setting in CheckList.UNFIXABLE:
            return f'Não é possível ajustar "{setting}"!'

        if hasattr(CheckList, f'_fix_{setting}'):
            exec(f'CheckList._fix_{setting}(question, value)')
        else:
            CheckList._fix_default(question, setting, value)

        return ''

    @staticmethod
    def _coderunner_questions(file):
        """Iterates through the questions in the given XML file.

        Each item is the tuple (tree, category, question) for the quiz's
        ElementTree and question's category and Element, respectively.
        """

        tree, category = ET.parse(file), None
        for question in tree.getroot():
            # As per Moodle documentation: "Within the <quiz> tags are any
            # number of <question> tags. One of these <question> tags can be a
            # dummy question with a category type to specify a category for the
            # import/export." Thus, all questions following a "category" type
            # belong to that category in the question bank.
            if question.get('type') == 'category':
                category = question.find('category/text').text.replace(
                    '$course$/top/', '')
            elif (question.get('type') == 'coderunner' and
                  question.find('prototypetype').text == '0'):
                yield tree, category, question

    @staticmethod
    def validate(file, outfile=None, values=DEFAULTS, set_defaults=False,
                 yes_to_all=False, sep=' > '):
        """Validates all questions in quiz file with the given setting values.

        Returns a boolean indicating if no issue was found. Also prints any
        found issues (identifying the question).

        Args:
          - file: XML file with quiz/question info.
          - outfile: string with the file to write the validated quiz to.
                     (default: same as file)
          - values: dict in the {setting: value} format.
          - set_defaults: boolean indicating whether to replace the
                          non-default values with the default ones.
                          (default: False)
          - yes_to_all: boolean indicating whether to prompt user for
                        confirmation for every issue found.
                        (default: False)
          - sep: string for separating question category levels.
                 (default: ' > ')
        """
        if outfile is None:
            outfile = file

        has_issues = False
        for tree, category, question in CheckList._coderunner_questions(file):
            if not question.find('tags'):
                question.append(ET.Element('tags'))

            name = question.find('name/text').text
            for child in question:
                setting, value = child.tag, values.get(child.tag, None)
                issues = CheckList._check_setting(question, setting, value)

                if issues:
                    category, has_issues = category.replace("/", sep), True
                    print(f'{category}{sep}{name}: {issues}.')

                    if not set_defaults:
                        continue

                    set_default = yes_to_all
                    if not yes_to_all:
                        response = input('Tentar ajustar o valor de '
                                         f'"{setting}" [Y/N]? ')
                        set_default = response in 'yY'

                    if set_default:
                        issue = CheckList._fix_setting(category, question,
                                                       setting, value, sep)
                        if not issue:
                            issue = f'[{setting}] ajustado!'
                        print(f'\t{issue}')
                    print()

            CheckList._add_CDATA(question)

        tree.write(outfile, encoding='UTF-8', xml_declaration=True)
        return not has_issues


def __print_dict__(d, indent=''):
    for k, v in d.items():
        if isinstance(v, dict):
            print(f'{indent} - {k}:')
            __print_dict__(v, f'    {indent}')
        else:
            print(f'{indent} - {k}: {v}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Quiz XML file.')
    parser.add_argument('-l', '--list_defaults', action='store_true',
                        help='List default values.')
    parser.add_argument('-d', '--set_defaults', action='store_true',
                        help='Set default values, overwrites the given file '
                        'unless the outfile is given.')
    parser.add_argument('-o', '--outfile',
                        help='Output file if overwriting any values.')
    parser.add_argument('-y', '--yes_to_all', action='store_true',
                        help='Answer YES to any iteractions.')
    args = parser.parse_args()

    if args.list_defaults:
        print('Default values:')
        __print_dict__(CheckList.DEFAULTS)
    else:
        CheckList.validate(args.file, args.outfile,
                           set_defaults=args.set_defaults,
                           yes_to_all=args.yes_to_all)
