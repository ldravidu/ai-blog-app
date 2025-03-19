from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from urllib.error import HTTPError
from django.conf import settings
import assemblyai as aai
import os
from yt_dlp import YoutubeDL
import logging
import hashlib
import pickle
import time
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.DEBUG)

TRANSCRIPT_CACHE_DIR = os.path.join(settings.MEDIA_ROOT, "transcripts")

if not os.path.exists(TRANSCRIPT_CACHE_DIR):
    os.makedirs(TRANSCRIPT_CACHE_DIR)


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

        # Get YouTube video title
        title = yt_title(yt_link)
        if not title:
            return JsonResponse({"error": "Failed to fetch video title"}, status=500)

        # Get transcript
        transcript = get_transcript(yt_link)
        if not transcript:
            return JsonResponse({"error": "Failed to get transcript"}, status=500)

        # Use OpenAI to generate blog
        blog_content = generate_blog_from_transcript(transcript)
        if not blog_content:
            return JsonResponse({"error": "Failed to generate blog"}, status=500)

        # Return blog article as a response
        return JsonResponse({"content": blog_content})
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


def yt_title(yt_link):
    try:
        ydl = YoutubeDL()
        info = ydl.extract_info(yt_link, download=False)
        return info.get("title", None)
    except Exception as e:
        logging.error(f"Error fetching video title: {e}")
        return None


def get_transcript(link):
    try:
        # Create a unique cache filename using a hash
        video_hash = hashlib.md5(link.encode()).hexdigest()
        cache_file = os.path.join(TRANSCRIPT_CACHE_DIR, f"{video_hash}.pkl")

        # Check if transcript already exists
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                cached_data = pickle.load(f)
            return cached_data

        # Download audio
        audio_file = download_audio(link)
        if not audio_file:
            return None

        # Transcribe audio using AssemblyAI
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file).text

        # Save transcript to cache
        with open(cache_file, "wb") as f:
            pickle.dump(transcript, f)

        # Clean up the downloaded audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)

        return transcript
    except Exception as e:
        logging.error(f"Error fetching transcript: {e}")
        return None


def download_audio(link):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(settings.MEDIA_ROOT, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "ffmpeg_location": "/usr/bin/ffmpeg",
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            audio_file = ydl.prepare_filename(info)
            base, ext = os.path.splitext(audio_file)
            audio_path = base + ".mp3"

            # Check if the file exists before returning
            if os.path.exists(audio_path):
                return audio_path
            else:
                return None
    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        return None


def generate_blog_from_transcript(transcript):
    try:
        client = InferenceClient(
            provider="hf-inference", api_key=settings.HUGGINGFACE_API_KEY
        )

        # Prepare the prompt
        prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article. Write it based on the transcript, but don't make it look like a YouTube video. Make it look like a proper blog article:\n\n{transcript}"

        result = client.text_generation(model="google/gemma-2-2b-it", prompt=prompt)

        # Generate the blog content
        generated_text = result.strip()

        # logging.debug(f"Generated blog content: {generated_text}")

        # Return the generated blog content
        return generated_text
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None


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
            except Exception as e:
                logging.error(f"Error creating account: {e}")
                error_message = "Error creating account"
                return render(request, "signup.html", {"error_message": error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, "signup.html", {"error_message": error_message})
    return render(request, "signup.html")


def user_logout(request):
    logout(request)
    return redirect("/login")
