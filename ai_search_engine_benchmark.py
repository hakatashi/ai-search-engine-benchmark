from revChatGPT.V1 import Chatbot
from dotenv import dotenv_values
from typing import TypeVar, Optional
from yaml import load, load_all, Loader, dump_all, Dumper, add_representer
from pathlib import Path

EXPECTED_MAX_RESULTS = 1

T = TypeVar('T')

def not_none(obj: Optional[T]) -> T:
	assert obj is not None
	return obj

env = dotenv_values(".env")

def str_presenter(dumper, data):
	if data.count('\n') > 0:
		return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
	return dumper.represent_scalar('tag:yaml.org,2002:str', data)

add_representer(str, str_presenter)

with open('questions.yml', encoding='utf-8') as file:
	questions = load(file, Loader=Loader)

chatbot = Chatbot(config={
	'model': 'text-davinci-002-render-sha',
	"access_token": not_none(env["CHATGPT_ACCESS_TOKEN"]),
})

def ask_chatgpt(prompt: str) -> str:
	response = ""
	for data in chatbot.ask(prompt):
		response = data["message"]
	return response

chat_engines = [
	('chatgpt', ask_chatgpt),
]

for question in questions:
	for engine_name, ask in chat_engines:
		# Ensure results directory
		engine_path = Path('results') / engine_name
		engine_path.mkdir(parents=True, exist_ok=True)
		
		result_file = engine_path / f'{question["A"]}.yml'
		if result_file.exists():
			with open(result_file, encoding='utf-8') as file:
				results = list(load_all(file, Loader=Loader))
		else:
			results = []

		if len(results) >= EXPECTED_MAX_RESULTS:
			print(f'Skipping {question["A"]} for {engine_name} as it has {len(results)} results')
			continue

		print(f'Asking {engine_name} for {question["A"]}')

		results.append({
			'question': question["Q"],
			'answer': question["A"],
			'result': ask(question["Q"]),
			'moderation': 'NONE',
		})

		with open(result_file, 'w', encoding='utf-8') as file:
			dump_all(results, file, Dumper=Dumper, allow_unicode=True)
