from revChatGPT.V1 import Chatbot as ChatGPTV1
from EdgeGPT import Chatbot as EdgeGPT
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

chatgpt_client = ChatGPTV1(config={
	'model': 'text-davinci-002-render-sha',
	"access_token": not_none(env["CHATGPT_ACCESS_TOKEN"]),
})

async def ask_chatgpt(prompt: str) -> str:
	response = ""
	for data in chatgpt_client.ask(prompt):
		response = data["message"]
	return response

async def main():
	edgegpt_client = await EdgeGPT.create(cookies=cookies)

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
		# ('chatgpt', ask_chatgpt),
		('edge_creative', partial(ask_edgegpt, ConversationStyle.creative)),
		('edge_precise', partial(ask_edgegpt, ConversationStyle.precise)),
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
			try:
				result = await ask(question["Q"])
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

			with open(result_file, 'w', encoding='utf-8') as file:
				dump_all(results, file, Dumper=Dumper, allow_unicode=True)

if __name__ == '__main__':
	asyncio.run(main())