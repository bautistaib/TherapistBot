from django.shortcuts import render, redirect
from django.contrib import auth
from django.contrib.auth.models import User
from .models import Patient, Session, Chat
from .prompts import new_user_prompt, new_session_prompt, profile_json_prompt, check_fields, required_fields
from django.conf import settings
import os
import json
from datetime import datetime, timedelta


from openai import OpenAI
api_key = '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'
client = OpenAI(api_key = api_key)
model = 'gpt-3.5-turbo'


def trim_message(message):
    # Remove the visible and timestamp keys from the message inside the conversation on models.Chat.
    return {"role": message["role"], "content": message["content"]}    

def respond(conversation, client, system_prompt, model=model, tools=None, max_tokens=200, tool_choice='auto', temperature=1.0):
    """
    Generates a response to a conversation using the OpenAI Chat API.

    Parameters:
    - conversation (list): A list of messages in the conversation.They must include a 'role' and 'content' key.
    - client: The OpenAI Chat API client.
    - system_prompt (str): The system prompt for the conversation.
    - model (str): The model to use for generating the response. Default is the value of the 'model' variable.
    - tools (list): A list of tools to use for generating the response. Default is None.
    - max_tokens (int): The maximum number of tokens in the generated response. Default is 200.
    - tool_choice (str): The tool choice for generating the response. Default is 'auto'.
    - temperature (float): The temperature for generating the response. Default is 1.0.

    Returns:
    - content (str): The content of the generated response.
    - finish_reason (str): The reason for finishing the response generation.
    - tool_calls (list): A list of tool calls made during the response generation.
    """
    messages = [{"role": "system", "content": system_prompt}] + [trim_message(message) for message in conversation]
    if tools not in [None, []]:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            temperature=temperature,
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    print('message:', response.choices[0].message.content, '\nfinish reason:', response.choices[0].finish_reason, '\ntool_calls:', response.choices[0].message.tool_calls)
    return response.choices[0].message.content, response.choices[0].finish_reason, response.choices[0].message.tool_calls

# <|FINISHED|>

def extract_patient_information(patient):
    """
    Extracts the patient information from a patient object and returns it as a json string.
    """
    information = "{\n"
    fields = ['alias', 'age', 'gender', 'email', 'phone_number', 'previous_diagnosis', 'first_time']
    for field in fields:
        if getattr(patient, field):
            information += f"{field}: {getattr(patient, field)}\n"
    information += "}"
    return information

def datetime_to_string(datetime):
    # Returns a string with the weekday and the datetime object for the chatbot to know the current datetime.
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return f"{weekdays[datetime.weekday()]} " + str(datetime)

def conversation_to_string(conversation):
    conversation_string = ""
    for message in conversation:
        conversation_string += f"{message['role']}: {message['content']}\n"
    return conversation_string

# check_date and set_session functions are to be used by the chatbot to set up a new session.
def check_date(year, month, day, hour):
    """
    Check if a session can be scheduled at a given date and time. Returns a string for the chatbot to read.
    """
    # Construct a datetime object from the arguments
    scheduled_time = datetime(year, month, day, hour)

    # Check for sessions within the hour range
    sessions = Session.objects.filter(date__gte=scheduled_time, date__lt=scheduled_time + timedelta(minutes=59))
    if sessions.exists():
        return 'There is already a session scheduled within the hour range you specified.'
    elif scheduled_time < datetime.now():
        return 'You cannot schedule a session in the past.'
    elif scheduled_time.weekday() == 5 or scheduled_time.weekday() == 6:
        return 'You cannot schedule a session on the weekend.'
    elif (hour < 8 and hour > 18) or (hour >= 12 and hour < 14):
        return 'You cannot schedule a session outside of business hours.'
    else:
        return 'No session scheduled, datetime is available.'

