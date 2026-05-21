from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
import requests
from gtts import gTTS
import json
from .models import Conversation, QuickResponse

def home(request):
    if request.user.is_authenticated:
        return redirect('conversation')
    return redirect('auth')

def auth_page(request):
    if request.user.is_authenticated:
        return redirect('conversation')

    if request.method == "POST":
        action = request.POST.get("action")

        # --- SIGN UP ---
        if action == "signup":
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
            confirm = request.POST.get("confirm")

            if password != confirm:
                messages.error(request, "Passwords do not match")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                login(request, user)
                return redirect("conversation")

        # --- SIGN IN ---
        elif action == "signin":
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("conversation")
            else:
                messages.error(request, "Invalid username or password")

    return render(request, "varta/auth.html")

@login_required(login_url='auth')
def conversation_view(request):
    # Handle POST requests for new messages
    if request.method == 'POST':
        message = request.POST.get('message')
        translated_message = request.POST.get('translated_message', '')
        source_language = request.POST.get('source_language', 'en')
        target_language = request.POST.get('target_language', 'hi')
        
        if message:
            Conversation.objects.create(
                user=request.user, 
                message=message,
                translated_message=translated_message,
                source_language=source_language,
                target_language=target_language,
                message_type='text'
            )
        return redirect('conversation')

    # Get user data and conversation history
    quick_responses = QuickResponse.objects.filter(user=request.user)
    recent_messages = Conversation.objects.filter(user=request.user).order_by('-timestamp')[:50]  # Increased to 50 messages

    # Prepare user data for the template
    user_data = {
        "id": request.user.id,
        "name": request.user.get_full_name() or request.user.username,
        "email": request.user.email,
        "username": request.user.username,
        "language": getattr(request, 'LANGUAGE_CODE', 'en'),
        "accessibility_settings": {
            "auto_speak": True,
            "speech_rate": 1.0
        }
    }

    # Convert messages to JSON for the frontend
    messages_data = []
    for msg in recent_messages:
        messages_data.append({
            "id": msg.id,
            "speaker": "You",
            "message": msg.message,
            "translated_message": msg.translated_message,
            "source_language": msg.source_language,
            "target_language": msg.target_language,
            "type": msg.message_type,
            "timestamp": msg.timestamp.isoformat()
        })

    return render(request, 'varta/conversation.html', {
        'quick_responses': quick_responses,
        'recent_messages': recent_messages,
        'user_data': json.dumps(user_data),
        'messages_data': json.dumps(messages_data)
    })

@login_required(login_url='auth')
def history_view(request):
    conversations = Conversation.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'varta/history.html', {'conversations': conversations})

@login_required(login_url='auth')
def quick_responses_view(request):
    if request.method == 'POST':
        phrase = request.POST.get('phrase')
        language = request.POST.get('language', 'en')
        category = request.POST.get('category', 'General')
        if phrase:
            QuickResponse.objects.create(
                user=request.user, 
                phrase=phrase, 
                language=language,
                category=category
            )
        return redirect('quick_responses')

    quick_responses = QuickResponse.objects.filter(user=request.user)
    return render(request, 'varta/quick_responses.html', {'quick_responses': quick_responses})

@login_required(login_url='auth')
def delete_quick_response(request, response_id):
    if request.method == 'POST':
        try:
            response = QuickResponse.objects.get(id=response_id, user=request.user)
            response.delete()
            messages.success(request, "Quick response deleted successfully")
        except QuickResponse.DoesNotExist:
            messages.error(request, "Quick response not found")
    return redirect('quick_responses')

def logout_view(request):
    logout(request)
    return redirect('auth')

# Translation and TTS functions
def detect_language(text):
    """Detect source language using MyMemory API"""
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=|en"
        res = requests.get(url)
        return res.json().get("responseData", {}).get("detectedSourceLanguage", "en")
    except:
        return "en"

@csrf_exempt
@login_required(login_url='auth')
def translate_text(request):
    """Translate text between two languages and save to database"""
    text = request.GET.get("text", "")
    target = request.GET.get("target", "en")
    
    if not text:
        return JsonResponse({"error": "No text provided"}, status=400)

    # Detect source language
    source = detect_language(text)
    
    # Get translation from MyMemory API
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
    
    try:
        res = requests.get(url)
        data = res.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        
        # Save to database if user is authenticated
        if request.user.is_authenticated:
            Conversation.objects.create(
                user=request.user,
                message=text,
                translated_message=translated,
                source_language=source,
                target_language=target,
                message_type='speech' if request.GET.get('is_speech') else 'text'
            )
        
        return JsonResponse({
            "source_lang": source,
            "translated_text": translated
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required(login_url='auth')
def text_to_speech(request):
    """Convert translated text into speech"""
    text = request.GET.get("text", "")
    lang = request.GET.get("lang", "en")

    if not text:
        return JsonResponse({"error": "No text provided"}, status=400)

    try:
        tts = gTTS(text=text, lang=lang)
        path = f"speech_{request.user.id}.mp3"  # User-specific file
        tts.save(path)
        return FileResponse(open(path, "rb"), content_type="audio/mpeg")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required(login_url='auth')
def save_conversation(request):
    """Save conversation message via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message')
            translated_message = data.get('translated_message', '')
            source_language = data.get('source_language', 'en')
            target_language = data.get('target_language', 'hi')
            message_type = data.get('type', 'text')
            
            if message:
                conversation = Conversation.objects.create(
                    user=request.user,
                    message=message,
                    translated_message=translated_message,
                    source_language=source_language,
                    target_language=target_language,
                    message_type=message_type
                )
                
                return JsonResponse({
                    "success": True,
                    "id": conversation.id,
                    "timestamp": conversation.timestamp.isoformat()
                })
            else:
                return JsonResponse({"success": False, "error": "No message provided"})
                
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    
    return JsonResponse({"success": False, "error": "Invalid method"})

@login_required(login_url='auth')
def get_conversation_history(request):
    """Get conversation history for the current user"""
    messages = Conversation.objects.filter(user=request.user).order_by('-timestamp')[:50]
    
    messages_data = []
    for msg in messages:
        messages_data.append({
            "id": msg.id,
            "speaker": "You",
            "message": msg.message,
            "translated_message": msg.translated_message,
            "source_language": msg.source_language,
            "target_language": msg.target_language,
            "type": msg.message_type,
            "timestamp": msg.timestamp.isoformat()
        })
    
    return JsonResponse({"messages": messages_data})

@login_required(login_url='auth')
def clear_conversation_history(request):
    """Clear all conversation history for the current user"""
    if request.method == 'POST':
        Conversation.objects.filter(user=request.user).delete()
        messages.success(request, "Conversation history cleared successfully")
        return JsonResponse({"success": True})
    
    return JsonResponse({"success": False, "error": "Invalid method"})