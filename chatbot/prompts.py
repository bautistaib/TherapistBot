import os
from django.conf import settings


prompt_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'prompts')
# Import the system prompts
with open(os.path.join(prompt_dir, 'new_user_prompt.txt'), 'r') as file:
    # new_user_prompt has a {username} and a {required_fields} placeholder.
    new_user_prompt = file.read()
with open(os.path.join(prompt_dir, 'required_fields.txt'), 'r') as file:
    # the data required for the patient.
    required_fields = file.read()
with open(os.path.join(prompt_dir, 'check_fields.txt'), 'r') as file:
    # A system prompt for the checker LLM to check if all the required fields are present on the converstion.
    # It has a {conversation} and {required_fields} placeholder.
    check_fields = file.read()
with open(os.path.join(prompt_dir, 'profile_json.txt'), 'r') as file:
    # A system prompt for the checker to output a JSON with the patient data.
    # It has a {conversation} placeholder.
    profile_json_prompt = file.read()
with open(os.path.join(prompt_dir, 'new_session.txt'), 'r') as file:
    # A system prompt for the checker to arrange a session with the patient.
    # It has a {conversation} placeholder.
    new_session_prompt = file.read()