def set_session(year, month, day, hour, patient):
    # Construct a datetime object from the arguments
    session_date = datetime(year, month, day, hour)
    check = check_date(year, month, day, hour)
    if check != 'No session scheduled, datetime is available.':
        return check, None
    else:
        session = Session.objects.create(patient=patient, date=session_date)
        session.save()
        return 'Session scheduled.', session


check_date_schema = {"type": "function", 
                    "function": {"name": "check_date", 
                                "description": "Check if a session can be scheduled at a given date and time", 
                                "parameters": {"type": "object", 
                                                "properties": {"year": {"type": "integer", "description": "The year of the session"}, 
                                                            "month": {"type": "integer", "description": "The month of the session"}, 
                                                            "day": {"type": "integer", "description": "The day of the session"}, 
                                                            "hour": {"type": "integer", "description": "The hour of the session"}}, 
                                                "required": ["year", "month", "day", "hour"]
                                            }
                                    }
                    }

# We remove the patient parameter from the set_session_schema, we'll handle it manually.
set_session_schema = {"type": "function",
                        "function": {"name": "set_session",
                                    "description": "Schedule a session at a given date and time",
                                    "parameters": {"type": "object", 
                                                "properties": {"year": {"type": "integer", "description": "The year of the session"}, 
                                                            "month": {"type": "integer", "description": "The month of the session"}, 
                                                            "day": {"type": "integer", "description": "The day of the session"}, 
                                                            "hour": {"type": "integer", "description": "The hour of the session"}}, 
                                                "required": ["year", "month", "day", "hour"]
                                            }
                                    }
                    }


# Sample backend logic to retrieve available and booked time slots
from datetime import datetime, timedelta

def get_available_time_slots(request):
    """
    Part of a TODO, this function would be used to display a calendar with the available time slots for the therapist.
    """
    # Logic to get the current week's time slots
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=7)

    # Logic to retrieve booked sessions for the therapist within this week
    booked_sessions = Session.objects.filter(date__range=[start_date, end_date])

    # Generate available time slots for the entire week (from 8 AM to 6 PM)
    available_time_slots = []
    for day in range(7):  # 0 for Monday, 1 for Tuesday, ..., 6 for Sunday
        for hour in range(8, 18):  # From 8 AM to 6 PM
            current_date = start_date + timedelta(days=day)
            slot_start = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour)
            slot_end = slot_start + timedelta(hours=1)
            # Check if the current hour slot is available
            is_available = not booked_sessions.filter(date__range=[slot_start, slot_end]).exists()
            available_time_slots.append({'day': day, 'hour': hour, 'available': is_available})

    return available_time_slots

