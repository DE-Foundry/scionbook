"""Failed pricing batches need consent before a bounded singleton recovery."""
import builtins
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import requests

import scionbook_report as report


class BatchSession:
    def __init__(self, batch_response=None, fail_single=False):
        self.calls = []
        self.batch_response = batch_response
        self.fail_single = fail_single

    def get(self, url, **kwargs):
        ids = list(map(int, urlsplit(url).path.rsplit('/', 1)[-1].split(',')))
        self.calls.append(ids)
        if len(ids) > 1:
            if self.batch_response is None:
                raise requests.Timeout('synthetic gateway timeout')
            return self.batch_response
        if self.fail_single:
            raise requests.Timeout('synthetic item timeout')
        payload = {'itemID': ids[0], 'recentHistory': [{'pricePerUnit': 100}]}
        return response(payload)


def response(payload, status=200):
    return SimpleNamespace(status_code=status, json=lambda: payload,
                           raise_for_status=lambda: None)


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    monkeypatch.setattr(report.time, 'sleep', lambda _: None)


@pytest.mark.parametrize('answer, expected', [('yes', [1, 2]), ('y', [1, 2]),
                                              ('no', []), ('', [])])
def test_interactive_retry_requires_yes(monkeypatch, capsys, answer, expected):
    monkeypatch.setattr(report.sys.stdin, 'isatty', lambda: True)
    prompts = []
    def reply():
        prompts.append(True)
        return answer
    monkeypatch.setattr(builtins, 'input', reply)
    session = BatchSession()
    out = report.fetch_prices([1, 2], 'Example World', session, attempts=1)
    assert sorted(out) == expected
    assert len(prompts) == 1
    assert session.calls == ([[1, 2], [1], [2]] if expected else [[1, 2]])
    assert 'Example World' in capsys.readouterr().err


def test_noninteractive_run_records_question_without_retry(monkeypatch):
    monkeypatch.setattr(report.sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(builtins, 'input', lambda: pytest.fail('must not read stdin'))
    session, notes = BatchSession(), []
    assert report.fetch_prices([1, 2], 'Example DC', session, attempts=1, notes=notes) == {}
    assert session.calls == [[1, 2]]
    assert any('Ask the user' in n and '--retry-pricing-single-items' in n for n in notes)


def test_prior_approval_retries_only_missing_ids(monkeypatch):
    monkeypatch.setattr(builtins, 'input', lambda: pytest.fail('approval already supplied'))
    session = BatchSession(response({'items': {'1': {'itemID': 1}, '2': None}}))
    out = report.fetch_prices([1, 2], 'Example DC', session, attempts=1,
                              retry_single_items=True)
    assert sorted(out) == [1, 2]
    assert session.calls == [[1, 2], [2]]


def test_approved_retry_is_bounded_even_when_singletons_fail():
    session, notes = BatchSession(fail_single=True), []
    out = report.fetch_prices([1, 2], 'Example DC', session, attempts=2,
                              retry_single_items=True, notes=notes)
    assert out == {}
    assert session.calls == [[1, 2], [1, 2], [1], [1], [2], [2]]
    assert any('remain unpriced' in n for n in notes)


def test_batch_404_can_be_recovered_after_approval():
    session = BatchSession(response({}, status=404))
    out = report.fetch_prices([1, 2], 'Example DC', session, attempts=1,
                              retry_single_items=True)
    assert sorted(out) == [1, 2]


@pytest.mark.parametrize('payload', [[], None, {'items': {}}, {'items': {'1': {}}}])
def test_malformed_or_empty_response_remains_recoverable(payload):
    session = BatchSession(response(payload))
    out = report.fetch_prices([1, 2], 'Example DC', session, attempts=1,
                              retry_single_items=True)
    assert sorted(out) == [1, 2]


def test_single_item_batch_size_does_not_offer_smaller_retry(monkeypatch):
    monkeypatch.setattr(builtins, 'input', lambda: pytest.fail('cannot reduce below 1'))
    session = BatchSession(fail_single=True)
    assert report.fetch_prices([1, 2], 'Example DC', session, chunk=1,
                               attempts=1, retry_single_items=True) == {}
    assert session.calls == [[1], [2]]


def test_single_item_404_is_not_retried(monkeypatch):
    monkeypatch.setattr(builtins, 'input', lambda: pytest.fail('404 is not retryable'))
    session = SimpleNamespace(get=lambda *a, **k: response({}, status=404))
    assert report.fetch_prices([1], 'Example DC', session, attempts=1) == {}
