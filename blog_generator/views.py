from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import assemblyai as aai
import openai
import os


# Create your views here.
@login_required(login_url="/login")
def index(request):
    return render(request, "index.html")


@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data["link"]
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid data"}, status=400)

        # Get Youtube video title
        title = yt_title(yt_link)

        # Get transcript
        transcript = get_transcript(yt_link)
        if not transcript:
            return JsonResponse({"error": "Failed to get transcript"}, status=500)

        # Use OpenAI to generate blog
        blog_content = generate_blog_from_transcript(transcript)

        if not blog_content:
            return JsonResponse({"error": "Failed to generate blog"}, status=500)

        # Save blog article to database

        # Return blog article as a response
        return JsonResponse(
            {
                "title": title,
                "transcript": transcript,
                "blog": blog_content,
            }
        )
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


def yt_title(link):
    yt = YouTube(link)
    return yt.title


def get_transcript(link):
    audio_file = download_audio(link)
    aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcriber.text


def download_audio(link):
    audio_file = (
        YouTube(link)
        .streams.filter(only_audio=True)
        .first()
        .download(output_path=settings.MEDIA_ROOT)
    )
    base, ext = os.path.splitext(audio_file)
    new_file = base + ".mp3"
    os.rename(audio_file, new_file)
    return new_file


def generate_blog_from_transcript(transcript):
    openai.api_key = settings.OPENAI_API_KEY

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but don't make it look like a youtube video. Make it look like a proper blog article:\n\n{transcript}\n\nArticle:"

    response = openai.Completion.create(model="gpt-4o", prompt=prompt, max_tokens=1000)

    generated_content = response.choices[0].text.strip()

    return generated_content


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            error_message = "Invalid credentials"
            return render(request, "login.html", {"error_message": error_message})
    return render(request, "login.html")


def user_signup(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmPassword = request.POST["confirmPassword"]

        if password == confirmPassword:
            try:
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                user.save()
                login(request, user)
                return redirect("/")
            except:
                error_message = "Error creating account"
                return render(request, "signup.html", {"error_message": error_message})

        else:
            error_message = "Passwords do not match"
            return render(request, "signup.html", {"error_message": error_message})
    return render(request, "signup.html")


def user_logout(request):
    logout(request)
    return redirect("/login")
