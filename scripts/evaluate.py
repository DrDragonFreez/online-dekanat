import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
def norm(value):
    if value is None or isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise ValueError('Ожидалась строка, boolean или null')
    value = unicodedata.normalize('NFC', value).casefold().replace('ё', 'е')
    for char in '«»“”„':
        value = value.replace(char, '"')
    return re.sub(r'\s+', ' ', value).strip()
def exact_value(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, bool):
        return a is b
    return norm(a) == norm(b)
def unique_strings(value, context):
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f'{context}: ожидался массив строк')
    if len(value) != len(set(value)):
        raise ValueError(f'{context}: повторяющиеся значения')
    return set(value)
def keys(obj, required, context):
    if not isinstance(obj, dict):
        raise ValueError(f'{context}: ожидался объект')
    if set(obj) != set(required):
        raise ValueError(
            f'{context}: нужны ключи {sorted(required)}, получены {sorted(obj)}'
        )
def by_id(items, key, context):
    if not isinstance(items, list):
        raise ValueError(f'{context}: ожидался массив')
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            raise ValueError(f'{context}: неверный {key}')
        if item[key] in result:
            raise ValueError(f'{context}: повтор {item[key]}')
        result[item[key]] = item
    return result
def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
def evaluate(reference, prediction):
    keys(prediction, ['version', 'documents'], 'results')
    if prediction['version'] != '1.0':
        raise ValueError('Ожидалась version 1.0')
    refs = by_id(reference['documents'], 'document_id', 'reference.documents')
    preds = by_id(prediction['documents'], 'document_id', 'results.documents')
    if set(refs) != set(preds):
        raise ValueError(
            f'Набор документов не совпадает: '
            f'пропущены {sorted(set(refs) - set(preds))}, '
            f'лишние {sorted(set(preds) - set(refs))}'
        )
    field_scores = []
    valid_scores = []
    question_scores = []
    errors = []
    for did, ref in refs.items():
        pred = preds[did]
        keys(pred, ['document_id', 'document_type', 'fields', 'validation', 'answers'], did)
        if pred['document_type'] != ref['document_type']:
            raise ValueError(
                f'{did}: неверный document_type '
                f'(ожидался {ref["document_type"]}, получен {pred["document_type"]})'
            )
        keys(pred['fields'], ref['fields'], f'{did}.fields')
        good = 0
        for key, value in ref['fields'].items():
            actual = pred['fields'][key]
            if type(actual) is not type(value):
                raise ValueError(
                    f'{did}.{key}: неверный тип значения '
                    f'(ожидался {type(value).__name__}, получен {type(actual).__name__})'
                )
            if exact_value(actual, value):
                good += 1
            else:
                errors.append({
                    'document_id': did,
                    'field': key,
                    'expected': value,
                    'actual': actual,
                })
        field_scores.append(good / len(ref['fields']))
        v = pred['validation']
        rv = ref['validation']
        keys(v, ['status', 'missing_fields', 'sources'], f'{did}.validation')
        if v['status'] not in ('document_ok', 'missing_fields'):
            raise ValueError(f'{did}: неверный статус проверки')
        missing = unique_strings(v['missing_fields'], f'{did}.missing_fields')
        if not missing <= set(ref['fields']):
            raise ValueError(f'{did}: неизвестные ключи missing_fields')
        sources = unique_strings(v['sources'], f'{did}.validation.sources')
        if any(not re.fullmatch(r'rule:\d+[.]\d+', s) for s in sources):
            raise ValueError(f'{did}: неверный формат источника правила')
        valid_ok = (
            v['status'] == rv['status']
            and missing == set(rv['missing_fields'])
            and sources == set(rv['sources'])
        )
        valid_scores.append(int(valid_ok))
        if not valid_ok:
            errors.append({
                'document_id': did,
                'validation': {
                    'expected_status': rv['status'],
                    'actual_status': v['status'],
                    'expected_missing': sorted(rv['missing_fields']),
                    'actual_missing': sorted(v['missing_fields']),
                    'expected_sources': sorted(rv['sources']),
                    'actual_sources': sorted(v['sources']),
                },
            })
        pred_answers = by_id(pred['answers'], 'question_id', f'{did}.answers')
        ref_answers = by_id(ref['answers'], 'question_id', f'{did}.reference.answers')
        if set(pred_answers) != set(ref_answers):
            missing_q = sorted(set(ref_answers) - set(pred_answers))
            extra_q = sorted(set(pred_answers) - set(ref_answers))
            raise ValueError(
                f'{did}: набор question_id не совпадает с эталоном '
                f'(не хватает {missing_q}, лишние {extra_q})'
            )
        for qid, ra in ref_answers.items():
            a = pred_answers[qid]
            keys(a, ['question_id', 'answerable', 'value', 'answer', 'sources'], qid)
            if not isinstance(a['answerable'], bool):
                raise ValueError(f'{qid}: answerable должен быть boolean')
            if a['value'] is not None and not isinstance(a['value'], str):
                raise ValueError(f'{qid}: value должен быть string или null')
            if not isinstance(a['answer'], str) or not a['answer'].strip():
                raise ValueError(f'{qid}: нужен непустой ответ')
            ss = unique_strings(a['sources'], f'{qid}.sources')
            if any(
                not re.fullmatch(r'(rule:\d+[.]\d+|field:[a-z_]+)', s)
                for s in ss
            ):
                raise ValueError(f'{qid}: неверный формат источника')
            ok = (
                a['answerable'] == ra['answerable']
                and exact_value(a['value'], ra['value'])
                and ss == set(ra['sources'])
            )
            question_scores.append(int(ok))
            if not ok:
                errors.append({
                    'question_id': qid,
                    'expected': {
                        'answerable': ra['answerable'],
                        'value': ra['value'],
                        'sources': sorted(ra['sources']),
                    },
                    'actual': {
                        'answerable': a['answerable'],
                        'value': a['value'],
                        'sources': sorted(ss),
                    },
                })
    mean = lambda xs: round(sum(xs) / len(xs), 6) if xs else None
    return {
        'format_valid': True,
        'documents': len(refs),
        'questions': len(question_scores),
        'field_accuracy_macro': mean(field_scores),
        'validation_exact_match': mean(valid_scores),
        'question_exact_match': mean(question_scores),
        'errors': errors,
        'note': (
            'Текст answer проверяется на демо; автоматически сравниваются '
            'value, answerable и sources. Итоговый балл жюри не рассчитывается.'
        ),
    }
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--report', help='Optional JSON report file')
    args = parser.parse_args()
    try:
        report = evaluate(load(args.reference), load(args.predictions))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'format_valid': False, 'error': str(exc)},
                         ensure_ascii=False, indent=2))
        return 2
    if args.report:
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0
if __name__ == '__main__':
    sys.exit(main())