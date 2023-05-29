from yaml import load, load_all, Loader
from pathlib import Path
import sys

with open('questions.yml', encoding='utf-8') as file:
	questions = load(file, Loader=Loader)

chat_engines = [
	('chatgpt_gpt35', 'ChatGPT (GPT-3.5)'),
	('chatgpt_gpt4_browsing', 'ChatGPT (GPT-4 with Browsing)'),
	('edge_creative', 'Bing AI (Creative)'),
	('edge_precise', 'Bing AI (Precise)'),
	('bard', 'Bard'),
]

def aggregate_results():
	results_dir = Path(__file__) / '..' / 'results'
	results = []
	scores = {}

	for chat_engine_id, chat_engine_name in chat_engines:
		scores[chat_engine_id] = 0

	for question in questions:
		question_results = {}

		for chat_engine_id, chat_engine_name in chat_engines:
			yml_file = results_dir / chat_engine_id / f'{question["A"]}.yml'

			if not yml_file.exists():
				print(f'No result file for {chat_engine_name} for {question["A"]}')
				sys.exit(1)

			with open(yml_file, encoding='utf-8') as file:
				engine_results = list(load_all(file, Loader=Loader))

			if len(engine_results) == 0:
				print(f'No results for {chat_engine_name} for {question["A"]}')
				sys.exit(1)

			for engine_result in engine_results:
				if engine_result['moderation'] not in ['CORRECT', 'PARTIALLY_WRONG', 'WRONG', 'INVALID', 'NO_ANSWER']:
					print(f'Invalid moderation value {engine_result["moderation"]} for {chat_engine_name} for {question["A"]}')
					sys.exit(1)

				if engine_result['moderation'] == 'CORRECT':
					scores[chat_engine_id] += 4

				if engine_result['moderation'] == 'PARTIALLY_WRONG':
					scores[chat_engine_id] += 3

				if engine_result['moderation'] == 'WRONG':
					scores[chat_engine_id] += 0

				if engine_result['moderation'] == 'INVALID':
					scores[chat_engine_id] += 1

				if engine_result['moderation'] == 'NO_ANSWER':
					scores[chat_engine_id] += 2
				
				question_results[chat_engine_id] = engine_result['moderation']
			
		results.append({
			'question': question['Q'],
			'answer': question['A'],
			'results': question_results,
		})
	
	for chat_engine_id, chat_engine_name in chat_engines:
		print(f'* {chat_engine_name}: {scores[chat_engine_id]}')

	print()

	result_marks = {
		'CORRECT': '✅',
		'PARTIALLY_WRONG': '⚠️',
		'WRONG': '❌',
		'INVALID': '🚫',
		'NO_ANSWER': '➖',
	}

	engine_names = ' | '.join([chat_engine_name for chat_engine_id, chat_engine_name in chat_engines])
	print(f'| | {engine_names} |')
	print('|:-:|:-:|:-:|:-:|:-:|:-:|')

	for i, result in enumerate(results):
		engine_results = ' | '.join([result_marks[result['results'][chat_engine_id]] for chat_engine_id, chat_engine_name in chat_engines])
		print(f'| Q{i + 1} | {engine_results} |')

if __name__ == '__main__':
	aggregate_results()
