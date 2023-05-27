from revChatGPT.V1 import Chatbot as ChatGPTV1
from EdgeGPT import Chatbot as EdgeGPT, Query
from Bard import Chatbot as Bard
from EdgeGPT import ConversationStyle
from dotenv import dotenv_values
from typing import TypeVar, Optional
from yaml import load, load_all, Loader, dump_all, Dumper, add_representer
from pathlib import Path
from functools import partial
import asyncio
import json

EXPECTED_MAX_RESULTS = 1

T = TypeVar('T')

def not_none(obj: Optional[T]) -> T:
	assert obj is not None
	return obj

env = dotenv_values(".env")
with open("bing_cookies.json", encoding="utf-8") as file:
	cookies = json.load(file)

def str_presenter(dumper, data):
	if data.count('\n') > 0:
		return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
	return dumper.represent_scalar('tag:yaml.org,2002:str', data)

add_representer(str, str_presenter)

with open('questions.yml', encoding='utf-8') as file:
	questions = load(file, Loader=Loader)

bard_client = Bard(not_none(env["BARD_TOKEN"]))

async def ask_chatgpt(model: str, prompt: str) -> str:
	chatgpt_client = ChatGPTV1(config={
		'model': model,
		'access_token': not_none(env["CHATGPT_ACCESS_TOKEN"]),
	})

	response = ""
	for data in chatgpt_client.ask(prompt):
		response = data["message"]
	return response

async def ask_bard(prompt: str) -> str:
	result = bard_client.ask(prompt)
	return result['content'].replace('\r\n', '\n')

async def main():
	edgegpt_client = await EdgeGPT.create()

	async def ask_edgegpt(conversation_style: ConversationStyle, prompt: str) -> str:
		await edgegpt_client.reset()

		result = await edgegpt_client.ask(prompt=prompt, conversation_style=conversation_style)

		bot_messages = [message for message in result['item']['messages'] if message['author'] == 'bot']

		message_texts = []
		for message in bot_messages:
			message_text = ''
			if type(message.get('adaptiveCards')) == list:
				for card in message.get('adaptiveCards'):
					for block in card.get('body'):
						if block.get('size') != 'small':
							message_text += block.get('text') + '\n'
			if len(message_text) == 0:
				message_text = message['text']
			message_texts.append(message_text)

		response = '\n'.join(message_texts)

		return response

	chat_engines = [
		('chatgpt_gpt35', partial(ask_chatgpt, 'text-davinci-002-render-sha'), ''),
		('chatgpt_gpt4_browsing', partial(ask_chatgpt, 'gpt-4-browsing'), ' 検索して答えてください。'),
		('edge_creative', partial(ask_edgegpt, ConversationStyle.creative), ' 検索して答えてください。'),
		('edge_precise', partial(ask_edgegpt, ConversationStyle.precise), ' 検索して答えてください。'),
		('bard', ask_bard, ''),
	]

	for question in questions:
		for engine_name, ask, suffix in chat_engines:
			# Ensure results directory
			engine_path = Path('results') / engine_name
			engine_path.mkdir(parents=True, exist_ok=True)
			
			result_file = engine_path / f'{question["A"]}.yml'
			if result_file.exists():
				with open(result_file, encoding='utf-8') as file:
					results = list(load_all(file, Loader=Loader))
			else:
				results = []

			results = list(filter(lambda result: len(result['result']) > 0, results))

			if len(results) >= EXPECTED_MAX_RESULTS:
				print(f'Skipping {question["A"]} for {engine_name} as it has {len(results)} results')
				continue

			print('Waiting 5 seconds...')
			await asyncio.sleep(5)

			print(f'Asking {engine_name} for {question["A"]}')

			try:
				result = await ask(question["Q"] + suffix)
				print(f'Got result from {engine_name} for {question["A"]}:')
				print(result)

				results.append({
					'question': question["Q"],
					'answer': question["A"],
					'result': result,
					'moderation': 'NONE',
					'moderation_note': '',
				})

			except Exception as e:
				print(f'Failed to ask {engine_name} for {question["A"]}')
				print(e)

				results.append({
					'question': question["Q"],
					'answer': question["A"],
					'result': '',
					'moderation': 'NONE',
					'moderation_note': '',
				})

			with open(result_file, 'w', encoding='utf-8') as file:
				dump_all(results, file, Dumper=Dumper, allow_unicode=True)

if __name__ == '__main__':
	asyncio.run(main())