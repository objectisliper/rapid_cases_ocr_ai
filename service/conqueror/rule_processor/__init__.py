"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Request chain processing

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
"""
"rules": [
    {
		"id": <идентификатор правила>,
	     "steps":[
		{
			"order": <порядковый номер условия>,
			"URLcondition": <тип условия>,
			"exact": <использовать ли нестрогую проверку>,
			"URLtext": <текст, который мы проверяем в адресе>,
			"ConditionsLogic": <логический оператор>,
			"PageContentsCondition": <тип условия>,
			"PageText": <текст, который мы проверяем на самой странице>,
		},
		{
			"order": <...>,
			"URLcondition": <...>,
			"URLtext": <...>,
	           ...
		}
		]
]
"""
import json


class QueryParser(object):
    """
    Default query parser
    """

    def __init__(self, raw_text):
        self.raw = json.loads(raw_text)
        self.request_id = None
        self.is_async = False

    def parse_step(self, step_json):
        # parses one step to the rule data
        # TODO awful mapper
        return {
            'order': int(step_json.get('order', '0')),
            'url_contains': (
                    step_json.get('URLcondition', 'contains') == 'contains'
            ),
            'url_text': step_json.get('URLtext', ''),
            'is_exact': step_json.get('exact', False),
            'page_contains': (
                    step_json.get('PageContentsCondition', 'contains') == 'contains'
            ),
            'page_text': step_json.get('PageText', ''),
            'use_or': (step_json.get('ConditionsLogic', 'or') == 'or')
        }

    def parse(self):
        # parses full query JSON
        self.request_id = self.raw.get('id', None)
        self.is_async = self.raw.get('async', False)

        rules = self.raw.get('rules', None)
        if not rules:
            raise Exception('Rules for the query are not defined')

        ret = {}
        for rule in rules:
            r = {
                'id': rule.get('id', None),
                'steps': []
            }
            for step in rule.get('steps', []):
                r['steps'].append(self.parse_step(step))
            ret[r['id']] = r

        return ret

    def get_request_id(self):
        return self.request_id if self.request_id else ''

    def get_async_flag(self):
        return self.is_async


class RuleProcessor(object):
    """
    Class that is used to process text based on rule matching
    """

    def __init__(self, rule_set):
        self.rules = rule_set
        print(rule_set)

    def match_rule(self, rule, raw_text):
        # match raw_text to the target rule
        matches = True
        for step in rule['steps']:
            text_matches = True
            if step['page_contains']:
                if step['page_text'] not in raw_text:
                    text_matches = False
            else:
                if step['page_text'] in raw_text:
                    text_matches = False

            # TODO: update this for URL parsing
            url_matches = True
            if step['url_contains']:
                if step['url_text'] not in raw_text:
                    url_matches = False
            else:
                if step['url_text'] in raw_text:
                    url_matches = False

            if step['use_or']:
                if not text_matches and not url_matches:
                    matches = False
                    break
            else:
                if not text_matches or not url_matches:
                    matches = False
                    break

        return matches

    def has_match(self, raw_text):
        # checking the text against the rules
        ret, has_any_matches = {}, False
        for k, v in self.rules.items():
            ret[k] = self.match_rule(v, raw_text)
            has_any_matches = has_any_matches or ret[k]

        return ret, has_any_matches


if __name__ == '__main__':
    raw_text = """
    {
        "rules": [{
    	"id": 151212,
        "steps": [
    	    {
    		"order": 0,
    		"URLcondition": "contains",
    		"exact": 0,
    		"URLtext": "someth",
    		"ConditionsLogic": "and",
    		"PageContentsCondition": "!contains",
    		"PageText": "fa"
    	    }
          ]
    }]
    }
    """

    qp = QueryParser(raw_text)
    print(qp.parse())
    print('FA')