working_range = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password= request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = "Invalid credentials"
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password']
        password2= request.POST['confirm_password']
        if password1 == password2:
            if User.objects.filter(username=username).exists():
                error_message = "Username already exists"
                return render(request, 'signup.html', {'error_message': error_message})
            else:
                user = User.objects.create_user(username=username, password=password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot')
        else:
            error_message = "Passwords do not match"
            return render(request, 'signup.html', {'error_message': error_message})
            
    return render(request, 'signup.html')

def chatbot(request):
    """
    This view handles all the chatbot logic. It has two working modes:
    - New user mode: The chatbot will ask for the required fields to create a patient profile.
        in this mode, the chatbot will ask for the required fields, once it decides it has them, it will ask the checker LLM to check if all the required fields are present.
        If they are, we use gpt-4-turbo in JSON mode to output a JSON with the patient data and create a new patient object.
    - Existing patient mode: The chatbot will ask if the user wants to schedule a session.
        in this mode, the chatbot has the ability to check if a given date and time are available, and to schedule a session.
        This is done through the tool calls on the OpenAI API.
    Once either of these modes is finished, we show a success message and new chat button to the user. 
    """
    # Check if user is logged in
    if request.user.is_anonymous:
        print("user is anonymous, redirecting")
        return redirect('login')
    # Check if the user has an open chat
    if Chat.objects.filter(user=request.user, is_open=True).exists():
        print("chat exists, opening existing chat")
        chat = Chat.objects.get(user=request.user, is_open=True)
    else:
        print("chat does not exist, creating new chat")
        chat = Chat.objects.create(user=request.user)
        # We add a hardcoded message to the chatbot to save tokens.
        # If the user has a profile, we'll ask if there's anything they need.
        # If they don't, we'll ask for their alias.
        if Patient.objects.filter(user=request.user).exists():
            print("Patient exists:", Patient.objects.get(user=request.user), "adding corresponding welcome message")
            patient = Patient.objects.get(user=request.user)
            chat.add_message("assistant", f"Hello {patient.alias}, welcome to the office of Dr. John Doe. Would you want to schedule a session?")
        else:
            print("Patient does not exist, adding corresponding welcome message")
            chat.add_message("assistant", f"Hello {request.user.username}, welcome to the office of Dr. John Doe. Is there any way you'd like to be called, both by me and Dr. Doe?")
    if request.method == 'POST':
        if 'reset_chat' in request.POST:
            chat.delete()
            print("chat deleted, redirecting")
            return redirect('chatbot')
        if 'new_chat' in request.POST:
            chat.is_open = False
            print("new chat, redirecting")
            return redirect('chatbot')
        if 'send_message' in request.POST:
            print("user sent a message")
            user_input = request.POST['user_input']
            print("user message added: ", user_input)
            chat.add_message("user", user_input)
            # Check if the user has a patient profile. If they do, we'll use the prompts for setting up a new session.
            # If they don't, we'll use the prompts for setting up a new patient profile.
            if Patient.objects.filter(user=request.user).exists():
                print("Patient exists:", Patient.objects.get(user=request.user))
                patient = Patient.objects.get(user=request.user)
                response, finish_reason, tool_calls = respond(chat.conversation, client, model = 'gpt-4-1106-preview',
                        system_prompt = new_session_prompt.format(patient_information = extract_patient_information(patient), current_datetime = datetime_to_string(datetime.now())),
                        tools = [check_date_schema, set_session_schema], max_tokens = 500, temperature = 0.5)
                if response is not None:
                    chat.add_message("assistant", response)
                if finish_reason == 'tool_calls':
                    print("tool calls")
                    tool_calls = tool_calls[0]
                    print(tool_calls)
                    chat.add_message("assistant",'Function called: ' + tool_calls.function.name, visible=False)
                    if tool_calls.function.name == 'check_date':
                        print("checking date")
                        try:
                            check = check_date(**json.loads(tool_calls.function.arguments))
                            print(check)
                            chat.add_message("assistant",'Output: ' + check, visible=False)
                        except Exception as e:
                            print(e)
                            chat.add_message("assistant",'Error: ' + str(e), visible=False)
                        response, _, _ = respond(chat.conversation, client, model = 'gpt-4-1106-preview',
                            system_prompt = new_session_prompt.format(patient_information = extract_patient_information(patient), current_datetime = datetime_to_string(datetime.now())),
                            tools = [check_date_schema, set_session_schema], max_tokens = 500, tool_choice = 'none')
                        chat.add_message("assistant", response)
                    elif tool_calls.function.name == 'set_session':
                        print("setting session")
                        try:
                            session_message, session = set_session(**json.loads(tool_calls.function.arguments), patient=patient)
                            print(session_message)
                            chat.add_message("assistant",'Output: ' + session_message, visible=False)
                            response, _, _ = respond(chat.conversation, client, model = 'gpt-4-1106-preview',
                                system_prompt = new_session_prompt.format(patient_information = extract_patient_information(patient), current_datetime = datetime_to_string(datetime.now())),
                                tools = [check_date_schema, set_session_schema], max_tokens = 500, tool_choice = 'none')
                            chat.add_message("assistant", response)
                            chat.session = session
                            chat.is_open = False
                            chat.save()
                        except Exception as e:
                            print(e)
                            chat.add_message("assistant",'Error: ' + str(e), visible=False)
                            response, _, _ = respond(chat.conversation, client, model = 'gpt-4-1106-preview',
                            system_prompt = new_session_prompt.format(patient_information = extract_patient_information(patient), current_datetime = datetime_to_string(datetime.now())),
                            tools = [check_date_schema, set_session_schema], max_tokens = 500, tool_choice = 'none')
                            chat.add_message("assistant", response)
                            return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})
                        
                        return render(request, 'chatbot.html', {'username': request.user, 'chat': chat, 'finished_chat': True, 'close_message': 'Session scheduled successfully! If you want to schedule another session, click on the "New chat" button.'})

                #patient = Patient.objects.get(user=request.user)
                return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})
            else:
                print("Patient does not exist")
                # The chatbot responds in new user mode, it's instructed to ask for the required fields.
                # Once it has them, it will finish the response with a "<|FINISHED|>" token.
                # If this happens, we'll check with another LLM if all the required fields are present.
                # If they are, we'll ask the LLM to output a JSON with the patient data and we'll create a new patient object.
                # If they aren't, we'll ask the LLM to output the missing fields and return them to the chatbot.
                response, _, _ = respond(chat.conversation, client,
                                    new_user_prompt.format(username=request.user.username, required_fields=required_fields))

                if '<|FINISHED|>' in response:
                    print("finished")
                    response = response.replace("<|FINISHED|>", "")
                    
                    # Check if the required fields are present
                    conversation_string = conversation_to_string(chat.conversation)
                    check = client.chat.completions.create(
                        model = model,
                        messages = [{"role": "system", "content": check_fields.format(conversation=conversation_string, required_fields=required_fields)}],
                        stop = '\n',
                    )
                    if 'yes' in check.choices[0].message.content.lower():
                        print("all required fields are present")
                        profile_response = client.chat.completions.create(
                            model = 'gpt-4-1106-preview',
                            messages = [{"role": "system", "content": profile_json_prompt.format(conversation=conversation_string, required_fields=required_fields)}],
                            max_tokens = 500,
                            response_format={ "type": "json_object" },
                        )
                        profile_json = json.loads(profile_response.choices[0].message.content.lower())
                        print('patient profile: ', profile_json)
                        # We try to create a patient object with the data from the profile_json
                        try:
                            patient = Patient.objects.create(user=request.user, **profile_json)
                            patient.save()
                            print("patient created")
                        except Exception as e:
                            # If there's an error, we'll show it to the chatbot as an invisible message and instruct it to tell the user about it.
                            print(e)
                            chat.add_message(role = "assistant", content = "Error: " + str(e) +'/n/nThought:I should tell the user about this error', visible=False)
                            response, _, _ = respond(conversation = chat.conversation, client = client, model = model,
                                    system_prompt = new_user_prompt.format(username=request.user.username, required_fields=required_fields))
                            chat.add_message("assistant", response)
                            return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})
                        chat.is_open = False
                        chat.save()
                        print("chat closed")
                        return render(request, 'chatbot.html', {'username': request.user, 'chat': chat, 'close_message': 'Patient registered successfully! If you want to schedule a session, click on the "New chat" button.'})
                    else:
                        print("not all required fields are present")
                        message = "Error: There are missing fields in the patient profile. Please continue the conversation until you have them."
                        chat.add_message("assistant", message, visible=False)
                        response, _, _ = respond(chat.conversation, client,
                                    new_user_prompt.format(username=request.user.username, required_fields=required_fields))
                        chat.add_message("assistant", response)
                        return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})
                else:
                    print("not finished")
                    chat.add_message("assistant", response)
                    return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})
            

    return render(request, 'chatbot.html', {'username': request.user, 'chat': chat})

def logout(request):
    auth.logout(request)
    return redirect('login')