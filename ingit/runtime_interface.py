"""Interactive runtime interface of ingit."""

import collections.abc
import logging
import sys
import typing as t

import readchar

_INTERRUPTS = {chr(3)}

_NEWLINES = {'\n', '\r'}

OUT = logging.getLogger('ingit.interface.print')

OUT_HANDLER = logging.StreamHandler(sys.stdout)
OUT_HANDLER.setLevel(logging.NOTSET)
OUT.addHandler(OUT_HANDLER)


def default_template(question, answers, default):
    """Print a question with candidate answers, with the default marked accordingly.

    This is the default template for ask().
    """
    case_insensitive_answers = {_.lower() for _ in answers}
    case_insensitive = len(case_insensitive_answers) == len(answers)
    if case_insensitive:
        answers_print = [(a.upper() if a == default else a) for a in answers]
        return f'{question} [{"/".join(answers_print)}] '
    return f'{question} [{"/".join(answers)}] [default={default}] '


def ask(question: str, answers: t.Sequence[str] | None = None, default: t.Optional[str] = None,
        autoanswer: bool | str | None = None,
        template: collections.abc.Callable = default_template) -> str:
    """Ask a question that is to be answered with a single keystroke.

    By default, it is asked like this: "question [y/N] ".

    :param question: a proposition that is to be answered
    :param answers: list of valid answers, list of lower-case letters; if None, use ['y', 'n']
    :param default:
        a default answer, lower-case letter; if None, use last of the answer, 'n' by default
    :param autoanswer:
        answer to be automatically given; if True, the default answer will be given
    :param template: a function taking question and answers and returning string
    :return: a lower-case letter that is the answer to the question
    """
    assert isinstance(question, str), type(question)
    if answers is None:
        answers = ['y', 'n']
    assert isinstance(answers, collections.abc.Sequence), type(answers)
    assert answers, answers
    assert all(
        isinstance(_, str) and len(_) == 1 and _ not in _INTERRUPTS and _ not in _NEWLINES
        for _ in answers), answers
    assert len(answers) == len(set(answers)), answers
    if default is None:
        default = answers[-1]
    assert isinstance(default, str), type(default)
    assert default in answers, (default, answers)
    # if autoanswer is None and not RuntimeInterfaceConfig.interactive:
    #    autoanswer = True
    if autoanswer is True:
        autoanswer = default
    assert autoanswer is None or isinstance(autoanswer, str), type(autoanswer)
    assert autoanswer is None or autoanswer in answers, (autoanswer, answers)
    assert callable(template), type(template)
    print(template(question, answers, default), end='', flush=True)
    case_insensitive_answers = {_.lower() for _ in answers}
    case_insensitive = len(case_insensitive_answers) == len(answers)
    if case_insensitive:
        answers = list(case_insensitive_answers)
        default = default.lower()
        if autoanswer is not None:
            autoanswer = autoanswer.lower()
    answer = autoanswer
    while answer not in answers:
        if answer is not None:
            print(answer, end='', flush=True)
        answer = readchar.readchar()
        assert answer is not None
        if case_insensitive:
            answer = answer.lower()
        if answer in _INTERRUPTS:
            raise KeyboardInterrupt()
        if answer in _NEWLINES:
            answer = default
    print(answer)
    return str(answer)
