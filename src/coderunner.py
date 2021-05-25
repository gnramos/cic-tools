import re
import xml.etree.ElementTree as ET


#######################################################################
def _CDATA(content):
    # https://docs.moodle.org/310/en/Moodle_XML_format
    # HTML fragments should be within CDATA section
    # content = re.sub(r']]>', r']]&gt;', content).strip()
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
    DEFAULTS = {
        'coderunnertype': 'python3_try_except',
        'defaultgrade': '1',
        'displayfeedback': '0',  # Set by quiz | Force Show | Force hide
        'allornothing': '0',
        'penaltyregime': '0, 0, 10, 20, ...',
        'precheck': '2',  # Disabled | Empty | Examples | Selected | All
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
                        # Tentanto eliminar <span> vazios aninhados aninhados.
                        (r'(<span>[.\s\S]*?</span>)', replace_empty_span),
                        (r'(<span>[.\s\S]*?</span>)', replace_empty_span))

        for pattern, repl in replacements:
            html = re.sub(pattern, repl, html)

        return html

    class Fix():
        """Attempts to fix questions settings with given values.

        Uses specific static method, if available, or replaces existing value
        with given one.
        """

        CANNOT_FIX = ['tags', 'testcases']

        @staticmethod
        def questiontext(question):
            name = question.find('name/text').text
            questiontext = question.find('questiontext/text')

            # Handle regex characters.
            name = ''.join(f'\\{c}' if c in r'\{[()]}.' else c for c in name)
            pattern = f'<h(\\d)>{name}</h\\d>'
            if m := re.search(pattern, questiontext.text, flags=re.IGNORECASE):
                if m.group(1) != '3':
                    questiontext.text = re.sub(f'<h(\\d)>{name}</h\\d>',
                                               f'<h3>{name}</h3>',
                                               questiontext.text)
            else:
                questiontext.text = f'<h3>{name}</h3>\n{questiontext.text}'

        @staticmethod
        def set_default(question, setting, value):
            if value is not None and question.find(setting).text != value:
                print(f'Ajustando "{setting}".')
                question.find(setting).text = value

        @staticmethod
        def setting(question, setting, value):
            try:
                if eval(f'CheckList.Check.{setting}(question, value)'):
                    if setting in CheckList.Fix.CANNOT_FIX:
                        print(f'Cannot fix "{setting}"!')
                    elif setting == 'questiontext':
                        print(f'Ajustando "questiontext".')
                        CheckList.Fix.questiontext(question)
                    else:
                        CheckList.Fix.set_default(question, setting, value)
            except AttributeError:
                CheckList.Fix.set_default(question, setting, value)

    class Check():
        """Attempts to check questions settings with given values.

        Uses specific static method, if available, or simply compares existing
        value to the given one.
        """

        @staticmethod
        def answer(question, value):
            return None if question.find('answer').text else 'ausente'

        @staticmethod
        def coderunnertype(question, value):
            question_type = question.find('coderunnertype').text
            issues = None
            if question_type != 'python3_try_except':
                issues = f'tipo de questão é {question_type}'
            if question.find('template'):
                if issues:
                    issues = f'{issues} e '
                issues = f'{issues}já tem template de correção'

            return issues

        @staticmethod
        def default(question, setting, default):
            text = question.find(setting).text
            if text == default:
                return None
            return f'é "{text}" (deveria ser "{default}")'

        @staticmethod
        def generalfeedback(question, value):
            if question.find('generalfeedback/text').text:
                return None
            return 'ausente'

        @staticmethod
        def questiontext(question, values):
            name = question.find('name/text').text
            questiontext = question.find('questiontext/text').text
            issues = ''
            if f'<h3>{name}</h3>' not in questiontext:
                issues = 'não apresenta título'
            if '<span' in questiontext:
                if issues:
                    issues = f'{issues} e '
                issues = f'{issues}tem tag <span>'
            return issues

        @staticmethod
        def setting(question, setting, value=None):
            if setting in ['answer', 'coderunnertype', 'generalfeedback',
                           'questiontext', 'tags', 'testcases']:
                if issues := eval(f'CheckList.Check.{setting}(question, value)'):
                    return f'[{setting}] {issues}'
            elif value is not None:
                if issues := CheckList.Check.default(question, setting, value):
                    return f'[{setting}] {issues}'
            return None

        @staticmethod
        def tags(question, value):
            tags = [test.text for test in question.findall('tags/tag/text')]
            if num_tags := sum(tag.lower() in ('fácil', 'médio', 'difícil')
                               for tag in tags):
                if num_tags > 1:
                    return 'múltiplos níveis de dificuldade'
            else:
                return 'nível de dificuldade ausente'

        @staticmethod
        def testcases(question, value):
            def check(useasexample, mark_value, display_value, num_cases):
                cases = [test for test in question.findall(
                    f'testcases/testcase[@useasexample="{useasexample}"]')
                         if test.find('display/text').text == display_value]

                issues = ''
                for t, test in enumerate(cases):
                    if has_issue := (mark_value != test.attrib['mark']):
                        if issues:
                            issues = f'{issues}. '

                        issues = f'Caso {t} tem pontuação {test.attrib["mark"]} ' \
                                 f'(deveria ser {mark_value})'

                    display = test.find('display/text').text
                    if display != display_value:
                        issues = f'{issues} e' if has_issue else f'Caso {t}'
                        issues = f'{issues} tem visibilidade {display} (deveria ser ' \
                                 f'"{display_value}")'

                if len(cases) != num_cases:
                    type = ('exemplos'
                            if useasexample == '1'
                            else 'visíveis' if display_value == "SHOW"
                            else 'escondidos')
                    issues = f'{issues} e são' if issues else 'São'
                    issues = f'{issues} {len(cases)} testes {type} (deveriam ser ' \
                             f'{num_cases})'

                return issues

            issues = '. '.join(check(*value[case])
                               for case in ('example', 'visible', 'hidden'))

            return issues

    @staticmethod
    def questions(file):
        """Iterates through the questions in the given xml file.

        Each item is the tuple (tree, question) for the quiz's ElementTree and
        question Element).
        """

        # Within the <quiz> tags are any number of <question> tags. One of
        # these <question> tags can be a dummy question with a category type to
        # specify a category for the import/export.
        #
        # Portanto, questões subsequentes à questão de tipo "categoria"
        # pertencem à categoria definida.
        tree = ET.parse(file)
        for question in tree.getroot():
            yield tree, question

    @staticmethod
    def validate(file, values):
        """Validates all the questions in the quiz file to the given setting values.

        Returns a boolean indicating if no issue was found. Also prints any
        found issues (identifying the question).

        Args:
          - file: XML file with quiz/question info.
          - values: dict in the {setting: value} format.
        """
        last_category = current_category = None
        has_issues = False
        for _, question in CheckList.questions(file):
            this_type = question.get('type')
            if this_type == 'category':
                last_category = current_category
                current_category = question.find('category/text').text.replace('$course$/top/', '')
            elif this_type == 'coderunner' and question.find('prototypetype').text == '0':
                if not question.find('tags'):
                    question.append(ET.Element('tags'))

                name = question.find('name/text').text
                for child in question:
                    if issues := CheckList.Check.setting(question, child.tag,
                                                         values.get(child.tag,
                                                                    None)):
                        has_issues = True
                        prefix = f'{current_category} > ' if current_category else ''
                        print(f'{prefix}"{name}": {issues}.')

        return not has_issues

    @staticmethod
    def set_defaults(file, values, outfile=None):
        """Sets the given values for all questions in the quiz file.

        Returns a boolean indicating whether any issue was found. Also prints
        any found issues (identifying the question).

        Args:
          - file: XML file with quiz/question info.
          - values: dict in the {setting: value} format.
          - outfile: string for output file. If not given, overwrites the given
                     file.
        """
        if outfile is None:
            print(f'Overwriting file "{file}".')
            outfile = file

        last_category = current_category = None
        for tree, question in CheckList.questions(file):
            this_type = question.get('type')
            if this_type == 'category':
                last_category = current_category
                current_category = question.find('category/text').text.replace('$course$/top/', '')
            elif this_type == 'coderunner' and question.find('prototypetype').text == '0':
                for child in question:
                    CheckList.Fix.setting(question, child.tag, values.get(child.tag, None))

                CheckList._add_CDATA(question)

        tree.write(outfile, encoding='UTF-8', xml_declaration=True)


if __name__ == '__main__':
    import sys

    # Check & Fix the first given argument.
    if not CheckList.validate(sys.argv[1], CheckList.DEFAULTS):
        CheckList.set_defaults(sys.argv[1], CheckList.DEFAULTS)
